# Agent/tool evaluation — evidence and limitations

This release adds a **real LLM tool-call path** for the four role-scoped specialists (when an API key is provided), plus a reproducible **120-case synthetic holdout check**. They measure very different things.

## What is implemented

1. Four specialists may call only explicitly allowlisted **read-only tools**. Tool arguments are validated, an external write/approval tool is never exposed, and the calling loop is bounded (`LLM_MAX_ROUNDS`, `LLM_MAX_TOOL_CALLS_PER_ROUND`).
2. When the external model issues a tool call, the backend executes the tool and passes the result back for subsequent model reasoning. Accepted suggestions can influence policy query wording and task ordering **within deterministic, previously validated rules**.
3. The system records actual model name, tool names, call rounds, token usage and wall-clock latency in each specialist's trace. Cost is **null** until per-million-token input/output prices are supplied by the operator.
4. If inference fails, the bounded specialists fall back to deterministic evidence verification and predefined administrative task rules; there is no model-driven approval or clinical prediction.
5. GitHub Actions runs offline tool-call contract tests with mocked provider responses, including forbidden tool names, and the 120-case synthetic holdout benchmark. **No paid API calls are made in CI.**

## Model setup — xAI Grok versus Groq (two different providers)

The common chat-completions tool API is used for the provider adapter. Model names and provider API capabilities change; use a model currently available to your account. For xAI reasoning models, the official provider recommends its newer Responses API; our chat-completions adapter is a compatibility implementation and may not take full advantage of multi-turn reasoning features.

In a local `.env`, add **either**:

```dotenv
# xAI Grok (not Groq):
LLM_BASE_URL=https://api.x.ai/v1
LLM_API_KEY=<your own key>
LLM_MODEL=<supported grok model>
```

or

```dotenv
# GroqCloud, a separate model-inference provider:
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_API_KEY=<your own key>
LLM_MODEL=<supported Groq-hosted model>
```

Never commit `.env` or paste credentials in issues. Only use the committed **synthetic cases** with these external providers. The connection has **not** been end-to-end tested with a real provider key in this release.

## Synthetic evaluation

```bash
python evals/benchmark.py --split holdout
python evals/benchmark.py --split all --output reports/workflow.json
```

The generator creates 160 deterministic combinations with seed `240826`: 40 development cases and **120 held-out-from-the-original-five-fixtures cases**. Gold labels come from the scenario metadata (follow-up state, result-owner state and whether the discharge narrative claims an appointment exists). They were authored by the developer and have **not** been adjudicated by healthcare professionals. Scenarios test positive/negative appointment wording, missing fields and one prompt-injection string. Results are not measures of medical accuracy or model reasoning.

Reported metrics: exact finding-set match, evidence-reference validity, discrepancy-route accuracy, per-finding precision/recall, p50/p95 latency, model tool-call counts, token usage and cost if configured. CI mode explicitly removes model endpoint/key variables, so its numbers **apply only to deterministic mode**.

Optional, deliberately budget-limited, real provider experiment:

```bash
# After configuring .env and exporting LLM_* environment variables:
python evals/benchmark.py --split development --live --max-live-cases 3
```

Real-provider results require the key, provider cost and available model. Use repeated runs, budget caps and expert-reviewed test cases before making reliability, generalization or clinical assertions. The --live option is a small **experiment**, not a full independent benchmark.

## What remains unproven

- Clinical validity, real patient data suitability and regulatory compliance.
- Whether a four-specialist model-driven approach outperforms a single-agent or deterministic baseline under fair latency/cost constraints.
- Model-provider compatibility and correctness in a real hosted session until a key-backed smoke test is performed.
- Fully autonomous goal formation, unrestricted planning or physical-world task execution (intentionally not implemented).

**Use the accurate portfolio description:** "Built a four-specialist LangGraph administrative workflow with bounded model-driven tool calls, evidence checks and supervisor approvals; added 120 reproducible synthetic acceptance cases and offline provider-contract tests." Do not call these 120 clinical cases or independent model-accuracy evaluations.
