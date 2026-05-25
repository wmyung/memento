# MEMENTO

**SQLite + Wiki memory for AI agents. No vector DB. No embeddings. Just facts and knowledge, connected.**

[![PyPI](https://img.shields.io/pypi/v/memento-memory)](https://pypi.org/project/memento-memory/)
[![Python](https://img.shields.io/pypi/pyversions/memento-memory)](https://pypi.org/project/memento-memory/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub stars](https://img.shields.io/github/stars/wmyung/memento)](https://github.com/wmyung/memento)

MEMENTO is a **two-system memory** for AI agents. It gives you:

- **A fast fact store** (SQLite + FTS5) — preferences, names, quick facts, configuration. Sub-millisecond recall.
- **A deep knowledge base** (Git + Markdown) — procedures, analyses, literature notes, research pipelines. Versioned, human-readable, LLM-curated.
- **A keyword bridge** connecting them — facts carry `wiki:slug` tokens. When you need depth ("잘 기억해봐"), it finds the fact, extracts the keyword, and retrieves the full wiki page.

**Why MEMENTO?** Existing agent memory systems (mem0, Chroma, ClawMemory, LangMem) store everything in one flat database. That works for *"what's the user's name?"* but fails for *"how does the GWAS analysis pipeline work step by step?"* Facts and knowledge are fundamentally different — MEMENTO gives you both.

**Zero dependencies.** `pip install memento-memory` and `memento init`. No Docker. No OpenAI key. No embedding model.

---

## Table of Contents

- [Why Two Systems?](#why-two-systems)
- [Comparison with Alternatives](#comparison-with-alternatives)
- [Quick Start](#quick-start)
- [For AI Agents](#for-ai-agents)
- [Keyword Bridge: How Facts Connect to Knowledge](#keyword-bridge-how-facts-connect-to-knowledge)
- [Architecture](#architecture)
- [CLI Reference](#cli-reference)
- [Upgrade from Hermes sqlite-suitectl](#upgrade-from-hermes-sqlite-suitectl)
- [Multi-Agent Setup](#multi-agent-setup)
- [Roadmap](#roadmap)
- [License](#license)

---

## Why Two Systems?

| | Fact Store (ME Complex) | Knowledge Base (Wiki Complex) |
|---|---|---|
| **What it stores** | Preferences, config, quick facts, entity info | Procedures, research notes, analysis pipelines, literature |
| **Storage** | SQLite single file, FTS5 full-text search | Markdown files, Git version control |
| **Query latency** | ~1–5ms (BM25) | ~10ms (grep) to ~2s (LLM synthesis) |
| **Entry size** | ~2KB average | 1KB–100KB per page |
| **History** | Last-updated timestamp | Full git history: blame, diff, log, branch |
| **Human readable** | Requires SQLite browser | Any text editor, GitHub UI |
| **Sharing** | Master–replica sync (scp/cron) | Git push/pull (every agent) |

**The key insight:** Facts are atomic and immutable ("coffee preference = americano"). Knowledge is structural and evolving ("GWAS pipeline v3 → v4 with QC changes"). One database cannot serve both well.

---

## Comparison with Alternatives

| Feature | **MEMENTO** | mem0 | LangMem | ClawMemory | AgentMemory | ChromaDB |
|---|---|---|---|---|---|---|
| **Embeddings required** | ❌ No | ✅ Yes | ✅ Yes | ❌ No | Optional | ✅ Yes |
| **Wiki / knowledge base** | ✅ Git-backed | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Fact ↔ Knowledge bridge** | ✅ Keywords | ❌ | ❌ | ❌ | ❌ | ❌ |
| **1-hop / 2-hop recall** | ✅ Trigger-based | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Multi-agent sharing** | ✅ Built-in | Cloud-only | LangGraph | ❌ | ❌ | ❌ |
| **Dependencies** | Python stdlib + SQLite | 10+ packages | LangChain stack | Go + SQLite | Python + SQLite | 5+ packages |
| **Setup time** | 10 seconds | 30 min + API key | 15 min + API key | 5 min | 2 min | 10 min + server |
| **Offline** | ✅ Fully | ❌ (API) | Partial | ✅ | ✅ | ✅ |
| **Git history** | ✅ Wiki is git | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Data transparency** | ✅ Full SQL + Markdown | ❌ Opaque API | ✅ LangGraph store | ✅ SQLite | ✅ SQLite | ✅ SQLite |
| **Framework lock-in** | ❌ None | ❌ None | ✅ LangChain | ✅ OpenClaw | ❌ None | ❌ None |

**MEMENTO is the only agent memory system that includes a wiki.** Not a vector store, not a fact DB — a real, Git-backed, LLM-curated knowledge base alongside a fast fact store.

---

## Quick Start

```bash
# Install — zero dependencies beyond Python 3.8+ and SQLite
pip install memento-memory

# Or from source
git clone https://github.com/wmyung/memento.git
cd memento
make install

# Initialize databases and wiki structure
memento init

# ── Store a fact ──
memento remember "The project uses Python 3.11 and SQLite with WAL mode" \
  --category config \
  --keywords "wiki:tech-stack"

# ── Search facts (1-hop, ~5ms) ──
memento recall "Python version"

# ── Create a wiki page ──
memento wiki create analysis/gwas-pipeline-v3

# ── Deep recall: fact → keyword → wiki (2-hop, ~50ms) ──
# Use this when you need detailed, procedural knowledge
memento deep-recall "tech stack"

# ── Track artifacts (plots, tables, reports) ──
memento artifact add ./figures/manhattan.png --desc "GWAS Manhattan plot" --tags "gwas,analysis,fig1"

# ── Record decisions (for future traceability) ──
memento decide "imputation method" "Beagle 5.4" --rationale "best accuracy for Asian populations"

# ── Semantic graph: tag and relate memories ──
memento tag add "mem:b003" "mixer"
memento relate "mem:b003" "mem:b004" "precedes"
memento trace "mem:b003"

# ── Status overview ──
memento status
```

---

## For AI Agents

### What to register in your SOUL.md or AGENTS.md after setup

```markdown
## Memory System

MEMENTO is installed at `~/memento` (or `memento` in PATH).

### Two memory stores

1. **Fact Store (ME Complex)** — `memento recall <query>`
   - Use for: user preferences, simple facts, configuration, quick lookups
   - Latency: ~5ms
   - Storage: `~/.memento/memory.sqlite3` (SQLite + FTS5)

2. **Knowledge Base (Wiki Complex)** — `memento wiki search <query>`
   - Use for: procedures, analysis pipelines, literature notes, research methods
   - Latency: ~50ms
   - Storage: `~/wiki/` (Markdown + Git)

### Recall protocol

| User says | You do |
|-----------|--------|
| "기억나?" / "뭐였지?" | `memento recall <query>` — 1-hop, fact store only |
| "잘 기억해봐" / "자세히" / "어떻게 했지?" | `memento deep-recall <query>` — 2-hop, fact → keyword → wiki |
| "어디 저장했지?" / "파일 찾아줘" | `memento artifact list --tag <tag>` |

### Always include keywords when storing facts

When you use `memento remember`, always add `--keywords "wiki:relevant-page"` if there's a corresponding wiki page. This is what enables the deep recall bridge.

### Best practices

- **Store facts atomically**: one `memento remember` per fact. Not paragraphs.
- **Use categories**: `--category preference`, `--category config`, `--category entity`, `--category finding`
- **Tag artifacts by project**: `--tags "project-b003,gwas,mixer"`
- **Log every decision**: `memento decide <topic> <decision> --rationale <why>`
- **Connect related memories**: `memento relate <source> <target> "informs"` or `"precedes"`
- **Revisit the wiki weekly**: consolidate raw notes into structured analysis pages
```

---

## Keyword Bridge: How Facts Connect to Knowledge

The keyword bridge is MEMENTO's core innovation.

```
Fact entry (in SQLite):
  "B003 = MDD Trivariate MiXeR. Joint analysis of 3 phenotypes."
  keywords: "wiki:b003-mixer wiki:mdd-trivariate wiki:heritability"

When you call `memento deep-recall "B003 pipeline"`:

  Hop 1 (5ms)
  └→ Fact store FTS5 search → finds the entry
     └→ Extracts keywords: ["b003-mixer", "mdd-trivariate", "heritability"]

  Hop 2 (50ms)
  └→ Wiki full-text search for "b003-mixer"
     └→ Returns wiki/analysis/b003-mixer.md (full pipeline with code, parameters, results)
```

**Advantages over hard links:**
- Wiki page renames → FTS still finds it
- One fact entry can point to multiple wiki pages
- Multiple facts can cluster around the same wiki page
- No maintenance overhead — keywords are just strings

**When to use keywords:**
- Any fact that describes *how to do something* → add `--keywords "wiki:procedure-name"`
- Any fact that references a research result → add `--keywords "wiki:paper-slug"`
- Any fact that belongs to a project → add `--keywords "wiki:project-name"`

---

## Architecture

```
                    ┌───────────────────────┐
                    │     Agent (any LLM)    │
                    │  memento recall/search │
                    └───────┬───────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
     ┌────────────────┐         ┌──────────────────┐
     │  Fact Store     │         │  Knowledge Base   │
     │  (ME Complex)   │◄─keyword─│  (Wiki Complex)   │
     │                 │  bridge  │                  │
     │  SQLite single  │         │  Markdown + Git   │
     │  file + FTS5    │         │  raw→sources→     │
     │  tags + graph   │         │  analysis pipeline│
     └───────┬─────────┘         └──────┬───────────┘
             │                          │
             └────── L3 Semantic Graph ──┘
                  (tags + relations
                   across both stores)

        + SQLite Suite: tool_cache, artifacts, decisions, experiences
        + memento-sync: master → replica DB sync
```

### Internal layers

**Fact Store (3 layers in one SQLite DB):**
| Layer | Table | Purpose |
|-------|-------|---------|
| L0 | `memories` + `memories_fts` | Raw facts, FTS5-indexed |
| L1 | `category`, `keywords` fields | Structured metadata, classification |
| L2 | `l3_tags`, `l3_relations` | Semantic tags, typed relations |

**Knowledge Base (3 layers in ~/wiki/):**
| Layer | Directory | Purpose |
|-------|-----------|---------|
| L0 | `raw/` | Immutable source materials (papers, exports, notes) |
| L1 | `sources/` | One-page-per-source summaries |
| L2 | `analysis/`, `concepts/`, `entities/` | Cross-source synthesis |

---

## CLI Reference

### Setup
```
memento init                    Initialize DBs + wiki directory structure
memento status                  Show all layer statistics
memento upgrade                 Migrate from Hermes sqlite-suitectl
memento upgrade --dry-run       Preview migration without changes
```

### Fact Store (1-hop)
```
memento remember <text> [--category <c>] [--keywords <k>]
memento recall <query>
```

### Knowledge Base (2-hop)
```
memento wiki create <slug>      Create a new wiki page (opens $EDITOR)
memento wiki search <query>     Full-text search wiki pages
memento deep-recall <query>     Fact → keyword → wiki (2-hop)
```

### Artifact & Decision Tracking
```
memento artifact add <path> [--desc <d>] [--tags <t>] [--source <s>]
memento artifact list [--tag <t>]
memento decide <topic> <decision> [--rationale <r>]
memento decisions [--topic <t>]
```

### Semantic Graph
```
memento tag <uri> <tag>          Tag any memory URI
memento tag-search <tag>         Find all URIs with a tag
memento relate <src> <tgt> [type]  Create a typed relation
memento trace <uri>              Show all relations for a URI
```

---

## Upgrade from Hermes sqlite-suitectl

If you're using Hermes Agent's `sqlite-suitectl`, `memory_enhancer_*`, or `memory_l3.py` tools, MEMENTO uses the **exact same SQLite schemas**. Your data is already compatible.

```bash
# 1. Install MEMENTO
pip install memento-memory

# 2. Preview migration (no changes)
memento upgrade --dry-run

# 3. Run migration
memento upgrade

# 4. Verify
memento status
memento recall "anything"

# 5. Update your AGENTS.md (see "For AI Agents" section above)
```

**What the migration does:**
- Copies `~/.hermes/shared_memory/memory.sqlite3` → `~/.memento/memory.sqlite3`
- Copies `~/.hermes/agent.db` → `~/.memento/agent.db`
- Symlinks existing wiki directory
- **Original files are untouched** — your Hermes setup continues to work

**Rollback:** Delete `~/.memento/` and point your tools back to `~/.hermes/`. No data is lost.

---

## Multi-Agent Setup

MEMENTO is designed for multi-agent environments from day one.

### Sharing the Fact Store (SQLite)

```bash
# On the master agent host:
memento-sync --push user@replica:~/.memento/memory.sqlite3

# Or set up cron-based sync:
echo 'mode=push
target=user@replica:~/.memento/memory.sqlite3
interval=300' > ~/.memento/sync.conf
# Then: crontab -e → */5 * * * * memento-sync
```

### Sharing the Knowledge Base (Wiki)

```bash
# All agents share the same git repo
git -C ~/wiki remote add origin git@github.com:org/shared-wiki.git
git -C ~/wiki push -u origin main

# Each agent clones:
git clone git@github.com:org/shared-wiki.git ~/wiki
```

### Agent Isolation (Optional)

```yaml
# ~/.memento/config.yaml (future)
agents:
  researcher:
    db: ~/.memento/researcher.db
    wiki: ~/wiki/research/
  coder:
    db: ~/.memento/coder.db
    wiki: ~/wiki/code/
```

Currently MEMENTO uses a single shared DB. Per-agent isolation is on the roadmap.

---

## Roadmap

- [x] **v0.1** — CLI, Fact Store, Wiki search, Keyword bridge, Artifact/Decision tracking, L3 graph, Upgrade tool
- [ ] **v0.2** — Wiki ingest command (`memento wiki ingest raw/note.md` → auto-extract → sources/ update)
- [ ] **v0.3** — LLM auto-tagging (`memento remember` suggests keywords automatically)
- [ ] **v0.4** — Per-agent DB isolation, configurable namespaces
- [ ] **v0.5** — MCP server (optional, for Claude Code / Codex CLI)
- [ ] **v1.0** — Stable API, PyPI release, full documentation

---

## Keywords for SEO

`agent memory`, `AI agent memory`, `SQLite memory`, `multi-agent memory`, `LLM knowledge base`, `agent knowledge management`, `AI memory system`, `vector database alternative`, `no-embedding memory`, `agent knowledge base`, `AI wiki`, `SQLite FTS5 memory`, `BM25 agent memory`, `agent long-term memory`, `persistent memory for AI agents`, `local AI memory`, `privacy-first agent memory`, `offline agent memory`, `Claude Code memory`, `Codex CLI memory`, `Hermes Agent memory`

---

## License

MIT. Use it, fork it, ship it.

---

*MEMENTO — because agents should remember both what you said and how to do it.*
