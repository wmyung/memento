#!/usr/bin/env python3
"""
memento-mcp — Optional MCP server for MEMENTO.

Allows MCP-compatible clients (Claude Code, Codex CLI, Cursor, etc.)
to use MEMENTO's memory system as MCP tools.

Usage:
  memento mcp                        # Stdio mode (for Claude Code, etc.)
  memento mcp --port 8765            # HTTP SSE mode (experimental)

Protocol: JSON-RPC 2.0 over stdio (MCP standard)
"""
import sys, json, sqlite3, subprocess, hashlib, os, time
from pathlib import Path
from datetime import datetime, timezone

HOME = Path.home()
ME_DB = HOME / ".memento" / "memory.sqlite3"
OP_DB = HOME / ".memento" / "agent.db"
WIKI_DIR = HOME / "wiki"

TOOLS = [
    {
        "name": "memento_recall",
        "description": "Search the fact store (SQLite FTS5, ~5ms). Returns matching facts with timestamps.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (FTS5 BM25)"},
                "limit": {"type": "number", "default": 10}
            },
            "required": ["query"]
        }
    },
    {
        "name": "memento_deep_recall",
        "description": "2-hop search: fact store → keyword bridge → wiki. Use for detailed procedural knowledge.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "number", "default": 5}
            },
            "required": ["query"]
        }
    },
    {
        "name": "memento_remember",
        "description": "Store a fact in SQLite fact store. Include --keywords 'wiki:slug' to bridge to wiki pages.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Fact text"},
                "keywords": {"type": "string", "description": "Space-separated keywords, use 'wiki:slug' for wiki bridge"},
                "category": {"type": "string", "enum": ["preference", "config", "entity", "finding", ""], "default": ""}
            },
            "required": ["content"]
        }
    },
    {
        "name": "memento_wiki_search",
        "description": "Search wiki pages (Markdown + Git) by content. Returns matching file paths.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "number", "default": 5}
            },
            "required": ["query"]
        }
    },
    {
        "name": "memento_decide",
        "description": "Record a methodological or architectural decision with rationale.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "decision": {"type": "string"},
                "rationale": {"type": "string", "default": ""}
            },
            "required": ["topic", "decision"]
        }
    },
    {
        "name": "memento_artifact_add",
        "description": "Register a file (plot, table, report) in the artifact registry.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute path to file"},
                "description": {"type": "string", "default": ""},
                "tags": {"type": "string", "default": ""}
            },
            "required": ["path"]
        }
    },
    {
        "name": "memento_experience_add",
        "description": "Log a success, failure, correction, or lesson learned.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["success", "failure", "correction", "lesson"]},
                "summary": {"type": "string"},
                "lesson": {"type": "string", "default": ""},
                "domain": {"type": "string", "default": ""},
                "severity": {"type": "number", "default": 1}
            },
            "required": ["type", "summary"]
        }
    },
    {
        "name": "memento_tag",
        "description": "Tag any memory URI with a semantic tag.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "uri": {"type": "string", "description": "e.g. mem:12345 or wiki://slug"},
                "tag": {"type": "string"}
            },
            "required": ["uri", "tag"]
        }
    },
    {
        "name": "memento_relate",
        "description": "Create a typed relation between two URIs. Types: informs, supports, contradicts, extends, built-from, related_to, precedes, follows, contemporaneous.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "target": {"type": "string"},
                "relation_type": {"type": "string", "default": "related_to"}
            },
            "required": ["source", "target"]
        }
    },
    {
        "name": "memento_timeline",
        "description": "Walk precedes/follows chains to reconstruct chronological order.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "uri": {"type": "string"}
            },
            "required": ["uri"]
        }
    },
    {
        "name": "memento_status",
        "description": "Show layer statistics (fact count, wiki pages, artifacts, decisions, tag, relations).",
        "inputSchema": {"type": "object", "properties": {}}
    }
]


def get_db(p):
    c = sqlite3.connect(str(p))
    c.row_factory = sqlite3.Row
    return c


