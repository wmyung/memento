#!/usr/bin/env python3
"""memento-sync: Sync ME DB master → replica. Requires scp."""
import subprocess, sys, time
from pathlib import Path

CFG = Path.home() / ".memento" / "sync.conf"
DB = Path.home() / ".memento" / "memory.sqlite3"

def load_cfg():
    if not CFG.exists(): return {}
    return dict(line.strip().split("=", 1) for line in CFG.read_text().strip().split("\n") if "=" in line)

def do_push(target):
    if not DB.exists(): print(f"❌ No DB at {DB}"); return False
    try:
        subprocess.run(["scp", "-o", "ConnectTimeout=10", "-q", str(DB), target], check=True, timeout=30)
        print(f"✅ Synced → {target}"); return True
    except Exception as e: print(f"❌ Sync failed: {e}"); return False

def do_pull(source):
    try:
        subprocess.run(["scp", "-o", "ConnectTimeout=10", "-q", source, str(DB)], check=True, timeout=30)
        print(f"✅ Pulled ← {source}"); return True
    except Exception as e: print(f"❌ Pull failed: {e}"); return False

def main():
    cfg = load_cfg()
    if len(sys.argv) > 1:
        if sys.argv[1] == "--push" and len(sys.argv) >= 3:
            do_push(sys.argv[2])
        elif sys.argv[1] == "--pull" and len(sys.argv) >= 3:
            do_pull(sys.argv[2])
        else:
            print("Usage: memento-sync --push user@host:path  | --pull user@host:path")
    elif cfg:
        mode = cfg.get("mode", "push")
        target = cfg.get("target", "")
        if not target: print("❌ No target in sync.conf"); return
        if mode == "push": do_push(target)
        else: do_pull(target)
    else:
        print("❌ No config. Create ~/.memento/sync.conf or use --push/--pull")
        print("  Config format:\n    mode=push\n    target=user@host:~/.memento/memory.sqlite3")

if __name__ == "__main__":
    main()
