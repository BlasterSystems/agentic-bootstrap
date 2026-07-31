# ADR-0004: Defer LLM Wiki integration for the MVP

- **Status:** Proposed
- **Date:** 2026-07-31
- **Decision owners:** Project maintainers
- **Scope:** Documentation architecture
- **Tags:** documentation, progressive-disclosure, llm-wiki
- **Supersedes:** None
- **Superseded by:** None

## Context

The repository needs concise, discoverable documentation for coding agents. The LLM Wiki pattern offers immutable raw sources, LLM-maintained synthesis pages, and index-first retrieval. Agentic Bootstrap already uses progressive-disclosure instructions, a documentation index, and an ADR index for a comparatively small normative documentation set.

## Decision drivers

- Keep one clear source of truth for product and architecture behavior.
- Avoid maintenance and ingestion machinery before a retrieval problem is demonstrated.
- Preserve index-first, low-context discovery.
- Leave a bounded path to evaluate larger knowledge corpora later.

## Considered options

### Integrate LLM Wiki now

Add raw sources, synthesis pages, indexing rules, and LLM maintenance workflows. This supports future research scale but duplicates current documentation structures and increases drift and review risk.

### Keep progressive-disclosure documentation only

Use `README.md`, `docs/README.md`, and `docs/adr/README.md` as layered indexes. This meets current needs with fewer moving parts but does not synthesize large external corpora.

### Defer integration and define pilot triggers

Use the current structure for the MVP and run an isolated, measurable wiki pilot only when source volume or repeated synthesis justifies it.

## Decision

Propose deferring LLM Wiki integration. Keep the repository-native progressive-disclosure structure and adopt the LLM Wiki's index-first principle through `docs/README.md`. Reconsider only through the pilot triggers and guardrails in `docs/LLM_WIKI_EVALUATION.md`.

## Consequences

### Positive

- Normative documentation remains reviewable with the code.
- Agents retain a small, explicit discovery path.
- Future experimentation has defined boundaries and measures.

### Negative

- External research remains manually curated.
- The repository does not provide automated synthesis or contradiction tracking.

### Risks and mitigations

Indexes can become stale. Documentation checks and normal review must verify links and summaries when documents change.

## Implementation and validation

Add `docs/README.md`, document the evaluation and pilot plan, and link both from the focused root README. Validate ADR indexing and links with the repository validator.

## Revisit triggers

Reconsider when at least two triggers in `docs/LLM_WIKI_EVALUATION.md` are met or when measured documentation retrieval becomes inadequate.

## References

- [LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- [LLM Wiki evaluation](../LLM_WIKI_EVALUATION.md)
- [ADR-0002](0002-adr-lifecycle-and-progressive-disclosure.md)
