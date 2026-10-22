# Security and Responsible AI threat model (prototype)

| Threat | Boundary | Implemented control | Unfinished production hardening |
|---|---|---|---|
| Anonymous case access | HTTP API | All case routes require bearer JWT | OIDC, revocation, TLS, brute-force controls |
| Unauthorized decisions | Task API | Supervisor/admin only | Fine-grained permission matrix, independent penetration test |
| Cross-tenant disclosure | SQL case access | Filters by authenticated tenant | SQL row-level security, tenant-specific encryption |
| Replay/duplicate approval | Task state | Conditional SQL update, version check; repeated identical decision doesn't repeat audit | Distributed outbox, external write deduplication |
| Model hallucinations | Agent planning | Findings/tasks require existing cited sources; model doesn't authorize writes | Held-out citation assessment, domain expert review |
| Prompt injection | Retrieved content | Synthetic text never grants additional rights; model output confined to narrow advisory fields | Structured red teaming, sandboxed tool gateway |
| PHI in public repo | Data ingestion | Committed cases fictional; real research files gitignored | De-identification governance, data retention, full DLP |
| Exposed secrets | Configuration | Env variables, placeholder .env, startup validation | Managed vault, rotation, secret scan in CI |
| Clinical overreach | Product logic | Administrative tasks only; explicit no clinical clearance | Human governance, clinical validation where legally applicable |
| Data corruption | Persistence | Unique keys and versioned task approvals | Alembic migration reviews, backups, reconciliation |

**Residual risk:** no claim of HIPAA/DPDP compliance, medical-device suitability, or verified clinical safety. No real PHI should be placed into this portfolio prototype. External LLM providers should receive only synthetic data in current configuration. Do not deploy it onto the public internet with actual records.