def handle_tool_call(name, args):
    if name == "memento_recall":
        q = args.get("query", ""); lim = args.get("limit", 10)
        c = get_db(ME_DB)
        try:
            rows = c.execute("SELECT id, content, category, keywords, created_at, access_count FROM memories_fts WHERE memories_fts MATCH ? ORDER BY rank LIMIT ?", (q, lim)).fetchall()
        except:
            rows = c.execute("SELECT id, content, category, keywords, created_at, access_count FROM memories WHERE content LIKE ? OR keywords LIKE ? ORDER BY updated_at DESC LIMIT ?", (f"%{q}%", f"%{q}%", lim)).fetchall()
        c.close()
        return {"results": [{"uri": r["id"], "content": r["content"], "category": r["category"], "keywords": r["keywords"], "created": datetime.fromtimestamp(r["created_at"], tz=timezone.utc).isoformat()} for r in rows]}

    elif name == "memento_deep_recall":
        q = args.get("query", ""); lim = args.get("limit", 5)
        c = get_db(ME_DB)
        try:
            rows = c.execute("SELECT id, content, keywords FROM memories_fts WHERE memories_fts MATCH ? ORDER BY rank LIMIT ?", (q, lim)).fetchall()
        except:
            rows = c.execute("SELECT id, content, keywords FROM memories WHERE content LIKE ? OR keywords LIKE ? ORDER BY updated_at DESC LIMIT ?", (f"%{q}%", f"%{q}%", lim)).fetchall()
        c.close()
        wiki_kws = set()
        for r in rows:
            for t in (r["keywords"] or "").split():
                if t.startswith("wiki:"): wiki_kws.add(t.split(":",1)[1])
        wiki_results = []
        for kw in wiki_kws:
            try:
                r = subprocess.run(["grep", "-ril", kw, str(WIKI_DIR / "wiki")], capture_output=True, text=True, timeout=5)
                for f in r.stdout.strip().split("\n"):
                    if f: wiki_results.append({"path": str(Path(f).relative_to(WIKI_DIR)), "keyword": kw})
            except: pass
        return {"l0_results": [{"uri": r["id"], "content": r["content"]} for r in rows], "wiki_results": wiki_results}

    elif name == "memento_remember":
        content = args.get("content", ""); kw = args.get("keywords", ""); cat = args.get("category", "")
        c = get_db(ME_DB); mid = f"mem:{int(time.time())}"
        c.execute("INSERT INTO memories (id, content, category, keywords) VALUES (?,?,?,?)", (mid, content, cat, kw))
        c.commit(); c.close()
        return {"status": "stored", "uri": mid}

    elif name == "memento_wiki_search":
        q = args.get("query", ""); lim = args.get("limit", 5)
        try:
            r = subprocess.run(["grep", "-ril", q, str(WIKI_DIR)], capture_output=True, text=True, timeout=10)
            files = [f for f in r.stdout.strip().split("\n") if f][:lim]
            return {"results": [{"path": str(Path(f).relative_to(WIKI_DIR))} for f in files]}
        except: return {"results": []}

    elif name == "memento_decide":
        c = get_db(OP_DB)
        c.execute("INSERT INTO decisions (topic, decision, rationale) VALUES (?,?,?)", (args["topic"], args["decision"], args.get("rationale", "")))
        c.commit(); c.close()
        return {"status": "recorded"}

    elif name == "memento_artifact_add":
        fp = Path(args["path"])
        if not fp.exists(): return {"error": f"File not found: {args['path']}"}
        h = hashlib.sha256(fp.read_bytes()).hexdigest()[:16]
        c = get_db(OP_DB)
        c.execute("INSERT OR REPLACE INTO artifacts (path, description, file_hash, source, tags, file_size) VALUES (?,?,?,?,?,?)",
                  (str(fp.resolve()), args.get("description",""), h, "mcp", args.get("tags",""), fp.stat().st_size))
        c.commit(); c.close()
        return {"status": "registered", "hash": h}

    elif name == "memento_experience_add":
        t = args.get("type", ""); s = args.get("summary", "")
        if t not in ("success","failure","correction","lesson"): return {"error": f"Invalid type: {t}"}
        c = get_db(OP_DB)
        c.execute("INSERT INTO experiences (experience_type, domain, task_summary, lesson, severity) VALUES (?,?,?,?,?)",
                  (t, args.get("domain",""), s, args.get("lesson",""), args.get("severity",1)))
        c.commit(); c.close()
        return {"status": "stored", "type": t}

    elif name == "memento_tag":
        c = get_db(ME_DB)
        c.execute("INSERT INTO l3_tags (uri, tag) VALUES (?,?)", (args["uri"], args["tag"]))
        c.commit(); c.close()
        return {"status": "tagged"}

    elif name == "memento_relate":
        c = get_db(ME_DB)
        c.execute("INSERT INTO l3_relations (source_uri, target_uri, relation_type) VALUES (?,?,?)", (args["source"], args["target"], args.get("relation_type", "related_to")))
        c.commit(); c.close()
        return {"status": "related"}

    elif name == "memento_timeline":
        uri = args.get("uri", "")
        c = get_db(ME_DB)
        visited = set(); chain = []
        def walk(u, _dir):
            if u in visited: return
            visited.add(u)
            for r in c.execute("SELECT source_uri FROM l3_relations WHERE target_uri = ? AND relation_type IN ('precedes','follows')", (u,)): walk(r["source_uri"], "backward")
            chain.append(u)
            for r in c.execute("SELECT target_uri FROM l3_relations WHERE source_uri = ? AND relation_type IN ('precedes','follows')", (u,)): walk(r["target_uri"], "forward")
        walk(uri, "forward")
        c.close()
        return {"uri": uri, "timeline": chain}

    elif name == "memento_status":
        try:
            c = get_db(ME_DB); l0 = c.execute("SELECT COUNT(*) FROM memories").fetchone()[0]; lt = c.execute("SELECT COUNT(*) FROM l3_tags").fetchone()[0]; lr = c.execute("SELECT COUNT(*) FROM l3_relations").fetchone()[0]; c.close()
            c = get_db(OP_DB); art = c.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]; dec = c.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]; exp = c.execute("SELECT COUNT(*) FROM experiences").fetchone()[0]; c.close()
            wc = len(list(WIKI_DIR.rglob("*.md"))) if WIKI_DIR.exists() else 0
            return {"facts": l0, "wiki_pages": wc, "artifacts": art, "decisions": dec, "experiences": exp, "tags": lt, "relations": lr}
        except Exception as e:
            return {"error": str(e)}

    return {"error": f"Unknown tool: {name}"}


