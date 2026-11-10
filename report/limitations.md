# Limitations — APICN000

- TF-IDF retrieval misses semantic matches ("my daughter studies abroad" ↔ "LRS").
- Year scoping is absent: identical provisions across FYs can both be retrieved.
- Single-LLM-call answers; no verification pass, so slab tables may be mangled.
- (keep ≤ 300 words)
