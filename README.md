# CareFlow Nexus v4.0

**Evidence-grounded transitions-of-care operations research workbench**  
Four bounded specialists • FastAPI • LangGraph • React • PostgreSQL • human review • FHIR R4 Task previews

[![CI](https://github.com/ESTROC/CareFlow-Nexus-v4.0/actions/workflows/ci.yml/badge.svg)](https://github.com/ESTROC/CareFlow-Nexus-v4.0/actions/workflows/ci.yml)

> **Evidence and safety statement:** This is an **enterprise-style engineering research prototype**, not a deployed hospital product, clinically validated predictor, medical device, or HIPAA-certified service. **Every included case is synthetic.** Human review is required for administrative task decisions. No autonomous clinical decisions, medication recommendations, third-party notifications or writes to external healthcare records occur in this release.

## Frontend — React operations dashboard

**Yes, this repository includes a full frontend**, not only a backend. Open the **[frontend source directory](frontend/)** or the **[frontend guide](frontend/README.md)**.

| UI screen | Available functionality |
| --- | --- |
| **Overview** | KPIs, case queue, reviews and proposed/approved tasks |
| **Case workbench** | Case search, investigations, evidence excerpts, findings, four-agent trace, audit events |
| **Approval queue** | Supervisor/admin approval or rejection of proposed administrative tasks |
| **Agent intelligence** | Inspect the four specialist roles and workflow transparency |
| **Governance** | Permissions, evidence attribution, audit controls and safety limitations |

The frontend entrypoint is [`frontend/src/App.jsx`](frontend/src/App.jsx), with responsive styling in [`frontend/src/style.css`](frontend/src/style.css). **Run `docker compose up --build -d`, then open [http://localhost:8088](http://localhost:8088)** to use the complete UI with its API. Alternatively, run Vite at **http://localhost:5173** alongside the backend.

GitHub's **Security** navigation tab is a built-in repository feature; GitHub does **not** create an automatic **Frontend** tab. The UI lives under the **Code → frontend/** directory. This release does not have a separately deployed public frontend preview or committed application screenshots.

## What actually works in the core application

- **Responsive case-management interface:** dashboard KPIs, case queue, investigated encounter, findings, evidence excerpts, agent trace and human approval queue.
- **Secured service:** Argon2 password hashes, expiring signed JWT, `admin`/`analyst`/`supervisor`/`auditor` roles, tenant-constrained case lookup, replay-safe task decisions and audit events.
- **Four specialist investigations:** EHR timeline, policy research, conditional discrepancy resolution and administrative care coordination. **LangGraph** executes the conditional workflow when installed. Each specialist has a bounded set of allowed actions.
- **Evidence validation:** Every finding and proposed task must cite a record or versioned **demo-policy** excerpt. Missing evidence causes an error rather than an unsupported result.
- **LLM tool use (opt-in):** Four specialists can request role-allowlisted read-only tools, inspect tool results and submit bounded suggestions over compatible Grok/Groq model endpoints. Hard-coded evidence, authorization and human approvals remain authoritative; traces capture actual tool calls, latency and tokens. **Provider-backed performance is not yet verified.**
- **FHIR interoperability preview:** Approved tasks can be inspected as FHIR R4-shaped `Task` resources. **No live HAPI FHIR write adapter has been completed.**
- **ML research track:** Separate reproducible UCI Diabetes readmission benchmark with patient-disjoint splitting, validation-only threshold tuning and held-out metrics. Never applied to dashboard patients.
- **Authentic-data research tooling:** Read-only MIMIC-IV demo schema/count inspection and a **separate local FHIR-shaped Bundle exporter** for official demo encounters. No patient data is committed; outputs never enter the fictional operational cases.
- **Testing and delivery:** API tests, mocked LLM tool-call permission tests, a reproducible **120-case developer-labelled synthetic evaluation** (routing, citations, matching, latency and token metrics), CI for React/Python/container builds, and Docker Compose. Synthetic agreement **does not establish clinical or real-model accuracy**.

## Screens and use case

1. Log in as a configured local administrator.
2. Select fictional case `CASE-1001`. Its discharge narrative claims an appointment was scheduled, but the synthetic structured field does not confirm it; the case also includes a pending test without a named administrative owner.
3. Run investigation. Read the versioned evidence trail, specialist trace and resulting proposed verification tasks.
4. Approve or reject individual tasks. Only administrators/supervisors may decide. Retrying the same decision is idempotent; stale plan versions cannot be approved.
5. Inspect the audit log and FHIR Task preview. Nothing is written to a clinical information system.

## Start locally using Docker (recommended)

Prerequisites: Docker Desktop/Engine, Docker Compose V2. The stack publishes the UI **only on loopback**.

```bash
cp .env.example .env
# Replace JWT_SECRET, ADMIN_PASSWORD, POSTGRES_PASSWORD with strong unique values.
docker compose up --build -d
# Open http://localhost:8088
```

Sign in using `ADMIN_USERNAME` and `ADMIN_PASSWORD` from `.env`. The app **fails at startup** if the secrets or admin password are missing or too short. Five fictional cases are seeded when `SEED_DEMO_DATA=true`.

```bash
docker compose logs -f api
docker compose ps
docker compose down
```

To discard local demo data **deliberately**, run `docker compose down -v`.

### Developer mode (without Docker)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\\Scripts\\activate
pip install -r requirements-dev.txt
# Configure DATABASE_URL=sqlite:///./careflow.db plus ADMIN_USERNAME, ADMIN_PASSWORD, JWT_SECRET, SEED_DEMO_DATA=true
uvicorn careflow.main:app --reload
# New terminal:
cd frontend
npm install
npm run dev
# http://localhost:5173
```

Developer UI uses the Vite `/api` proxy to port 8000. `GET /api/v1/health` is a public liveness endpoint; all case data requires a token.

## Optional Grok / Groq model-driven tools

The four specialists run deterministic investigation logic when no model is configured. With a supported provider key, they may **select read-only tools, inspect their results, and return bounded suggestions**; neither the model nor its tools can approve tasks, change source evidence or make clinical decisions.

In your local `.env`, set **one** provider (they are different companies):

```dotenv
# xAI Grok
LLM_BASE_URL=https://api.x.ai/v1
LLM_API_KEY=your_private_key
LLM_MODEL=your_current_supported_grok_model
```

For **GroqCloud** instead, use `LLM_BASE_URL=https://api.groq.com/openai/v1` and a model currently available to your account. The shared implementation uses the OpenAI-compatible **Chat Completions tool-call API**; xAI recommends its newer Responses API for some reasoning models. Never commit a key or send real PHI. Provider-backed operation requires your own API key and has **not** been externally verified yet.

- [Agent/tool integration, model telemetry, evaluation and honest limitations](docs/AGENT_EVALUATION.md)
- Run the expanded **offline 120-case evaluation**: `python evals/benchmark.py --split holdout`
- Optional **limited-cost** real provider test: `python evals/benchmark.py --live --split development --max-live-cases 3`

## Validate

```bash
cd backend && pytest -q
cd ..
python ml/evaluate_workflow.py
python evals/benchmark.py --split holdout
cd frontend && npm install && npm run build
cd ..
docker compose config -q
```

The original synthetic evaluation has five developer-authored cases; the new reproducible holdout covers **120 additional developer-labelled synthetic scenarios**, not expert-verified clinical or LLM reasoning accuracy. CI outcomes are visible on the [GitHub Actions page](https://github.com/ESTROC/CareFlow-Nexus-v4.0/actions).

## Authentic data, without fraudulent joins

| Track | Source | Permitted purpose in this codebase | Scope limitations |
|---|---|---|---|
| Operational application | Committed fictional fixtures | Fully functioning case/approval demonstration | **Synthetic**; never presented as real hospital encounters |
| Clinical database exploration | [MIMIC-IV Demo 2.2](https://physionet.org/content/mimic-iv-demo/2.2/) | Local `integrations/mimic_demo_inspect.py` for schema/row-count exploration | Open demo of **100** de-identified patients, no free-text notes; **not imported into operational cases** |
| ML research | [UCI Diabetes 130-US Hospitals](https://archive.ics.uci.edu/dataset/296/diabetes+130-us+hospitals+for+years+1999-2008) | `ml/train_uci.py` reproduces separate prediction experiment | Historical 1999–2008 cohort; no contemporary clinical validation; requires locally downloaded CSV |

Never combine UCI and MIMIC patient identifiers. Never upload clinical files, secrets or checkpoints to the public repository.

### Real historical ML experiment

Download `diabetic_data.csv` from the [UCI dataset](https://archive.ics.uci.edu/dataset/296/diabetes+130-us+hospitals+for+years+1999-2008) (CC BY 4.0), and place it in ignored `ml/data/`. Then:

```bash
pip install -r ml/requirements.txt
python ml/train_uci.py --csv ml/data/diabetic_data.csv --out ml/output
```

This trains Logistic Regression and Random Forest, uses `patient_nbr`-disjoint train/validation/test partitions, chooses the model by **validation PR-AUC**, tunes the threshold using validation F1 only, and reports held-out test PR-AUC, ROC-AUC, recall, precision, F1 and Brier score. Scores are **not claimed until the script has run on the real dataset**. Its artifact is a research model only; it is not available in the operational care-coordination UI. Attribution: Strack et al. dataset, DOI [10.24432/C5230J](https://doi.org/10.24432/C5230J).

### MIMIC-IV demo research inspection

Obtain the open-access data from its [official PhysioNet demo page](https://physionet.org/content/mimic-iv-demo/2.2/) under the stated ODbL terms and store it under ignored `research/data/`. Run:

```bash
python integrations/mimic_demo_inspect.py --directory research/data/mimic-iv-demo/2.2/hosp
```

This deliberately reports aggregate counts and column names, not identifiable information or clinical model predictions. For a local patient/encounter mapping test (FHIR R4-shaped Bundle, no live writes), also run:

```bash
python integrations/mimic_to_fhir.py --directory research/data/mimic-iv-demo/2.2/hosp --out research/data/mimic-fhir-bundle.json --limit 30
```

The export keeps pseudonymous, locally linkable identifiers and is **not** suitable for public upload. It deliberately excludes lab/medication conversions until separately validated. Credit: Johnson et al. MIMIC-IV Clinical Database Demo v2.2, DOI [10.13026/dp1f-ex47](https://doi.org/10.13026/dp1f-ex47).

## Engineering boundaries and known limitations

- **Not enterprise production-ready:** Prototype bootstraps SQL tables with `create_all` rather than migrations; full production configuration would require Alembic, managed secrets, TLS, rate limiting, OIDC/SSO, backups, retention controls, external audit/approval policy and tenant-isolation review.
- **Four bounded specialists ≠ four autonomous LLMs by default:** Without configured external inference, their findings are deterministic and traceable. The bounded optional model tool-calling pathway cannot create autonomous writes; agents still require measured task-quality evaluations and threat modelling.
- **Policy corpus is illustrative**, labeled `DEMO_POLICY` rather than falsely cited as an institution's policy or clinical guidance. The policies are not medical advice.
- **FHIR Task output is a preview**, not a validated external integration or a substitute for full FHIR conformance testing. The fictional `Patient`/`Encounter` references are not actual HAPI resources.
- **Not yet implemented:** external external HAPI interoperability (only local R4-shaped Bundle/Task outputs implemented), Redis/Celery, n8n, MCP, end-to-end clinical workflow validation, OCR/deep-learning extraction, real-time observability, MLflow integration, deployment to Kubernetes. See [Roadmap](docs/ROADMAP.md). The existence of technology in a plan must never be interpreted as implementation.
- **Security limits:** a public demo with realistic personal health information would be inappropriate. Do not use any real PHI. Admin bootstrap and local JWT security are proof-of-concept features, not a claim of regulatory compliance.

## Further documentation

- [Agent/tool evaluation and provider configuration](docs/AGENT_EVALUATION.md)
- [System architecture and data contracts](docs/ARCHITECTURE.md)
- [Threat model and test design](docs/SECURITY.md)
- [Verification and planned releases](docs/ROADMAP.md)

**Independent portfolio project.** No affiliation with Optum or any healthcare provider. No real patient records or private health information are contained in the source tree.
