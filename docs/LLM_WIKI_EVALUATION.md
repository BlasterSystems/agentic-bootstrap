# LLM Wiki Integration Evaluation

**Date:** 2026-07-31  
**Recommendation:** Keep the repository-native progressive-disclosure documentation for the MVP; do not add an LLM Wiki subsystem yet.

## What was evaluated

Andrej Karpathy's [LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) describes an LLM-maintained knowledge base built from immutable raw sources and evolving, interlinked Markdown synthesis pages. A content index is read first, then the agent loads only relevant pages. The pattern is intended for growing collections of external sources, research, personal knowledge, or team information.

## Fit with this repository

The useful retrieval pattern is already present:

- `AGENTS.md` defines progressive-disclosure tiers.
- `docs/README.md` catalogs documentation by task.
- `docs/adr/README.md` indexes durable decisions before individual ADRs are loaded.
- Source-controlled documentation is reviewed and validated with the code it describes.

This repository's documentation is primarily **normative project documentation**, not a large corpus of raw source material requiring continuous synthesis. Adding `raw/`, generated wiki pages, ingestion workflows, and another index now would duplicate sources of truth and create drift risk without a demonstrated retrieval problem.

## Recommendation

For the MVP:

1. Keep `README.md` short and use `docs/README.md` as the detailed documentation index.
2. Continue index-first ADR discovery and scoped loading.
3. Keep external research as links in evaluations or ADR references rather than ingesting it automatically.
4. Require human review before research conclusions become normative documentation or accepted ADRs.
5. Do not add embeddings, a wiki runtime, automated ingestion, or LLM-authored background updates.

## When to reconsider

Run a bounded pilot if at least two of these become true:

- The project accumulates roughly 50–100 substantial external sources.
- Agents repeatedly re-synthesize the same research.
- Cross-project knowledge, meeting transcripts, or operational history must be queried together.
- Documentation search misses relevant material despite maintained indexes.
- Contradictions between sources need explicit tracking over time.

## Optional pilot design

Keep a pilot separate from normative documentation:

```text
wiki/
├── index.md       # content catalog read first
├── raw/           # immutable captured sources
└── pages/         # LLM-maintained synthesis
```

Guardrails:

- `wiki/raw/` is immutable after ingestion.
- Every synthesis claim links to one or more raw sources.
- Wiki automation cannot edit `AGENTS.md`, `docs/`, or accepted ADRs directly.
- Promotion from wiki synthesis into normative docs requires a reviewed change.
- The pilot must be removable without changing the bootstrap CLI or generated-project contract.

Evaluate the pilot using retrieval accuracy, stale-link count, contradiction handling, review effort, context usage, and maintenance cost. Adopt it only if those measures outperform the current index-first documentation structure.
