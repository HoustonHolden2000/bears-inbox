#!/usr/bin/env python3
"""
READ-ONLY view of the Iron Halo calibration inbox for the Bears.
The Bears reason over what landed here. This module only reads; it has no
network, no route to Iron Halo, and cannot write the store.
"""
import os, json, sys

STORE = os.environ.get("IRONHALO_INBOX_STORE",
                       os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "ironhalo_inbox.jsonl"))

def read_all():
    if not os.path.exists(STORE):
        return []
    out = []
    with open(STORE, "r", encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                out.append(json.loads(ln))
    return out

def verify_chain():
    import hashlib
    prev = "GENESIS"
    n = 0
    for rec in read_all():
        body = json.dumps(rec["packet"], sort_keys=True, ensure_ascii=False)
        want = hashlib.sha256((prev + body).encode("utf-8")).hexdigest()[:16]
        if want != rec.get("_chain"):
            return False, n
        prev = rec["_chain"]
        n += 1
    return True, n

if __name__ == "__main__":
    recs = read_all()
    ok, n = verify_chain()
    print(f"packets={len(recs)} chain={'INTACT' if ok else 'BROKEN@'+str(n)}")
    if "--dump" in sys.argv:
        for r in recs:
            print(json.dumps(r["packet"], indent=2)[:600])
