#!/usr/bin/env python3
"""
memento-upgrade — 기존 Hermes sqlite-suitectl → MEMENTO 마이그레이션

Usage:
  memento upgrade           # 자동 감지 및 마이그레이션
  memento upgrade --dry-run # 변경 없이 미리보기만
"""
import os, sys, shutil, sqlite3
from pathlib import Path

HERMES = Path.home() / ".hermes"
MEMENTO = Path.home() / ".memento"

# 찾을 대상
SOURCES = {
    "ME Complex": {
        "src": HERMES / "shared_memory" / "memory.sqlite3",
        "dst": MEMENTO / "memory.sqlite3",
        "required": False,
    },
    "SQLite Suite": {
        "src": HERMES / "agent.db",
        "dst": MEMENTO / "agent.db",
        "required": False,
    },
    "Wiki (우재님 LLM Wiki)": {
        "src": Path.home() / "vaults" / "llm-wiki",
        "dst": Path.home() / "wiki",
        "required": False,
    },
    "Wiki (에이전트 Wiki)": {
        "src": Path.home() / "wiki",
        "dst": Path.home() / "wiki",
        "required": False,
    },
}

def check_schema_compat(db_path):
    """두 DB의 schema가 호환되는지 확인"""
    try:
        c = sqlite3.connect(str(db_path))
        tables = set(r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall())
        c.close()
        # MEMENTO가 필요한 최소 테이블
        required = {"memories", "l3_tags", "l3_relations"}
        found = required & tables
        return len(found) > 0, list(found)
    except:
        return False, []

def cmd_upgrade(dry_run=False):
    print("🔍 MEMENTO Upgrade Scanner")
    print("=" * 50)
    
    found_any = False
    actions = []
    
    for name, conf in SOURCES.items():
        src = conf["src"]
        dst = conf["dst"]
        
        if not src.exists():
            print(f"  · {name}: ❌ 없음 ({src})")
            continue
        
        found_any = True
        size = src.stat().st_size
        size_str = f"{size/1024:.0f}KB" if size < 1024*1024 else f"{size/1024/1024:.1f}MB"
        
        if dst.exists():
            print(f"  · {name}: ✅ 이미 있음 ({dst})")
            continue
        
        compat, tables = check_schema_compat(src)
        if not compat:
            print(f"  · {name}: ⚠️  발견 ({src}, {size_str}) — schema mismatch (tables: {tables})")
            continue
        
        actions.append((name, src, dst))
        print(f"  · {name}: 🆕 발견 ({src}, {size_str}) → {dst}")
    
    if not found_any:
        print("\n기존 Hermes 데이터가 발견되지 않았습니다.")
        print("MEMENTO는 처음부터 사용 가능합니다: memento init")
        return
    
    if not actions:
        print("\n✅ 모든 데이터가 이미 MEMENTO 위치에 있습니다.")
        return
    
    print(f"\n{'=' * 50}")
    print(f"📋 마이그레이션 대상: {len(actions)}개")
    
    if dry_run:
        print("(--dry-run 모드, 변경 없음)")
        for name, src, dst in actions:
            print(f"  · {name}: cp {src} → {dst}")
        print("\n실행하려면: memento upgrade (--dry-run 없이)")
        return
    
    # 실제 수행
    confirm = input(f"\n위 {len(actions)}개를 MEMENTO로 이동할까요? (y/N): ")
    if confirm.lower() != "y":
        print("취소됨.")
        return
    
    MEMENTO.mkdir(parents=True, exist_ok=True)
    
    for name, src, dst in actions:
        try:
            if src.is_dir():
                # Wiki: symlink
                if dst.exists():
                    shutil.rmtree(dst)
                dst.symlink_to(src, target_is_directory=True)
                print(f"  ✅ {name}: symlink {src} → {dst}")
            else:
                # DB: copy (안전)
                shutil.copy2(src, dst)
                print(f"  ✅ {name}: copy → {dst} ({src.stat().st_size/1024:.0f}KB)")
        except Exception as e:
            print(f"  ❌ {name}: 실패 — {e}")
    
    # Agent 메모리 업데이트 제안
    print(f"\n{'=' * 50}")
    print("📝 다음 단계")
    print("  · `memento status` 로 모든 레이어 확인")
    print("  · `memento recall 'query'` 로 검색 테스트")
    print("  · AGENTS.md 의 memory 관련 내용을 MEMENTO CLI로 업데이트")
    print("\n기존 Hermes 도구(sqlite-suitectl 등)는 그대로 동작합니다.")
    print("언제든지 되돌리려면 ~/.memento/ 를 삭제하면 됩니다.")

def main():
    dry_run = "--dry-run" in sys.argv
    cmd_upgrade(dry_run)

if __name__ == "__main__":
    main()
