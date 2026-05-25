# MEMENTO

**The SQLite Wiki Memory — facts you can search, knowledge you can read.**

[![PyPI](https://img.shields.io/pypi/v/memento-memory)](https://pypi.org/project/memento-memory/)
[![Python](https://img.shields.io/pypi/pyversions/memento-memory)](https://pypi.org/project/memento-memory/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

MEMENTO is a **two-system memory** for AI agents:

- **A fast fact store** (SQLite + FTS5) — preferences, config, quick facts. Auto-saves every session. Sub-millisecond recall.
- **A deep knowledge base** (Git + Markdown) — procedures, documentation, research notes. Agent asks before saving.
- **A keyword bridge** connecting them — facts carry wiki references. When you need depth, it finds the fact and retrieves the corresponding wiki page.

`pip install memento-memory` and `memento init`. No vector DB. No embeddings. No Docker.

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

---

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

If you currently use [WikiLLM](https://github.com/wmyung/hermes-wiki) (Markdown wiki with raw/sources/analysis pipeline), MEMENTO adds the missing half: **a fast fact store.**

| What you have (WikiLLM) | What MEMENTO adds |
|--------------------------|-------------------|
| Deep knowledge (procedures, docs) | Quick facts (preferences, config, entities) — **~5ms recall** |
| Git versioned, human-readable | SQLite FTS5, agent-searchable |
| LLM-curated (raw→sources→analysis) | Auto-saved every session, no permission needed |
| Manual wiki search (`grep`) | `memento recall` — BM25 semantic search |
| Knowledge isolation | **Keyword bridge** connects facts to wiki pages |
| Single-agent | **Multi-agent**: shared fact store + shared wiki |

**The key asymmetry:** WikiLLM is optimized for *reading and writing deep knowledge*, which requires human/LLM effort. But most agent memory needs are *quick facts* ("what Python version?", "what's the config path?", "who is the user?"). These don't belong in a wiki — they belong in a searchable fact store.

MEMENTO gives you both, and the keyword bridge connects them.

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

`agent memory`, `AI agent memory`, `multi-agent memory`, `SQLite knowledge base`, `LLM knowledge base`, `agent knowledge management`, `AI memory system`, `vector database alternative`, `no-embedding memory`, `agent knowledge base`, `AI wiki`, `SQLite FTS5 memory`, `BM25 agent memory`, `agent long-term memory`, `persistent memory for AI agents`, `local AI memory`, `offline agent memory`, `Heremes Agent memory`, `Claude Code memory`, `Codex CLI memory`

---

## License

MIT

---

*MEMENTO — because agents should remember both what you said and how to do it.*
