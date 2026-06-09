# MEMENTO

**Agent Memory System — SQLite fact store + Git wiki + keyword bridge. No embeddings, no Docker.**

[![PyPI](https://img.shields.io/pypi/v/memento-memory)](https://pypi.org/project/memento-memory/)
[![Python](https://img.shields.io/pypi/pyversions/memento-memory)](https://pypi.org/project/memento-memory/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Used by](https://img.shields.io/badge/used%20by-agent--wiki-blue)](https://github.com/wmyung/agent-wiki)
[![Multi-agent UI](https://img.shields.io/badge/multi--agent%20UI-memento--multiagent-6f42c1)](https://github.com/wmyung/memento-multiagent)

MEMENTO is a **two-system memory** for AI agents:

- **A fast fact store** (SQLite + FTS5) — preferences, config, quick facts. Auto-saves every session. Sub-millisecond recall.
- **A deep knowledge base** (Git + Markdown) — procedures, documentation, research notes. Agent asks before saving.
- **A keyword bridge** connecting them — facts carry wiki references. When you need depth, it finds the fact and retrieves the corresponding wiki page.

`pip install memento-memory` and `memento init`. No vector DB. No embeddings. No Docker.

MEMENTO runs on a single local machine. You do **not** need a VM or server unless you want persistent remote agents or team infrastructure.

For a browser control plane that lets humans view, edit, quarantine, and manage memory and skills across Codex, Claude, Hermes, and other agents, see **[wmyung/memento-multiagent](https://github.com/wmyung/memento-multiagent)**.

---

## Related Projects

- **[wmyung/memento](https://github.com/wmyung/memento)** — this lightweight memory core: SQLite fact store, Git/Markdown wiki, keyword bridge, decisions, artifacts, and experiences.
- **[wmyung/memento-multiagent](https://github.com/wmyung/memento-multiagent)** — optional multi-agent layer: browser control plane, agent registry, skill visibility, memory cleanup, and privacy review.

---

## Production Users

MEMENTO's architecture is deployed in production as **Hermes Agent's shared memory system** — a 6-agent multi-agent setup managing biomedical research pipelines across 2 machines (GCP VM + local GPU server).

- **[wmyung/agent-wiki](https://github.com/wmyung/agent-wiki)** — 6-agent shared wiki deployed on GCP (3 agents) and a local GPU server (3 agents), connected via git sync and MEMENTO-style keyword bridge.

The agent-wiki implements the exact same ME Complex + Wiki Complex + keyword bridge pattern, with auto-push cron (2h), deploy-key-based access, and SOUL.md/AGENTS.md integration.

---

## Why Two Systems?

| | Fact Store (SQLite) | Knowledge Base (Wiki) |
|---|---|---|
| **What it stores** | Simple facts, preferences, config | Procedures, docs, research notes |
| **Storage** | SQLite single file, FTS5 search | Markdown files, Git version control |
| **Latency** | ~1–5ms | ~50ms to ~2s |
| **Entry size** | ~2KB average | 1KB–100KB per page |
| **History** | Last-updated timestamp | Full git history |
| **Write policy** | Auto-saves every session | Agent asks user before writing |

Facts and knowledge are different. A flat fact DB works for *"what's the user's name?"* but not for *"how does the pipeline work step by step?"* MEMENTO gives you both in one CLI.

---

## Comparison with Alternatives

| Feature | **MEMENTO** | mem0 | LangMem | ClawMemory | AgentMemory |
|---|---|---|---|---|---|
| **Embeddings required** | ❌ No | ✅ Yes | ✅ Yes | ❌ No | Optional |
| **Wiki / knowledge base** | ✅ Git-backed | ❌ | ❌ | ❌ | ❌ |
| **Fact ↔ Knowledge bridge** | ✅ Keywords | ❌ | ❌ | ❌ | ❌ |
| **1-hop / 2-hop recall** | ✅ Trigger-based | ❌ | ❌ | ❌ | ❌ |
| **Multi-agent sharing** | ✅ Built-in | Cloud-only | LangGraph | ❌ | ❌ |
| **Dependencies** | Python stdlib + SQLite | 10+ packages | LangChain stack | Go + SQLite | Python + SQLite |
| **Setup time** | 10 seconds | 30 min + key | 15 min + key | 5 min | 2 min |
| **Offline** | ✅ Fully | ❌ (API) | Partial | ✅ | ✅ |
| **Git history** | ✅ Wiki has it | ❌ | ❌ | ❌ | ❌ |
| **Framework lock-in** | ❌ None | ❌ None | ✅ LangChain | ✅ OpenClaw | ❌ None |

---

## Quick Start

```bash
pip install memento-memory
memento init

# Store a fact (auto-saved)
memento remember "Python 3.11, SQLite with WAL mode" --category config

# Search facts (1-hop, ~5ms)
memento recall "Python version"

# Create a wiki page (agent asks user first)
memento wiki create docs/deployment-guide

# Deep recall: fact → keyword → wiki (2-hop, ~50ms)
memento deep-recall "deployment"

# Track artifacts
memento artifact add ./diagram.png --desc "Architecture overview" --tags "docs,fig1"

# Record decisions
memento decide "deployment target" "Docker + AWS ECS" --rationale "cost efficiency"

# Log experiences (successes, failures, lessons)
memento experience add success "Deployment automation" --domain devops --lesson "Use health checks"
memento experience add failure "Missed edge case in config" --domain devops --severity 4
memento experience recall "deployment"

# Semantic graph
memento tag add "mem:config" "deployment"
memento relate "mem:config" "mem:decision-1" "informs"
memento trace "mem:config"
```

---

## For AI Agents

### Write policy

| Store | Policy |
|-------|--------|
| **Fact Store** | Auto-save every session. Do not ask user. Store facts proactively. |
| **Knowledge Base** | **Ask user before writing.** `memento wiki create <slug>` only after user confirms. |
| **Experiences** | Ask user before storing success/failure/lesson entries. |

### Recall protocol

| User says | You do | Store |
|-----------|--------|-------|
| "What was that thing?" / "do you remember" | `memento recall <query>` | Fact store only |
| "Tell me more" / "go deeper" / "remember in detail" | `memento deep-recall <query>` | Fact → keyword → Wiki |
| "Where's that file?" | `memento artifact list --tag <tag>` | SQLite Suite |
| "How did this project unfold?" | `memento timeline <uri>` | L3 temporal graph |

### What to register in SOUL.md or AGENTS.md

```markdown
## Memory

MEMENTO at `~/memento/` (or `memento` in PATH).

- **Fact Store**: `memento recall <query>` — auto-saved, no permission needed
- **Wiki**: `memento wiki search <query>` — agent asks before creating
- **Deep recall**: `memento deep-recall <query>` — 2-hop fact → keyword → wiki
- **Keyword bridge**: always add `--keywords "wiki:slug"` when storing facts that have a wiki page
- **Decisions**: `memento decide <topic> <decision> --rationale <reason>`
- **Experiences**: `memento experience add <type> <summary> [--lesson <text>]` — ask user first
- **Semantic graph**: `memento tag/relate/trace` for cross-linking
```

### Best practices

- Store facts atomically: one `memento remember` per fact, not paragraphs
- Use categories: `--category preference`, `--category config`, `--category entity`, `--category finding`
- Always add `--keywords "wiki:relevant-slug"` when a wiki page exists for the fact
- Tag artifacts by project: `--tags "project-alpha,backend,fig1"`
- Log every decision with rationale: `memento decide <topic> <decision> --rationale <why>`
- Connect related facts: `memento relate <source> <target> "informs"`

**Agent guidelines:** auto-save facts, ask before wiki write, log decisions and experiences.

## MCP Integration (Optional)

MEMENTO can run as an MCP (Model Context Protocol) server, allowing Claude Code, Codex CLI, Cursor, or any MCP-compatible client to use its memory tools directly.

```bash
# Stdio mode (for Claude Code config)
memento mcp

# HTTP SSE mode (for remote access)
memento mcp --port 8765
```

**Claude Code configuration (`~/.claude.json`):**
```json
{
  "mcpServers": {
    "memento": {
      "command": "memento",
      "args": ["mcp"]
    }
  }
}
```

**Tools exposed via MCP:**
`memento_recall`, `memento_deep_recall`, `memento_remember`, `memento_wiki_search`, `memento_decide`, `memento_artifact_add`, `memento_experience_add`, `memento_tag`, `memento_relate`, `memento_timeline`, `memento_status`

## Keyword Bridge

```
Fact entry:
  "Deployment uses Docker + ECS with blue-green strategy"
  keywords: "wiki:deployment-strategy wiki:aws-ecs"

memento deep-recall "deployment strategy"
  → Hop 1: Fact store → finds entry, extracts "wiki:deployment-strategy"
  → Hop 2: Wiki search → returns docs/deployment-strategy.md (full guide)
```

**Why keywords, not links:**
- Wiki page renames → FTS still finds them
- One fact → multiple wiki pages, multiple facts → same wiki page
- Zero maintenance overhead — keywords are just strings

---

## For Wiki LLM Users

If you currently use [WikiLLM](https://github.com/wmyung/hermes-wiki) (raw/sources/analysis pipeline), MEMENTO adds a **token-efficient fact layer** alongside it.

| | WikiLLM alone | + MEMENTO fact store |
|---|---|---|
| **Write cost** | LLM summarizes + categorizes + links + structures | LLM extracts fact, simple INSERT |
| **Write latency** | Seconds (full LLM call) | ~5ms |
| **Write policy** | Agent asks, thinks, curates | Auto-save every session |
| **Read latency** | ~50–500ms (grep markdown) | ~5ms (FTS5 BM25) |
| **Best for** | Deep knowledge: docs, analysis, procedures | Quick facts: preferences, config, entities |

**The key asymmetry:** Both systems use LLM processing to write. But a wiki page requires the LLM to summarize, categorize, link to existing pages, and maintain structure — a full knowledge curation pass. A fact store write just needs the LLM to extract the key fact — lighter processing, same extraction context.

Facts should be auto-saved because they're cheaper to write. Wiki pages should be curated because they cost more to produce well. The keyword bridge connects both: facts carry `wiki:slug` references, so a quick `memento deep-recall` retrieves the full wiki page when you need depth.

## Feature Comparison: MEMENTO vs Original Hermes Tools

MEMENTO replaces `sqlite-suitectl`, `memory_enhancer_*`, and `memory_l3.py` with one unified CLI.

| Feature | Original Tool | MEMENTO | Status |
|---------|--------------|---------|--------|
| Fact storage | `memory_enhancer_remember` | `memento remember` | ✅ |
| Fact search | `memory_enhancer_search` | `memento recall` | ✅ |
| Deep recall (fact→wiki) | — (new) | `memento deep-recall` | ✅ **New** |
| Wiki search | manual grep | `memento wiki search` | ✅ |
| Wiki create | manual edit | `memento wiki create` | ✅ |
| L3 tags | `memory_l3.py tag add` | `memento tag` | ✅ |
| L3 relations | `memory_l3.py relate` | `memento relate` | ✅ |
| L3 trace | `memory_l3.py trace` | `memento trace` | ✅ |
| Artifact registry | `sqlite-suitectl artifact add` | `memento artifact add` | ✅ |
| Decision log | `sqlite-suitectl decide` | `memento decide` | ✅ |
| Experience tracking | `sqlite-suitectl experience add` | `memento experience add` | ✅ |
| DB status | `sqlite-suitectl status` | `memento status` | ✅ |
| Cache stats | `sqlite-suitectl cache-stats` | ❌ | Planned |
| Cache clear | `sqlite-suitectl cache-clear` | ❌ | Planned |
| Experience stats | `sqlite-suitectl experience stats` | ❌ | Planned |
| Raw SQL query | `sqlite-suitectl query` | ❌ | Planned (use `sqlite3` directly) |

## Time Concepts

MEMENTO treats time as a first-class dimension across all layers:

| Layer | Time Field | Purpose |
|-------|-----------|---------|
| Fact store | `created_at`, `updated_at`, `access_count` | Know when a fact was stored, last updated, how often used |
| Fact store | `ttl` (time-to-live) | Auto-expire temporary facts (0 = permanent) |
| L3 graph | `precedes` / `follows` relations | Chronological ordering of events, projects, decisions |
| L3 graph | `contemporaneous` relation | Events that happened at the same time |
| L3 graph | `timeline <uri>` command | Walks temporal chains to reconstruct order |
| Experiences | `created_at`, `last_encountered_at` | Track when patterns occurred and recurred |
| Experiences | `recurrence_count` | Count how many times a failure/lesson repeated |

**Timeline example:**

```bash
memento relate "mem:project-init" "mem:research-phase" "precedes"
memento relate "mem:research-phase" "mem:analysis-phase" "precedes"
memento relate "mem:analysis-phase" "mem:writeup" "precedes"

memento timeline "mem:project-init"
# 1. mem:project-init
# 2. mem:research-phase
# 3. mem:analysis-phase
# 4. mem:writeup
```

## CLI Reference

```
  init                    Initialize databases + wiki structure
  status                  Layer statistics

  Fact Store:
  ───────────────────────
  remember <text> [--keywords k] [--category c]
  recall <query>

  Knowledge Base:
  ───────────────────────
  wiki create <slug>      (agent: ask user first!)
  wiki search <query>
  deep-recall <query>

  SQLite Suite:
  ───────────────────────
  artifact add <path> [--desc d] [--tags t]
  artifact list [--tag t]
  decide <topic> <decision> [--rationale r]
  decisions [--topic t]
  experience add <type> <summary> [--domain d] [--lesson l] [--tags t] [--severity <1-5>]
  experience recall <query>
  experience list [--type success|failure|correction|lesson]

  Semantic Graph:
  ────────────────────
  tag <uri> <tag>
  tag-search <tag>
  relate <source> <target> [type]
  trace <uri>

  Upgrade:
  ────────────────────
  upgrade                 Migrate from Hermes sqlite-suitectl
  upgrade --dry-run       Preview without changes
```

---

## Architecture

```
                    ┌───────────────────────┐
                    │     Agent (any LLM)    │
                    └───────┬───────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
     ┌────────────────┐         ┌──────────────────┐
     │  Fact Store     │         │  Knowledge Base   │
     │  (SQLite)       │◄─keyword─│  (Markdown + Git) │
     │  FTS5 search    │  bridge  │  Git versioned    │
     │  Auto-save      │         │  Ask before write  │
     └───────┬─────────┘         └──────┬───────────┘
             │                          │
             └────── L3 Semantic Graph ──┘
                  (tags + relations)

        + SQLite Suite: tool_cache, artifacts, decisions, experiences
        + memento-sync: master → replica (scp/cron)
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design: 3 internal layers per store, L3 graph, sync protocol.

---

## Upgrade from Hermes sqlite-suitectl

MEMENTO uses the **exact same SQLite schemas** as Hermes Agent's memory tools.

```bash
pip install memento-memory
memento upgrade --dry-run   # Preview (no changes)
memento upgrade              # Migrate data to ~/.memento/
memento status               # Verify all layers
```

Your original Hermes data is preserved. Both systems can run side by side. Rollback: delete `~/.memento/`.

---

## Keywords for Discovery

`agent memory`, `AI agent memory`, `multi-agent memory`, `SQLite knowledge base`, `LLM knowledge base`, `agent knowledge management`, `AI memory system`, `vector database alternative`, `no-embedding memory`, `agent knowledge base`, `AI wiki`, `SQLite FTS5 memory`, `BM25 agent memory`, `agent long-term memory`, `persistent memory for AI agents`, `local AI memory`, `offline agent memory`, `Hermes Agent memory`, `Claude Code memory`, `Codex CLI memory`, `AI agent tools`, `LLM tool memory`, `agentic memory`, `memory for AI assistants`, `structure memory AI`, `AI agent long-term memory`, `knowledge graph agent`, `fact store AI`, `agent memory database`, `SQLite for AI agents`, `markdown knowledge base`, `git wiki agent`, `AI research memory`, `paper memory system`, `academic AI memory`, `multi-agent knowledge sharing`, `agent memory without vector DB`, `lightweight agent memory`, `Python agent memory`, `CLI agent memory`, `MCP memory server`, `Claude memory tool`, `AI memory manager`, `agent memory pipeline`, `episodic memory AI`, `semantic memory AI`

---

## License

MIT

---

*MEMENTO — because agents should remember both what you said and how to do it.*
