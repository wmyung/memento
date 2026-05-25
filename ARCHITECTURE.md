# MEMENTO Architecture

## Design Philosophy

MEMENTO is built on a simple observation: **facts and knowledge are fundamentally different.**

| | Facts | Knowledge |
|---|---|---|
| Nature | Atomic, immutable | Structural, evolving |
| Example | "User prefers coffee" | "GWAS pipeline: QC → imputation → association testing" |
| Query pattern | "What is X?" | "How to do X?" |
| Update pattern | Append, correct | Revise, expand, restructure |
| Ideal storage | Key-value with search | Document with version control |

Most agent memory systems (mem0, Chroma, ClawMemory) treat both the same way — embed everything into vectors or stuff everything into a fact DB. MEMENTO splits them into two parallel storage complexes optimized for each purpose, connected by a keyword bridge.

## Two Parallel Complexes

```
                    ┌───────────────────────┐
                    │     Agent (any LLM)    │
                    │  memento recall/search │
                    └───────┬───────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
     ┌────────────────────┐    ┌──────────────────────┐
     │    ME Complex       │    │   Wiki Complex        │
     │   (Fact Store)      │    │  (Knowledge Base)     │
     │                     │    │                       │
     │  ~/.memento/        │    │  ~/wiki/              │
     │  memory.sqlite3     │    │  Markdown + Git       │
     │                     │    │                       │
     │  ┌───────────────┐  │    │  ┌─────────────────┐  │
     │  │ L0: raw facts  │  │    │  │ L0: raw/        │  │
     │  │ (FTS5-indexed) │  │    │  │ (immutable      │  │
     │  │                │  │    │  │  source materia)│  │
     │  ├───────────────┤  │    │  ├─────────────────┤  │
     │  │ L1: structured│  │    │  │ L1: sources/    │  │
     │  │ (category,    │  │    │  │ (per-source      │  │
     │  │  keywords)    │  │    │  │  summaries)      │  │
     │  ├───────────────┤  │    │  ├─────────────────┤  │
     │  │ L2: semantic  │  │    │  │ L2: analysis/   │  │
     │  │ (tags +       │  │    │  │ (cross-source    │  │
     │  │  relations)   │  │    │  │  synthesis)      │  │
     │  └───────────────┘  │    │  └─────────────────┘  │
     └─────────┬──────────┘    └──────────┬─────────────┘
               │                          │
               └────────── keyword bridge ──────────┘
                          (wiki:slug tokens
                           in fact keywords)

  L3 Semantic Graph (spans both stores):
    l3_tags, l3_relations tables
    "mem:b003" ──precedes──▶ "mem:b004"
    "mem:b003" ──tag──▶ "mixer"
```

## The Keyword Bridge

This is MEMENTO's core innovation — a simple but effective way to connect fast facts to deep knowledge.

### How it works

1. **Storage side**: When saving a fact, the agent may add `wiki:slug` tokens in the `keywords` field:
   ```bash
   memento remember "B003 uses trivariate MiXeR" --keywords "wiki:b003-mixer wiki:heritability"
   ```

2. **Normal recall (1-hop)**: Standard query hits only the fact store:
   ```bash
   memento recall "B003"
   # → "B003 uses trivariate MiXeR" (5ms)
   ```

3. **Deep recall (2-hop)**: When the agent or user signals "need details", MEMENTO:
   ```
   memento deep-recall "B003 pipeline"
   # Hop 1: Fact store → "B003 uses trivariate MiXeR"
   #         keywords: "wiki:b003-mixer"
   # Hop 2: Wiki search → wiki/analysis/b003-mixer.md
   #         (full pipeline with code, parameters, results)
   ```

### Advantages over alternatives

| Approach | Problem | Our solution |
|----------|---------|--------------|
| Hard links (URIs) | Break on rename | Keywords survive renames (FTS finds them) |
| Full-text search only | Slow on large fact stores | FTS5 BM25 on facts (~5ms), grep on wiki (~50ms) |
| Embeddings | Heavy infra, cost, offline-unfriendly | Zero deps, fully offline |
| Manual cross-referencing | Agents forget | Convention: always add `wiki:` keywords |

