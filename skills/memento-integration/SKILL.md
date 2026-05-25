---
name: memento-integration
description: "Use MEMENTO memory system — SQLite fact store + Git wiki + keyword bridge"
trigger: Always load when MEMENTO is installed
---

## MEMENTO CLI

MEMENTO is installed at `~/memento/` or `memento` in PATH. It provides two connected memory systems:

### Two stores

| Store | Command | Use for |
|-------|---------|---------|
| **Fact Store** (SQLite + FTS5) | `memento recall <query>` | Preferences, config, quick facts |
| **Knowledge Base** (Git + Markdown) | `memento wiki search <query>` | Procedures, pipelines, research notes |
| **Deep recall** (fact → keyword → wiki) | `memento deep-recall <query>` | When user says "tell me more" or "go deeper" |

### Always include keywords when storing

```bash
memento remember "B003 = Trivariate MiXeR" --keywords "wiki:b003-mixer wiki:mdd"
```

This is what enables the keyword bridge. Without keywords, the fact is isolated from the wiki.

### Storage protocol

| User intent | Your command |
|-------------|--------------|
| Simple fact | `memento remember "fact" --category preference/config/entity/finding` |
| Complex procedure | `memento wiki create analysis/slug` then add content |
| Both (fact + wiki) | `memento remember "summary" --keywords "wiki:slug"` + `memento wiki create wiki/slug` |
| Past file | `memento artifact list --tag project-name` |
| Past decision | `memento decisions --topic method` |

### Semantic graph

```bash
memento tag add "mem:12345" "mixer"           # Tag any memory
memento relate "mem:12345" "mem:67890" "informs"  # Connect related facts
memento trace "mem:12345"                      # See all connections
```

### Upgrade from sqlite-suitectl

If you see `sqlite-suitectl` commands in context, replace with:
- `sqlite-suitectl artifact add` → `memento artifact add`
- `sqlite-suitectl decide` → `memento decide`
- `sqlite-suitectl experience add` → (not yet in memento)
- `memory_enhancer_remember` → `memento remember`
- `memory_enhancer_search` → `memento recall`
- `memory_l3.py tag add` → `memento tag add`

The MEMENTO CLI reads/writes the **exact same SQLite files** as the Hermes tools.