def main():
    if "--port" in sys.argv:
        idx = sys.argv.index("--port")
        port = int(sys.argv[idx+1]) if idx+1 < len(sys.argv) else 8765
        # Simple HTTP SSE mode (minimal)
        from http.server import HTTPServer, BaseHTTPRequestHandler
        class MCPHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                try:
                    req = json.loads(body)
                    resp = handle_request(req)
                except Exception as e:
                    resp = {"jsonrpc": "2.0", "error": {"code": -32700, "message": str(e)}, "id": None}
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(resp).encode())
            def log_message(self, *a): pass
        print(f"MEMENTO MCP server on http://localhost:{port}", file=sys.stderr)
        HTTPServer(("", port), MCPHandler).serve_forever()
    else:
        # Stdio mode (MCP standard)
        for line in sys.stdin:
            line = line.strip()
            if not line: continue
            try:
                req = json.loads(line)
                resp = handle_request(req)
                print(json.dumps(resp), flush=True)
            except json.JSONDecodeError as e:
                err = {"jsonrpc": "2.0", "error": {"code": -32700, "message": str(e)}, "id": None}
                print(json.dumps(err), flush=True)


def handle_request(req):
    method = req.get("method", ""); params = req.get("params", {}); rid = req.get("id")
    if method == "ping":
        return {"jsonrpc": "2.0", "result": "pong", "id": rid}
    elif method == "tools/list":
        return {"jsonrpc": "2.0", "result": {"tools": TOOLS}, "id": rid}
    elif method == "tools/call":
        try:
            result = handle_tool_call(params.get("name", ""), params.get("arguments", {}))
            return {"jsonrpc": "2.0", "result": {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}, "id": rid}
        except Exception as e:
            return {"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}, "id": rid}
    return {"jsonrpc": "2.0", "error": {"code": -32601, "message": f"Unknown: {method}"}, "id": rid}


if __name__ == "__main__":
    main()