## ME Complex (Fact Store)

### Schema

The fact store is a single SQLite file at `~/.memento/memory.sqlite3`:

```sql
-- L0: Raw facts with FTS5 full-text search
CREATE TABLE memories (
    id            TEXT PRIMARY KEY,          -- "mem:1700000000"
    content       TEXT NOT NULL,             -- fact text
    category      TEXT DEFAULT '',           -- preference|config|entity|finding
    keywords      TEXT DEFAULT '',           -- "wiki:slug wiki:other-slug"
    created_at    INTEGER NOT NULL,
    updated_at    INTEGER NOT NULL,
    access_count  INTEGER DEFAULT 0,
    agent_name    TEXT DEFAULT '',
    ttl           INTEGER DEFAULT 0          -- 0 = permanent
);

-- FTS5 virtual table for BM25 search
CREATE VIRTUAL TABLE memories_fts USING fts5(
    content, keywords, category,
    content='memories', content_rowid='rowid'
);

-- L2: Semantic tags
CREATE TABLE l3_tags (
    id         INTEGER PRIMARY KEY,
    uri        TEXT NOT NULL,                -- references any memory URI
    tag        TEXT NOT NULL,
    created_at INTEGER NOT NULL
);

-- L2: Typed relations
CREATE TABLE l3_relations (
    id            INTEGER PRIMARY KEY,
    source_uri    TEXT NOT NULL,
    target_uri    TEXT NOT NULL,
    relation_type TEXT NOT NULL,             -- informs|supports|contradicts|extends|built-from|related_to|precedes|follows|contemporaneous
    created_at    INTEGER NOT NULL
);
```

### Design decisions

- **FTS5 instead of embeddings**: BM25 ranking is surprisingly effective for agent memory queries. Most queries are keyword-based ("Python version", "coffee preference", "GWAS pipeline"). When you need fuzzy search, add it as a plugin — the core doesn't depend on it.
- **WAL mode**: Multiple agents can read concurrently without write contention.
- **No schema migrations**: Simple enough that we don't need them. Add columns as needed.

## Wiki Complex (Knowledge Base)

### Directory structure

```
~/wiki/
├── index.md              # Table of contents
├── log.md                # Change log
├── overview.md           # High-level synthesis
├── raw/                  # L0: Immutable source materials
│   ├── paper-notes/      #   One subdir per source type
│   └── meeting-notes/
├── sources/              # L1: Source summaries
│   └── <slug>.md         #   One page per paper/report/note
├── concepts/             # Concepts, methods, terminology
│   ├── gwas.md
│   └── mixer.md
├── analysis/             # L2: Cross-source synthesis
│   └── b003-mixer.md     #   Combined analysis of multiple sources
└── entities/             # People, institutions, cohorts
    └── woojae-myung.md
```

### Data flow

```
New material
    │
    ▼
raw/ (immutable, agent writes)
    │
    ▼  (LLM summarizes)
sources/ (one page per source, agent curates)
    │
    ▼  (LLM synthesizes across sources)
analysis/ (cross-source insights, agent refines)
    │
    └── concepts/ + entities/ (cross-cutting, updated as needed)
```

## SQLite Suite (Operational Storage)

A separate SQLite file at `~/.memento/agent.db` for operational data that doesn't belong in the fact store:

| Table | Purpose | Use case |
|-------|---------|----------|
| `tool_cache` | API call deduplication | Cache web_search results (TTL-based) |
| `artifacts` | File registry | Track generated plots, tables, reports |
| `decisions` | Decision log | Record methodological choices |
| `experiences` | Learning from mistakes | Store success/failure patterns |

These tables have the **same schema** as the original Hermes `sqlite-suitectl` for backward compatibility.

## L3 Semantic Graph (Cross-Layer)

Tags and relations span both fact store and wiki. The `l3_tags` and `l3_relations` tables in `memory.sqlite3` reference URIs from any layer:

