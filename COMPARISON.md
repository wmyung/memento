# MEMENTO vs Other Agent Memory Systems

## Landscape Overview (May 2026)

There are three approaches to agent memory:

| Approach | Examples | Philosophy |
|----------|----------|------------|
| **Vector DB + LLM** | mem0, LangMem, Chroma, Zep | Embed everything, search by similarity |
| **SQLite + BM25** | ClawMemory, AgentMemory, agentmem, MEMENTO | FTS5 keyword search, no embeddings |
| **Managed cloud** | mem0 Cloud, Zep Cloud, OpenAI Memory | Opaque API, zero control |

## Head-to-Head

### MEMENTO vs mem0

mem0 is the most popular (56k stars). It uses embeddings + graph + LLM extraction in a managed pipeline.

| Aspect | mem0 | MEMENTO |
|--------|------|---------|
| Architecture | Vector store + Entity graph + LLM | SQLite FTS5 + Markdown Wiki + keyword bridge |
| Setup | `pip install mem0ai` + API key + embedding model | `pip install memento-memory` + `memento init` |
| Dependencies | Python, OpenAI/other LLM, embedding model | Python stdlib + SQLite only |
| Storage | Cloud or Docker (Qdrant/Postgres) | Single SQLite file |
| Wiki | ❌ | ✅ Git-backed markdown wiki |
| Offline | ❌ (needs API) | ✅ Fully offline |
| Cost | $/token for embeddings + LLM calls | $0 |
| Transparency | Opaque processing pipeline | Full SQLite access, plain markdown files |

**Choose mem0 when:** you need managed infrastructure, cloud sync, and don't mind API costs.
**Choose MEMENTO when:** you want zero-dependency, full data control, and a real wiki.

### MEMENTO vs ClawMemory

ClawMemory is the closest competitor — same philosophy (SQLite FTS5, no embeddings).

| Aspect | ClawMemory | MEMENTO |
|--------|------------|---------|
| Architecture | Single SQLite fact store | Two complexes: fact store + wiki |
| Storage | SQLite (FTS5) + optional Turso | SQLite (FTS5) + Git-backed Markdown wiki |
| Wiki | ❌ | ✅ raw → sources → analysis pipeline |
| Keyword bridge | ❌ (single store) | ✅ fact ↔ wiki via keywords |
| Multi-agent | ❌ (single-agent) | ✅ shared + sync |
| Agent framework | OpenClaw plugin only | Any agent (CLI/MCP) |
| Memory lifecycle | Extraction, profiling, decay | Extraction + wiki curation + graph |
| Language | Go | Python |

**Choose ClawMemory when:** you use OpenClaw and want a single fact database.
**Choose MEMENTO when:** you need both facts and deep knowledge, or use multiple agent frameworks.

### MEMENTO vs LangMem

LangMem is LangChain's official memory solution.

| Aspect | LangMem | MEMENTO |
|--------|---------|---------|
| Architecture | LangGraph BaseStore + embeddings | SQLite FTS5 + Markdown Wiki |
| Framework lock-in | LangGraph required | Framework-agnostic (CLI/MCP) |
| Wiki | ❌ | ✅ |
| Embeddings | Required for search | Not used (FTS5 BM25) |
| Storage backend | InMemoryStore (dev) or Postgres (prod) | Single SQLite file |
| Offline | Limited | ✅ Fully |

**Choose LangMem when:** you're already deep in LangChain/LangGraph ecosystem.
**Choose MEMENTO when:** you want framework-agnostic, zero-dependency memory.

### MEMENTO vs Hermes memory providers (Holographic, Local Memory, scope-recall)

These are Hermes Agent-specific plugins.

| Aspect | Holographic | MEMENTO |
|--------|-------------|---------|
| Architecture | SQLite + HRR vector algebra | SQLite FTS5 + Markdown Wiki |
| Wiki | ❌ | ✅ |
| Scope | Hermes Agent only | Any agent (CLI/MCP) |
| Unique | Trust scoring, compositional queries | Two-system memory, keyword bridge |

**Choose Holographic when:** you need trust scoring and compositional reasoning within Hermes.
**Choose MEMENTO when:** you need a wiki, multi-agent sharing, or framework independence.

## Summary: MEMENTO's Niche

MEMENTO occupies a unique position in the landscape:

```
                  Has Wiki?
                  /      \
                Yes       No
               /            \
         MEMENTO         Has embeddings?
                            /       \
                          Yes        No
                         /            \
                   mem0, LangMem    ClawMemory,
                                   AgentMemory
```

**MEMENTO is the only agent memory system that includes a wiki.** Not a vector store, not a fact DB — a real, Git-backed, LLM-curated knowledge base alongside a fast fact store.

## Why This Matters

Agent memory systems today all solve the same problem: "remember facts from conversations." But agents also need to remember **how to do things** — procedures, analyses, workflows. That's not fact storage, that's knowledge management. 

MEMENTO's two-system design is the first to address both:
- **Fact Store** → "What does the user prefer?"
- **Wiki** → "How does the analysis pipeline work?"

And the keyword bridge makes sure they don't live in isolation.
