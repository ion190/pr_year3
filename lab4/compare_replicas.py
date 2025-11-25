import requests
import json
import glob
import sys
import os
from collections import Counter

LEADER_URL = "http://localhost:8000/dump"
FOLLOWER_PORTS = [8001, 8002, 8003, 8004, 8005]
TIMEOUT = 10

def fetch_and_save(url: str, outpath: str) -> dict:
    try:
        r = requests.get(url, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        with open(outpath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return data
    except Exception as e:
        print(f"ERROR fetching {url}: {e}")
        if os.path.exists(outpath):
            try:
                return json.load(open(outpath))
            except Exception:
                return {}
        return {}

def load_json_path(path):
    try:
        return json.load(open(path))
    except Exception:
        return {}

def main():
    print("Fetching leader dump...")
    leader = fetch_and_save(LEADER_URL, "leader_dump.json")
    if not isinstance(leader, dict):
        print("Leader dump is not a JSON object (expected dict). Aborting.")
        sys.exit(1)
    follower_files = []
    for p in FOLLOWER_PORTS:
        url = f"http://localhost:{p}/dump"
        out = f"follower_{p}.json"
        print(f"Fetching follower {p}...")
        data = fetch_and_save(url, out)
        follower_files.append(out)

    print("\nCounts:")
    try:
        print("leader:", len(leader))
    except Exception:
        print("leader: (error reading leader_dump.json)")
    for f in sorted(follower_files):
        try:
            d = load_json_path(f)
            print(f, len(d))
        except Exception:
            print(f, "(error)")

    print("\nLeader summary")
    leader_keys = set(leader.keys())
    print("keys:", len(leader_keys))
    print()

    overall_ok = True
    for f in sorted(follower_files):
        d = load_json_path(f)
        print(f)
        if not isinstance(d, dict):
            print("  follower dump empty or unreadable")
            overall_ok = False
            continue
        fk = set(d.keys())
        missing = sorted(list(leader_keys - fk))
        extra = sorted(list(fk - leader_keys))
        mismatches = []
        for k in sorted(leader_keys & fk):
            if d[k] != leader[k]:
                mismatches.append((k, leader[k], d[k]))
        print(f"leader keys: {len(leader_keys)}, follower keys: {len(fk)}")
        print(f"missing keys on follower: {len(missing)}")
        print(f"extra keys on follower: {len(extra)}")
        print("matching keys:", len(leader_keys & fk) - len(mismatches))
        print("mismatched values:", len(mismatches))
        if missing:
            print("  sample missing keys:", missing[:5])
        if extra:
            print("  sample extra keys:", extra[:5])
        
        print()

if __name__ == "__main__":
    main()