```
"mem:b003" ──precedes──▶ "mem:b004"       (temporal: B003 came before B004)
"mem:b003" ──built-from──▶ "mem:b001"     (structural: B003 depends on B001)
"wiki://mixer" ──informs──▶ "mem:b003"    (cross-layer: wiki page informs a fact)
```

**Use cases:**
- **Timeline reconstruction**: trace `precedes` chains to rebuild project history
- **Impact analysis**: find all facts informed by a wiki page
- **Knowledge discovery**: traverse `related_to` to find unexpected connections

## Sync Architecture (Multi-Host)

```
Master (main host)
├── ME DB ──scp (cron */5)────▶ Replica (secondary host)
├── Wiki ──git push/pull────────▶ All agents (bidirectional)
└── OP DB ──per-agent──────────▶ (no cross-host sync)
```

- **ME DB**: Single-direction sync (master → replica). SQLite file is small enough for cron-based scp.
- **Wiki**: Bidirectional via git. Each agent has its own SSH deploy key. Merge conflicts resolved via standard git workflows.
- **OP DB**: Per-agent by default. No cross-host sync (operational data is agent-specific).

## Trigger-Based Recall Depth

MEMENTO uses a simple protocol to decide how deep to search:

| Trigger | Depth | Latency | What happens |
|---------|-------|---------|--------------|
| Normal query | 1-hop | ~5ms | Fact store only (FTS5 BM25) |
| "tell me more" / deep recall | 2-hop | ~50ms | Fact store → extract keywords → wiki search |

This prevents unnecessary wiki lookups for simple factual queries while enabling deep knowledge retrieval when needed.

## Upgrade Path from Hermes sqlite-suitectl

MEMENTO uses the **exact same SQLite schemas** as Hermes Agent's:
- `memory_enhancer_*` → ME Complex (`memory.sqlite3`)
- `sqlite-suitectl` → SQLite Suite (`agent.db`)
- `memory_l3.py` → L3 tags/relations (same `memory.sqlite3`)

This means:
1. Your existing data is 100% compatible
2. You can run MEMENTO and Hermes tools side by side
3. Migration is a simple `cp` — no schema changes needed
4. Rollback is trivial — just delete `~/.memento/`

## Performance Characteristics

| Operation | Latency | Dependencies |
|-----------|---------|--------------|
| `memento init` | ~100ms | Python, SQLite |
| `memento remember` | ~5ms | Python, SQLite |
| `memento recall` (1-hop) | ~5ms | Python, SQLite (FTS5) |
| `memento deep-recall` (2-hop) | ~50ms | Python, SQLite, grep |
| `memento wiki search` | ~50ms | Python, grep |
| `memento artifact add` | ~10ms | Python, SQLite, file I/O |
| `memento status` | ~10ms | Python, SQLite |
| `memento tag/relate` | ~5ms | Python, SQLite |

All operations work offline. No network calls. No API keys. No docker containers.

## Why Not Embeddings?

Vector embeddings add complexity without proportional benefit for agent memory:

| Concern | With embeddings | Without (BM25 FTS5) |
|---------|----------------|---------------------|
| Setup | Install model + server + API | Python stdlib + SQLite |
| Latency | ~500ms–3s (embed + search) | ~5ms (FTS5 BM25) |
| Cost | $/token or GPU | $0 |
| Offline | Limited (model download) | Fully offline |
| Maintenance | Model updates, index rebuilds | None |
| Accuracy | Good for fuzzy semantic queries | Excellent for keyword queries |

Agent memory queries are mostly keyword-based ("Python version", "SQLite WAL", "GWAS pipeline"). For the rare case where you need fuzzy semantic search, add an embedding provider as a plugin — MEMENTO's fact store is designed to accommodate optional vector columns without changing the core API.

## Keywords for Discovery

`agent memory architecture`, `multi-agent memory system`, `SQLite knowledge base`, `AI agent long-term memory`, `memory stack for LLM agents`, `vector database alternative`, `local AI memory`, `privacy-first memory`, `offline agent memory`, `Hermes Agent memory`, `Claude Code memory`, `Codex memory plugin`
