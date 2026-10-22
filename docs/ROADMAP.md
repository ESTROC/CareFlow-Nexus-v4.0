# Delivery register — what is actually done versus planned

## Release 0.1 — working engineering baseline

- [x] Synthetic case fixtures with explicit provenance
- [x] Authenticated API, Argon2 password hashes, JWT and tenant filters
- [x] Admin/analyst/supervisor/auditor roles; task decision authorization
- [x] Four specialist workflow functions with conditional discrepancy routing
- [x] LangGraph implementation with explicit deterministic fallback
- [x] Optional model-guided specialist investigation advisories
- [x] Evidence references, audit trace, case version and idempotent approvals
- [x] Responsive React operations dashboard and case review workspace
- [x] FHIR R4 Task JSON preview (not a server-side write)
- [x] UCI group-disjoint ML training/evaluation source code
- [x] MIMIC demo read-only local schema/count inspection tool
- [x] Docker/CI definitions and Python integration tests

## Next — proof of engineering maturity

- [ ] Verify successful GitHub Actions frontend and Docker builds for release SHA
- [ ] Expand authorization, concurrency and failed-operation tests
- [ ] Introduce migrations, proper session identity federation and scoped API permissions
- [ ] Add real FHIR test server and validate schema/conformance with synthetic patient bundles
- [ ] Run UCI benchmark against official download, record actual held-out metrics and model card
- [ ] Run MIMIC demo schema inspection locally under its license, record provenance metadata
- [ ] Build 100+ independently reviewed workflow evaluation cases and deterministic/single-agent/multi-agent baselines
- [ ] Add controlled LLM prompt/tool evaluation, latency, cost and tracing metrics
- [ ] Add real document intelligence with a licensed benchmark and annotated ground truth
- [ ] Add a justified independent integration (MCP, n8n, Redis workers or event outbox) and demonstrate its value
- [ ] Add deployment and recovery testing, stricter threat model, SBOM and vulnerability assessment

The unchecked work is **not implemented** and must not be claimed on a resume. The first release must be described as a *portfolio prototype*, not a deployed enterprise healthcare service.
