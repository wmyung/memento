#!/usr/bin/env python3
"""
memento — Efficient Memory System: SQLite + LLM + Wiki + Network

Unified CLI for multi-layer memory in AI agent environments.
Zero dependencies beyond Python stdlib + SQLite.
"""
import sqlite3, sys, os, json, time, hashlib, subprocess, shutil
from pathlib import Path
from datetime import datetime, timezone

# ── Paths ──
HOME = Path.home()
CONFIG_DIR = HOME / ".memento"
ME_DB = CONFIG_DIR / "memory.sqlite3"       # ME Complex (L0, L1, L2, L3)
OP_DB = CONFIG_DIR / "agent.db"              # SQLite Suite (cache, artifacts, decisions, experiences)
WIKI_DIR = HOME / "wiki"                     # Wiki Complex
MEMENTO_SESSION_ID = os.environ.get("MEMENTO_SESSION_ID", "")
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
WIKI_DIR.mkdir(parents=True, exist_ok=True)

# ── SQLite Suite schema ──

ME_SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    id          TEXT PRIMARY KEY,
    content     TEXT NOT NULL,
    category    TEXT DEFAULT '',
    keywords    TEXT DEFAULT '',
    created_at  INTEGER NOT NULL DEFAULT (unixepoch()),
    updated_at  INTEGER NOT NULL DEFAULT (unixepoch()),
    access_count INTEGER DEFAULT 0,
    agent_name  TEXT DEFAULT '',
    ttl         INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
CREATE INDEX IF NOT EXISTS idx_memories_keywords ON memories(keywords);
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    content, keywords, category,
    content='memories', content_rowid='rowid'
);
CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, content, keywords, category) VALUES (new.rowid, new.content, new.keywords, new.category);
END;
CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, content, keywords, category) VALUES('delete', old.rowid, old.content, old.keywords, old.category);
END;
CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, content, keywords, category) VALUES('delete', old.rowid, old.content, old.keywords, old.category);
    INSERT INTO memories_fts(rowid, content, keywords, category) VALUES (new.rowid, new.content, new.keywords, new.category);
