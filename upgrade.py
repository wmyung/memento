#!/usr/bin/env python3
"""
memento-upgrade — Migrate existing Hermes sqlite-suitectl data to MEMENTO.

Usage:
  memento upgrade               # Auto-detect and migrate
  memento upgrade --dry-run     # Preview only, no changes
"""
import os, sys, shutil, sqlite3
from pathlib import Path

HERMES = Path.home() / ".hermes"
MEMENTO = Path.home() / ".memento"

SOURCES = {
    "ME Complex (facts)": {
        "src": HERMES / "shared_memory" / "memory.sqlite3",
        "dst": MEMENTO / "memory.sqlite3",
        "required": False,
    },
    "SQLite Suite": {
        "src": HERMES / "agent.db",
        "dst": MEMENTO / "agent.db",
        "required": False,
    },
    "Wiki (llm-wiki)": {
        "src": Path.home() / "vaults" / "llm-wiki",
        "dst": Path.home() / "wiki",
        "required": False,
    },
}

def check_schema_compat(db_path):
    """Check if the source DB has tables compatible with MEMENTO."""
    try:
        c = sqlite3.connect(str(db_path))
        tables = set(r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall())
        c.close()
        required = {"memories", "l3_tags", "l3_relations"}
        found = required & tables
        return len(found) > 0, list(found)
    except:
        return False, []

def cmd_upgrade(dry_run=False):
    print("MEMENTO Upgrade Scanner")
    print("=" * 50)

    found_any = False
    actions = []

    for name, conf in SOURCES.items():
        src = conf["src"]
        dst = conf["dst"]

        if not src.exists():
            print(f"  · {name}: not found ({src})")
            continue

        found_any = True
        size = src.stat().st_size
        size_str = f"{size/1024:.0f}KB" if size < 1024*1024 else f"{size/1024/1024:.1f}MB"

        if dst.exists():
            print(f"  · {name}: already exists ({dst})")
            continue

        compat, tables = check_schema_compat(src)
        if not compat:
            print(f"  · {name}: found ({src}, {size_str}) — schema mismatch (tables: {tables})")
            continue

        actions.append((name, src, dst))
        print(f"  · {name}: ready ({src}, {size_str}) -> {dst}")

    if not found_any:
        print("\nNo existing Hermes data detected.")
        print("MEMENTO can be used standalone: memento init")
        return

    if not actions:
        print("\nAll data is already at MEMENTO paths.")
        return

    print(f"\nItems to migrate: {len(actions)}")

    if dry_run:
        print("(--dry-run mode, no changes)")
        for name, src, dst in actions:
            if src.is_dir():
                print(f"  · {name}: symlink {src} -> {dst}")
            else:
                print(f"  · {name}: copy {src} -> {dst}")
        print("\nRun without --dry-run to execute.")
        return

    # Execute migration
    confirm = input(f"\nMigrate {len(actions)} items to ~/.memento/? [y/N]: ")
    if confirm.lower() != "y":
        print("Cancelled.")
        return

    MEMENTO.mkdir(parents=True, exist_ok=True)

    for name, src, dst in actions:
        try:
            if src.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                dst.symlink_to(src, target_is_directory=True)
                print(f"  symlinked: {src} -> {dst}")
            else:
                shutil.copy2(src, dst)
                print(f"  copied: {src} ({src.stat().st_size/1024:.0f}KB)")
        except Exception as e:
            print(f"  failed: {name} - {e}")

    print("\n---")
    print("Verify with: memento status")
    print("Your original Hermes data is untouched.")
    print("Rollback: delete ~/.memento/")

def main():
    dry_run = "--dry-run" in sys.argv
    cmd_upgrade(dry_run)

if __name__ == "__main__":
    main()
