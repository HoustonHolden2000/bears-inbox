#!/usr/bin/env python3
"""
Iron Halo -> Bears CALIBRATION INBOX (receiver-only, one-way).

Contract (Matthew Lambert / Vanguard, 2026-07-28):
  - POST JSON body to /inbox
  - REQUIRE header: Authorization: Bearer <IRONHALO_FEED_KEY>
  - Missing/wrong key -> 401 (no body stored)
  - Valid  -> append packet to hash-chained store, respond 200 {"ok":true}
  - The Bears READ the store. They never call Iron Halo. No outbound route exists here.

Key discipline: the key is read from env IRONHALO_FEED_KEY ONLY.
It is never written to disk, never logged, never printed. If the env var is
unset, the server refuses to start (fail-closed) rather than accept anything.

Store: append-only JSONL, SHA-256 hash chain (Bears ledger discipline).
Default bind: 127.0.0.1 (localhost). Public exposure is a DEPLOY decision
(host + domain + TLS) that is Brad's gavel — this file does not make it.
"""
import os, sys, json, hashlib, hmac, datetime, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

STORE = os.environ.get("IRONHALO_INBOX_STORE",
                       os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "ironhalo_inbox.jsonl"))
AUDIT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inbox_audit.jsonl")
_LOCK = threading.Lock()
MAX_BODY = 1_000_000  # 1 MB cap per packet


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def _tail_hash():
    """Last hash in the chain, or the genesis seed if empty."""
    if not os.path.exists(STORE):
        return "GENESIS"
    last = None
    with open(STORE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                last = line
    if not last:
        return "GENESIS"
    try:
        return json.loads(last).get("_chain", "GENESIS")
    except Exception:
        return "GENESIS"

def append_packet(packet, mode="redacted", remote=""):
    """Append one received packet to the hash-chained store. Returns entry hash."""
    with _LOCK:
        prev = _tail_hash()
        rec = {
            "_received_at": _now(),
            "_prev": prev,
            "_mode": mode,
            "_remote": remote,
            "packet": packet,
        }
        body = json.dumps(rec["packet"], sort_keys=True, ensure_ascii=False)
        rec["_chain"] = hashlib.sha256((prev + body).encode("utf-8")).hexdigest()[:16]
        with open(STORE, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec["_chain"]

def _audit(event, detail):
    try:
        with open(AUDIT, "a", encoding="utf-8") as f:
            f.write(json.dumps({"t": _now(), "event": event, "detail": detail}) + "\n")
    except Exception:
        pass


def _get_key():
    key = os.environ.get("IRONHALO_FEED_KEY", "")
    return key.strip()

class Handler(BaseHTTPRequestHandler):
    server_version = "IronHaloBearsInbox/0.1"

    def _reply(self, code, obj):
        payload = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt, *args):
        return  # silence default stderr logging (never log auth headers)

    def do_GET(self):
        # Health only. No packet data is ever served over the network.
        if self.path.split("?")[0] == "/health":
            return self._reply(200, {"ok": True, "service": "bears-inbox", "packets": _count()})
        return self._reply(404, {"ok": False, "error": "not_found"})

    def do_POST(self):
        expected = _get_key()
        auth = self.headers.get("Authorization", "")
        presented = auth[7:].strip() if auth.startswith("Bearer ") else ""
        if not expected or not presented or not hmac.compare_digest(presented, expected):
            _audit("reject_401", {"remote": self.client_address[0], "reason": "bad_or_missing_key"})
            return self._reply(401, {"ok": False, "error": "unauthorized"})
        if self.path.split("?")[0] != "/inbox":
            return self._reply(404, {"ok": False, "error": "not_found"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length <= 0 or length > MAX_BODY:
                return self._reply(413, {"ok": False, "error": "bad_length"})
            raw = self.rfile.read(length)
            packet = json.loads(raw.decode("utf-8"))
        except Exception as e:
            _audit("reject_400", {"remote": self.client_address[0], "err": str(e)[:120]})
            return self._reply(400, {"ok": False, "error": "bad_json"})
        chain = append_packet(packet, remote=self.client_address[0])
        _audit("accept", {"remote": self.client_address[0],
                          "packet_id": str(packet.get("packet_id", ""))[:80], "chain": chain})
        return self._reply(200, {"ok": True})

def _count():
    if not os.path.exists(STORE):
        return 0
    with open(STORE, "r", encoding="utf-8") as f:
        return sum(1 for ln in f if ln.strip())


def serve(host=None, port=None):
    if not _get_key():
        sys.stderr.write("FATAL: IRONHALO_FEED_KEY not set in env. Refusing to start (fail-closed).\n")
        sys.exit(2)
    # Render (and most PaaS) inject PORT and require binding 0.0.0.0.
    render_port = os.environ.get("PORT")
    default_host = "0.0.0.0" if render_port else "127.0.0.1"
    host = host or os.environ.get("IRONHALO_INBOX_HOST", default_host)
    port = int(port or render_port or os.environ.get("IRONHALO_INBOX_PORT", "8787"))
    httpd = ThreadingHTTPServer((host, port), Handler)
    sys.stderr.write(f"bears-inbox listening on {host}:{port} (POST /inbox) store={STORE}\n")
    httpd.serve_forever()

def selftest():
    """Localhost-only proof: good key -> 200 + stored; bad key -> 401 + not stored."""
    import urllib.request, urllib.error, socket
    os.environ["IRONHALO_FEED_KEY"] = "SELFTEST_KEY_" + hashlib.sha256(b"st").hexdigest()[:8]
    global STORE, AUDIT
    STORE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_selftest_store.jsonl")
    AUDIT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_selftest_audit.jsonl")
    for p in (STORE, AUDIT):
        if os.path.exists(p):
            os.remove(p)
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{port}/inbox"
    key = os.environ["IRONHALO_FEED_KEY"]
    results = []
    def post(bearer, body):
        req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        if bearer is not None:
            req.add_header("Authorization", "Bearer " + bearer)
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code
    results.append(("good_key_200", post(key, {"packet_id": "cal-selftest-001", "drill": True}) == 200))
    results.append(("bad_key_401", post("WRONG", {"packet_id": "should-not-store"}) == 401))
    results.append(("no_key_401", post(None, {"packet_id": "should-not-store"}) == 401))
    stored = _count()
    results.append(("only_good_stored", stored == 1))
    srv.shutdown()
    ok = all(r[1] for r in results)
    for name, passed in results:
        print(("PASS " if passed else "FAIL ") + name)
    print("SELFTEST:", "PASS" if ok else "FAIL", "| stored packets =", stored)
    for p in (STORE, AUDIT):
        if os.path.exists(p):
            os.remove(p)
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        selftest()
    elif len(sys.argv) > 1 and sys.argv[1] == "serve":
        serve()
    else:
        print("usage: ironhalo_receiver.py [selftest|serve]")