END;
CREATE TABLE IF NOT EXISTS l3_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uri TEXT NOT NULL,
    tag TEXT NOT NULL,
    created_at INTEGER NOT NULL DEFAULT (unixepoch())
);
CREATE TABLE IF NOT EXISTS l3_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_uri TEXT NOT NULL,
    target_uri TEXT NOT NULL,
    relation_type TEXT NOT NULL DEFAULT 'related_to',
    created_at INTEGER NOT NULL DEFAULT (unixepoch())
);
CREATE INDEX IF NOT EXISTS idx_l3_tag ON l3_tags(tag);
CREATE INDEX IF NOT EXISTS idx_l3_uri ON l3_tags(uri);
CREATE INDEX IF NOT EXISTS idx_l3_rel_source ON l3_relations(source_uri);
CREATE INDEX IF NOT EXISTS idx_l3_rel_target ON l3_relations(target_uri);
"""

OP_SCHEMA = """
CREATE TABLE IF NOT EXISTS tool_cache (
    query_hash TEXT PRIMARY KEY,
    tool_name TEXT NOT NULL,
    args_json TEXT NOT NULL,
    result TEXT NOT NULL,
    ttl INTEGER NOT NULL DEFAULT 3600,
    created_at INTEGER NOT NULL DEFAULT (unixepoch())
);
CREATE TABLE IF NOT EXISTS artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT '',
    file_hash TEXT DEFAULT '',
    source TEXT DEFAULT '',
    tags TEXT DEFAULT '',
    session_id TEXT DEFAULT '',
    file_size INTEGER DEFAULT 0,
    created_at INTEGER NOT NULL DEFAULT (unixepoch()),
    accessed_at INTEGER DEFAULT (unixepoch())
);
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    decision TEXT NOT NULL,
    rationale TEXT DEFAULT '',
    alternatives TEXT DEFAULT '',
    session_id TEXT DEFAULT '',
    created_at INTEGER NOT NULL DEFAULT (unixepoch())
);
CREATE TABLE IF NOT EXISTS experiences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experience_type TEXT NOT NULL CHECK(experience_type IN ('success','failure','correction','lesson')),
    domain TEXT DEFAULT '',
    task_summary TEXT NOT NULL,
    approach TEXT DEFAULT '',
    outcome TEXT DEFAULT '',
    lesson TEXT DEFAULT '',
    context_tags TEXT DEFAULT '',
    recurrence_count INTEGER DEFAULT 1,
    severity INTEGER DEFAULT 1,
    agent_name TEXT DEFAULT '',
    session_id TEXT DEFAULT '',
    created_at INTEGER NOT NULL DEFAULT (unixepoch()),
    last_encountered_at INTEGER DEFAULT (unixepoch())
);
CREATE INDEX IF NOT EXISTS idx_artifact_tags ON artifacts(tags);
CREATE INDEX IF NOT EXISTS idx_decision_topic ON decisions(topic);
CREATE INDEX IF NOT EXISTS idx_exp_type ON experiences(experience_type);
"""

# ── DB Helpers ──

def me_db():
    c = sqlite3.connect(str(ME_DB))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    return c

def op_db():
    c = sqlite3.connect(str(OP_DB))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    return c

# ── Init ──

def cmd_init():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    c = me_db(); c.executescript(ME_SCHEMA); c.commit(); c.close()
    c = op_db(); c.executescript(OP_SCHEMA); c.commit(); c.close()
    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    for d in ["raw", "sources", "concepts", "analysis", "entities"]:
        (WIKI_DIR / d).mkdir(parents=True, exist_ok=True)
    if not (WIKI_DIR / "index.md").exists():
        (WIKI_DIR / "index.md").write_text("# Wiki Index\n\n")
    print(f"✅ MEMENTO initialized")
    print(f"   ME DB:  {ME_DB}")
    print(f"   OP DB:  {OP_DB}")
    print(f"   Wiki:   {WIKI_DIR}")

def ensure_init():
    """Ensure databases exist, create them if not."""
    if not ME_DB.exists() or not OP_DB.exists():
        cmd_init()

# ── ME Complex — L0: raw facts ──

def cmd_remember(content, category="", keywords=""):
    c = me_db()
    mid = f"mem:{int(time.time())}"
    c.execute("INSERT INTO memories (id, content, category, keywords) VALUES (?,?,?,?)",
              (mid, content, category, keywords))
    c.commit(); c.close()
    print(f"✅ [{mid}] {content[:60]}")

def cmd_recall(query, limit=10):
    c = me_db()
    try:
        rows = c.execute(
            "SELECT id, content, category, keywords, created_at, access_count FROM memories_fts WHERE memories_fts MATCH ? ORDER BY rank LIMIT ?",
            (query, limit)
        ).fetchall()
    except:
        rows = c.execute(
            "SELECT id, content, category, keywords, created_at, access_count FROM memories WHERE content LIKE ? OR keywords LIKE ? ORDER BY updated_at DESC LIMIT ?",
            (f"%{query}%", f"%{query}%", limit)
        ).fetchall()
    if not rows:
        print(f"📭 No matches for '{query}'"); c.close(); return
    for r in rows:
        d = datetime.fromtimestamp(r['created_at'], tz=timezone.utc).strftime('%Y-%m-%d %H:%M')
        kw = f" [{r['keywords']}]" if r['keywords'] else ""
        print(f"  📌 {r['id']} [{d}]{kw}")
        print(f"     {r['content'][:200]}")
        if r['access_count']: print(f"     (accessed {r['access_count']}x)")
        if r['category']: print(f"     [{r['category']}]")
        c.execute("UPDATE memories SET access_count = access_count + 1 WHERE id = ?", (r['id'],))
    c.commit(); c.close()

# ── Wiki Complex — L0/L1/L2 ──

def cmd_wiki_create(slug):
    """Create wiki page under wiki/ directory."""
    path = WIKI_DIR / f"{slug}.md"
    if path.exists():
        print(f"⚠️  Exists: {path}"); return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# {slug.split('/')[-1]}\n\n")
    editor = os.environ.get("EDITOR")
    if not editor:
        for candidate in ("sensible-editor", "editor", "nano", "vim", "vi"):
            resolved = shutil.which(candidate)
            if resolved:
                editor = resolved
                break
    if editor:
        subprocess.call([editor, str(path)])
    else:
        print(f"⚠️  No editor found; created without opening: {path}")
        return
    print(f"✅ Created: {path}")

def cmd_wiki_search(query, limit=10):
    if not WIKI_DIR.exists(): print("❌ No wiki at {WIKI_DIR}"); return
    try:
        r = subprocess.run(["grep", "-ril", query, str(WIKI_DIR)],
                          capture_output=True, text=True, timeout=10)
        files = [f for f in r.stdout.strip().split("\n") if f]
        for f in files[:limit]:
            p = Path(f)
            title = p.read_text().split("\n")[0] if p.exists() else ""
            print(f"  📄 {p.relative_to(WIKI_DIR)}")
            if title: print(f"     {title[:100]}")
        if not files: print(f"📭 No wiki matches for '{query}'")
    except FileNotFoundError: print("❌ grep not available")

# ── Deep Recall: ME → keyword → Wiki ──

def cmd_deep_recall(query, limit=5):
    """2-hop: ME Complex → extract wiki: keywords → Wiki Complex search."""
    c = me_db()
    try:
        rows = c.execute(
            "SELECT id, content, keywords FROM memories_fts WHERE memories_fts MATCH ? ORDER BY rank LIMIT ?",
            (query, limit)
        ).fetchall()
    except:
        rows = c.execute(
            "SELECT id, content, keywords FROM memories WHERE content LIKE ? OR keywords LIKE ? ORDER BY updated_at DESC LIMIT ?",
            (f"%{query}%", f"%{query}%", limit)
        ).fetchall()
    c.close()
    if not rows: print(f"📭 No L0 matches for '{query}'"); return

    wiki_kws = set()
    print(f"🔍 Hop 1 — ME Complex:")
    for r in rows:
        kw = r['keywords'] or ""
        for t in kw.split():
            if t.startswith("wiki:"): wiki_kws.add(t.split(":",1)[1])
        print(f"     {r['id']}: {r['content'][:120]}")
        if r['keywords']: print(f"        keywords: {r['keywords']}")

    if wiki_kws:
        print(f"🔍 Hop 2 — Wiki Complex via keywords: {wiki_kws}")
        for kw in wiki_kws:
            cmd_wiki_search(kw, 3)

# ── SQLite Suite — operational ──

def cmd_artifact_add(path, desc="", tags="", source=""):
    p = Path(path)
    if not p.exists(): print(f"❌ Not found: {path}"); return
    h = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    sz = p.stat().st_size
    c = op_db()
    c.execute("INSERT OR REPLACE INTO artifacts (path, description, file_hash, source, tags, file_size) VALUES (?,?,?,?,?,?)",
              (str(p.resolve()), desc, h, source, tags, sz))
    c.commit(); c.close()
    print(f"✅ Artifact: {path}")

def cmd_artifact_list(tag=None):
    c = op_db()
    if tag:
        rows = c.execute("SELECT path, description, tags, created_at FROM artifacts WHERE tags LIKE ? ORDER BY created_at DESC LIMIT 50", (f"%{tag}%",)).fetchall()
    else:
        rows = c.execute("SELECT path, description, tags, created_at FROM artifacts ORDER BY created_at DESC LIMIT 50").fetchall()
    c.close()
    if not rows: print("📂 No artifacts"); return
    for r in rows:
        d = datetime.fromtimestamp(r['created_at'], tz=timezone.utc).strftime('%Y-%m-%d')
        print(f"  📄 {r['path']}")
        if r['description']: print(f"     {r['description'][:80]}")
        print(f"     [{d}] tags: {r['tags'] or '-'}")

def cmd_decide(topic, decision, rationale="", alternatives=""):
    c = op_db()
    c.execute("INSERT INTO decisions (topic, decision, rationale, alternatives) VALUES (?,?,?,?)",
              (topic, decision, rationale, alternatives))
    c.commit(); c.close()
    print(f"✅ Decision: {topic} → {decision[:60]}")

def cmd_decisions(topic=None):
    c = op_db()
    if topic:
        rows = c.execute("SELECT topic, decision, rationale, created_at FROM decisions WHERE topic LIKE ? ORDER BY created_at DESC LIMIT 20", (f"%{topic}%",)).fetchall()
    else:
        rows = c.execute("SELECT topic, decision, rationale, created_at FROM decisions ORDER BY created_at DESC LIMIT 20").fetchall()
    c.close()
    if not rows: print("📋 No decisions"); return
    for r in rows:
        d = datetime.fromtimestamp(r['created_at'], tz=timezone.utc).strftime('%Y-%m-%d')
        print(f"  📋 [{d}] {r['topic']}")
        print(f"     → {r['decision'][:100]}")
        if r['rationale']: print(f"     why: {r['rationale'][:100]}")

# ── SQLite Suite — experiences ──

def cmd_experience_add(exp_type, summary, domain="", approach="", outcome="", lesson="", tags="", severity=1):
    if exp_type not in ("success", "failure", "correction", "lesson"):
        print(f"❌ Invalid type: {exp_type}. Use: success, failure, correction, lesson"); return
    ensure_init()
    c = op_db()
    c.execute(
        "INSERT INTO experiences (experience_type, domain, task_summary, approach, outcome, lesson, context_tags, severity, agent_name) VALUES (?,?,?,?,?,?,?,?,?)",
        (exp_type, domain, summary, approach, outcome, lesson, tags, severity, os.environ.get("MEMENTO_AGENT_NAME", ""))
    )
    c.commit(); c.close()
    print(f"✅ [{exp_type}] {summary[:60]}")

def cmd_experience_recall(query, limit=5):
    ensure_init()
    c = op_db()
    rows = c.execute(
        "SELECT id, experience_type, domain, task_summary, lesson, severity, recurrence_count, created_at FROM experiences WHERE task_summary LIKE ? OR lesson LIKE ? OR context_tags LIKE ? ORDER BY severity DESC, created_at DESC LIMIT ?",
        (f"%{query}%", f"%{query}%", f"%{query}%", limit)
    ).fetchall()
    c.close()
    if not rows: print(f"📭 No experiences match '{query}'"); return
    for r in rows:
        d = datetime.fromtimestamp(r['created_at'], tz=timezone.utc).strftime('%Y-%m-%d')
        icon = {"success": "✅", "failure": "❌", "correction": "🔧", "lesson": "📖"}.get(r['experience_type'], "📌")
        print(f"  {icon} [{d}] [{r['experience_type']}] {r['task_summary'][:80]}")
        if r['lesson']: print(f"     lesson: {r['lesson'][:120]}")
        print()

def cmd_experience_list(exp_type=None, domain=None, limit=20):
    ensure_init()
    c = op_db()
    sql = "SELECT id, experience_type, domain, task_summary, lesson, severity, created_at FROM experiences WHERE 1=1"
    params = []
    if exp_type: sql += " AND experience_type = ?"; params.append(exp_type)
    if domain: sql += " AND domain LIKE ?"; params.append(f"%{domain}%")
    sql += " ORDER BY created_at DESC LIMIT ?"; params.append(limit)
    rows = c.execute(sql, params).fetchall()
    c.close()
    if not rows: print("📭 No experiences"); return
    for r in rows:
        d = datetime.fromtimestamp(r['created_at'], tz=timezone.utc).strftime('%Y-%m-%d')
        icon = {"success": "✅", "failure": "❌", "correction": "🔧", "lesson": "📖"}.get(r['experience_type'], "📌")
        print(f"  {icon} [{d}] [{r['experience_type']}] {r['task_summary'][:80]}")
        if r['lesson']: print(f"     {r['lesson'][:100]}")
        print()


# ── Semantic Graph (L3) ──

def cmd_tag(uri, tag):
    c = me_db()
    c.execute("INSERT INTO l3_tags (uri, tag) VALUES (?,?)", (uri, tag))
    c.commit(); c.close()
    print(f"✅ Tagged {uri} → {tag}")

def cmd_tag_search(tag):
    c = me_db()
    rows = c.execute("SELECT uri, tag, created_at FROM l3_tags WHERE tag LIKE ? ORDER BY created_at DESC LIMIT 30", (f"%{tag}%",)).fetchall()
    c.close()
    if not rows: print(f"📭 No tag '{tag}'"); return
    for r in rows:
        d = datetime.fromtimestamp(r['created_at'], tz=timezone.utc).strftime('%Y-%m-%d')
        print(f"  🏷️  {r['uri']} → {r['tag']} [{d}]")

def cmd_relate(src, tgt, rel="related_to"):
    c = me_db()
    c.execute("INSERT INTO l3_relations (source_uri, target_uri, relation_type) VALUES (?,?,?)", (src, tgt, rel))
    c.commit(); c.close()
    print(f"✅ {src} ──{rel}──▶ {tgt}")

def cmd_trace(uri):
    c = me_db()
    rows = c.execute(
        "SELECT target_uri, relation_type FROM l3_relations WHERE source_uri = ? UNION ALL SELECT source_uri, '←'||relation_type FROM l3_relations WHERE target_uri = ? ORDER BY relation_type",
        (uri, uri)
    ).fetchall()
    c.close()
    if not rows: print(f"📭 No relations for {uri}"); return
    for r in rows:
        print(f"  🔗 {uri} ──{r['relation_type']}──▶ {r['target_uri']}")

def cmd_timeline(uri):
    """Walk temporal precedes/follows chains to reconstruct chronological order."""
    c = me_db()
    visited = set()
    chain = []

    def walk(u, direction):
        if u in visited: return
        visited.add(u)
        # backward: find what precedes this
        for r in c.execute("SELECT source_uri FROM l3_relations WHERE target_uri = ? AND relation_type = 'precedes'", (u,)):
            walk(r['source_uri'], "backward")
        for r in c.execute("SELECT source_uri FROM l3_relations WHERE target_uri = ? AND relation_type = 'follows'", (u,)):
            walk(r['source_uri'], "backward")
        chain.append(u)
        # forward: find what this precedes
        for r in c.execute("SELECT target_uri FROM l3_relations WHERE source_uri = ? AND relation_type = 'precedes'", (u,)):
            walk(r['target_uri'], "forward")
        for r in c.execute("SELECT target_uri FROM l3_relations WHERE source_uri = ? AND relation_type = 'follows'", (u,)):
            walk(r['target_uri'], "forward")

    walk(uri, "forward")
    c.close()
    if not chain:
        print(f"📭 No timeline for {uri}"); return
    print(f"📅 Timeline for {uri}")
    for i, u in enumerate(chain):
        print(f"  {i+1}. {u}")

# ── Status ──

def cmd_status():
    c = me_db()
    l0 = c.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    l3t = c.execute("SELECT COUNT(*) FROM l3_tags").fetchone()[0]
    l3r = c.execute("SELECT COUNT(*) FROM l3_relations").fetchone()[0]
    c.close()
    c = op_db()
    art = c.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
    dec = c.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
    exp = c.execute("SELECT COUNT(*) FROM experiences").fetchone()[0]
    c.close()
    wc = len(list(WIKI_DIR.rglob("*.md"))) if WIKI_DIR.exists() else 0

    print("📊 MEMENTO — Efficient Memory System")
    print(f"  ME Complex (SQLite):")
    print(f"    L0 facts:  {l0}")
    print(f"    L3 tags:   {l3t}")
    print(f"    L3 rels:   {l3r}")
    print(f"  Wiki Complex (Markdown):")
    print(f"    files:     {wc}  ({WIKI_DIR})")
    print(f"  SQLite Suite:")
    print(f"    artifacts: {art}")
    print(f"    decisions: {dec}")
    print(f"    experienc: {exp}")

# ── CLI ──

def print_usage():
    print("Usage: memento <command> [args]")
    print()
    print("  init                    Initialize databases + wiki structure")
    print("  status                  Layer statistics")
    print()
    print("  ME Complex (fast facts):")
    print("  ───────────────────────")
    print("  remember <text> [--keywords k] [--category c]")
    print("  recall <query>")
    print()
    print("  Wiki Complex (deep knowledge):")
    print("  ─────────────────────────────")
    print("  wiki create <slug>")
    print("  wiki search <query>")
    print("  deep-recall <query>              (ME → keyword → Wiki)")
    print()
    print("  SQLite Suite (operational):")
    print("  ─────────────────────────────")
    print("  artifact add <path> [--desc d] [--tags t]")
    print("  artifact list [--tag t]")
    print("  decide <topic> <decision> [--rationale r]")
    print("  decisions [--topic t]")
    print("  experience add <type> <summary> [--domain d] [--lesson l] [--tags t] [--severity <1-5>]")
    print("  experience recall <query>")
    print("  experience list [--type success|failure|correction|lesson]")
    print()
    print("  Upgrade (from Hermes sqlite-suitectl):")
    print("  ─────────────────────────────────────")
    print("  upgrade                 Migrate existing data to ~/.memento/")
    print("  upgrade --dry-run       Preview without changes")
    print()
    print("  MCP (optional):")
    print("  ────────────────────")
    print("  mcp                     Start MCP server (stdio, for Claude Code/Codex CLI)")
    print("  mcp --port 8765         Start MCP server (HTTP)")
    print()
    print("  Semantic Graph (L3):")
    print("  ────────────────────")
    print("  tag <uri> <tag>")
    print("  tag-search <tag>")
    print("  relate <source> <target> [type]")
    print("  trace <uri>")
    print("  timeline <uri>            Walk precedes/follows chains")

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h","--help"):
        print_usage(); return

    cmd = sys.argv[1]
    args = sys.argv[2:]

    # init
    if cmd == "init": cmd_init(); return
    if cmd == "status": cmd_status(); return
    if cmd == "mcp":
        from mcp_server import main as mcp_main
        mcp_main()
        return
    if cmd == "upgrade":
        from upgrade import cmd_upgrade
        cmd_upgrade(dry_run="--dry-run" in sys.argv)
        return

    # ME Complex
    if cmd == "remember":
        if len(args) < 1: print("Usage: memento remember <text> [--keywords k]"); return
        text = args[0]
        kw = cat = ""
        for i, a in enumerate(args[1:]):
            if a == "--keywords" and i+1 < len(args[1:]): kw = args[1+i+1]
            if a == "--category" and i+1 < len(args[1:]): cat = args[1+i+1]
        cmd_remember(text, cat, kw)
    elif cmd == "recall":
        if len(args) < 1: print("Usage: memento recall <query>"); return
        cmd_recall(" ".join(args))

    # Wiki Complex
    elif cmd == "wiki":
        if len(args) < 2: print("Usage: memento wiki create|search"); return
        sub = args[0]
        if sub == "create": cmd_wiki_create(args[1])
        elif sub == "search": cmd_wiki_search(" ".join(args[1:]))
    elif cmd == "deep-recall":
        if len(args) < 1: print("Usage: memento deep-recall <query>"); return
        cmd_deep_recall(" ".join(args))

    # SQLite Suite
    elif cmd == "artifact":
        if len(args) < 2: print("Usage: memento artifact add|list"); return
        sub = args[0]
        if sub == "add":
            p = args[1]; desc=tags=src=""
            for i, a in enumerate(args[2:]):
                if a == "--desc" and i+1 < len(args[2:]): desc = args[2+i+1]
                if a == "--tags" and i+1 < len(args[2:]): tags = args[2+i+1]
                if a == "--source" and i+1 < len(args[2:]): src = args[2+i+1]
            cmd_artifact_add(p, desc, tags, src)
        elif sub == "list":
            tag = ""
            for i, a in enumerate(args[1:]):
                if a == "--tag" and i+1 < len(args[1:]): tag = args[1+i+1]
            cmd_artifact_list(tag)
    elif cmd == "decide":
        if len(args) < 2: print("Usage: memento decide <topic> <decision> [--rationale r]"); return
        topic, decision = args[0], args[1]
        rationale = ""
        for i, a in enumerate(args[2:]):
            if a == "--rationale" and i+1 < len(args[2:]): rationale = args[2+i+1]
        cmd_decide(topic, decision, rationale)
    elif cmd == "decisions":
        topic = " ".join(args) if args else None
        cmd_decisions(topic)
    elif cmd == "experience":
        if len(args) < 2: print("Usage: memento experience add|recall|list"); return
        sub = args[0]
        if sub == "add":
            if len(args) < 3: print("Usage: memento experience add <type> <summary> [--domain d] [--lesson l] [--tags t] [--severity <1-5>]"); return
            exp_type, summary = args[1], args[2]
            domain = lesson = tags = ""; severity = 1
            for i, a in enumerate(args[3:]):
                if a == "--domain" and i+1 < len(args[3:]): domain = args[3+i+1]
                if a == "--lesson" and i+1 < len(args[3:]): lesson = args[3+i+1]
                if a == "--tags" and i+1 < len(args[3:]): tags = args[3+i+1]
                if a == "--severity" and i+1 < len(args[3:]):
                    try: severity = int(args[3+i+1])
                    except: pass
            cmd_experience_add(exp_type, summary, domain, "", "", lesson, tags, severity)
        elif sub == "recall":
            if len(args) < 2: print("Usage: memento experience recall <query>"); return
            cmd_experience_recall(" ".join(args[1:]))
        elif sub == "list":
            exp_type = None; domain = None
            for i, a in enumerate(args[1:]):
                if a == "--type" and i+1 < len(args[1:]): exp_type = args[1+i+1]
                if a == "--domain" and i+1 < len(args[1:]): domain = args[1+i+1]
            cmd_experience_list(exp_type, domain)
        else: print(f"Unknown: {sub}")

    # Semantic Graph
    elif cmd == "tag":
        if len(args) < 2: print("Usage: memento tag <uri> <tag>"); return
        cmd_tag(args[0], args[1])
    elif cmd == "tag-search":
        if len(args) < 1: print("Usage: memento tag-search <tag>"); return
        cmd_tag_search(" ".join(args))
    elif cmd == "relate":
        if len(args) < 2: print("Usage: memento relate <source> <target> [type]"); return
        cmd_relate(args[0], args[1], args[2] if len(args) > 2 else "related_to")
    elif cmd == "trace":
        if len(args) < 1: print("Usage: memento trace <uri>"); return
        cmd_trace(args[0])
    elif cmd == "timeline":
        if len(args) < 1: print("Usage: memento timeline <uri>"); return
        cmd_timeline(args[0])

    else:
        print(f"Unknown: {cmd}")
        print_usage()

if __name__ == "__main__":
    main()
