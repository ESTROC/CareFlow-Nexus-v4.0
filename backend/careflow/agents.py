"""Four bounded investigation specialists. Execution uses LangGraph when installed.

Without LLM credentials the specialists execute deterministic, evidence-backed
policies. They are NOT falsely advertised as four autonomous LLMs in offline mode.
Optional model guidance is restricted to read-only investigation planning and is
never trusted for authorization, assertions, or task writes.
"""
from __future__ import annotations
from hashlib import sha256
from typing import TypedDict, Any
from .retrieval import search_policies
from .fixtures import POLICIES
from .model_advisory import advise


class InvestigationState(TypedDict, total=False):
    record: dict
    evidence: list[dict]
    findings: list[dict]
    tasks: list[dict]
    trace: list[dict]
    has_discrepancy: bool


def evidence_item(identifier: str, quote: str, origin: str):
    return {"id": identifier, "quote": quote, "origin": origin}


def add_finding(state: InvestigationState, code: str, text: str, sources: list[str], severity: str):
    state["findings"].append({"code": code, "description": text, "evidence_ids": sources, "severity": severity})


def timeline_agent(state: InvestigationState) -> InvestigationState:
    record = state["record"]
    state["evidence"].append(evidence_item("EHR-ENCOUNTER", f"Encounter {record['encounter']}; discharged at {record['discharged_at']}", "synthetic FHIR-like encounter"))
    state["evidence"].append(evidence_item("EHR-FOLLOWUP", f"Structured follow-up status: {record['followup_status']}", "synthetic structured field"))
    state["evidence"].append(evidence_item("EHR-RESULT", f"Pending-result flag: {record['pending_result']}; owner: {record['followup_owner'] or 'not recorded'}", "synthetic structured field"))
    for event in record["events"]:
        state["evidence"].append(evidence_item(event["id"], f"{event['at']} — {event['summary']}", "synthetic event log"))
    recommendation = advise("ehr_timeline_investigator", {"encounter": record["encounter"], "event_kinds": [e["kind"] for e in record["events"]]}, ["focus_event_kinds", "reason"])
    state["trace"].append({"agent": "EHR_TIMELINE", "action": "Read authorized encounter and event history", "tools": ["get_encounter", "get_events"], "status": "completed", "advisory": recommendation, "mode": "llm-guided" if recommendation else "deterministic"})
    return state


def policy_agent(state: InvestigationState) -> InvestigationState:
    record = state["record"]
    doc = record.get("document", "")
    state["evidence"].append(evidence_item("DOC-DISCHARGE", doc or "No discharge document provided", "synthetic discharge document"))
    recommendation = advise("policy_researcher", {"followup_status": record["followup_status"], "pending_result": record["pending_result"], "document": doc[:800]}, ["search_query", "reason"])
    query = (str(recommendation.get("search_query", ""))[:180] if recommendation else "") or "discharge follow-up pending test appointment verification evidence handoff"
    ranked = search_policies(query, limit=4)
    # Audit-required policy references cannot vanish because of an LLM query.
    policy_by_id = {p["id"]: p for p in ranked}
    for policy in POLICIES:
        policy_by_id.setdefault(policy["id"], policy)
    for source in policy_by_id.values():
        state["evidence"].append(evidence_item(source["id"], source["text"], f"{source['name']} / {source['version']}"))
    if record["followup_status"] != "SCHEDULED":
        add_finding(state, "FOLLOWUP_UNCONFIRMED", "A confirmed follow-up arrangement is not recorded in structured data.", ["EHR-FOLLOWUP", "POL-001"], "attention")
    if record["pending_result"] and not record["followup_owner"]:
        add_finding(state, "RESULT_OWNER_MISSING", "A pending test has no recorded administrative follow-up owner.", ["EHR-RESULT", "POL-002"], "attention")
    state["trace"].append({"agent": "POLICY_RESEARCH", "action": "Search versioned workflow policy and cite excerpts", "tools": ["search_policies", "read_discharge_document"], "status": "completed", "advisory": recommendation, "mode": "llm-guided" if recommendation else "deterministic"})
    return state


def needs_discrepancy(state: InvestigationState) -> str:
    doc = state["record"].get("document", "").lower()
    status = state["record"]["followup_status"]
    claims_scheduled = "appointment has been scheduled" in doc or "appointment scheduled" in doc
    return "discrepancy" if claims_scheduled and status != "SCHEDULED" else "coordination"


def discrepancy_agent(state: InvestigationState) -> InvestigationState:
    add_finding(state, "RECORD_CONFLICT", "The discharge document claims an appointment was scheduled, but the structured record does not confirm it. The true status is unknown.", ["DOC-DISCHARGE", "EHR-FOLLOWUP", "POL-003"], "high")
    state["has_discrepancy"] = True
    recommendation = advise("discrepancy_investigator", {"structured": state["record"]["followup_status"], "document": state["record"]["document"][:800]}, ["additional_evidence_needed", "reason"])
    state["trace"].append({"agent": "DISCREPANCY_RESOLUTION", "action": "Compare conflicting source claims without assuming which is correct", "tools": ["compare_evidence", "read_structured_status"], "status": "completed", "advisory": recommendation, "mode": "llm-guided" if recommendation else "deterministic"})
    return state


def coordination_agent(state: InvestigationState) -> InvestigationState:
    findings = {f["code"]: f for f in state["findings"]}
    tasks: list[dict[str, Any]] = []
    if "FOLLOWUP_UNCONFIRMED" in findings or "RECORD_CONFLICT" in findings:
        citations = ["EHR-FOLLOWUP", "POL-001"] + (["DOC-DISCHARGE", "POL-003"] if "RECORD_CONFLICT" in findings else [])
        tasks.append({"key": "VERIFY_FOLLOWUP", "title": "Verify follow-up appointment with authorized coordinator", "reason": "Appointment status requires source-system confirmation; do not make clinical assumptions.", "evidence_ids": citations})
    if "RESULT_OWNER_MISSING" in findings:
        tasks.append({"key": "ASSIGN_RESULT_OWNER", "title": "Assign administrative owner for pending result", "reason": "Ownership is missing from the structured discharge record; requires supervisor review.", "evidence_ids": ["EHR-RESULT", "POL-002"]})
    if not tasks:
        add_finding(state, "NO_ADMIN_ISSUES", "No missing follow-up or pending-result ownership was detected by the configured demo checks; this is not clinical clearance.", ["EHR-FOLLOWUP", "EHR-RESULT"], "informational")
    recommendation = advise("coordination_planner", {"available_task_keys": [t["key"] for t in tasks], "finding_codes": list(findings)}, ["task_order", "reason"])
    if recommendation and isinstance(recommendation.get("task_order"), list):
        order = recommendation["task_order"]
        if len(order) == len(tasks) and set(order) == {t["key"] for t in tasks}:
            tasks.sort(key=lambda t: order.index(t["key"]))
    state["tasks"] = tasks
    state["trace"].append({"agent": "CARE_COORDINATION", "action": "Prepare bounded administrative task drafts; no external writes", "tools": ["task_catalog", "dependency_rules"], "status": "completed", "advisory": recommendation, "mode": "llm-guided" if recommendation else "deterministic"})
    return state


def review_sources(state: InvestigationState) -> None:
    valid = {e["id"] for e in state["evidence"]}
    for item in state["findings"] + state["tasks"]:
        if not item["evidence_ids"] or not set(item["evidence_ids"]).issubset(valid):
            raise ValueError("Unsupported finding/task: missing evidence reference")
    unique = {t["key"] for t in state["tasks"]}
    if len(unique) != len(state["tasks"]):
        raise ValueError("Duplicate task key in plan")


def investigate(record: dict) -> dict:
    state: InvestigationState = {"record": record, "evidence": [], "findings": [], "tasks": [], "trace": [], "has_discrepancy": False}
    try:
        from langgraph.graph import StateGraph, END
    except ImportError:
        # Explicitly documented local fallback for environments without LangGraph.
        state = timeline_agent(state)
        state = policy_agent(state)
        if needs_discrepancy(state) == "discrepancy":
            state = discrepancy_agent(state)
        state = coordination_agent(state)
        execution = "local-deterministic-fallback"
    else:
        builder = StateGraph(InvestigationState)
        builder.add_node("ehr", timeline_agent)
        builder.add_node("policy", policy_agent)
        builder.add_node("discrepancy", discrepancy_agent)
        builder.add_node("coordination", coordination_agent)
        builder.set_entry_point("ehr")
        builder.add_edge("ehr", "policy")
        builder.add_conditional_edges("policy", needs_discrepancy, {"discrepancy": "discrepancy", "coordination": "coordination"})
        builder.add_edge("discrepancy", "coordination")
        builder.add_edge("coordination", END)
        state = builder.compile().invoke(state)
        execution = "langgraph-specialist-workflow"
    review_sources(state)
    return {"findings": state["findings"], "tasks": state["tasks"], "evidence": state["evidence"],
            "trace": state["trace"], "execution_mode": execution,
            "evidence_hash": sha256(str(sorted((e["id"], e["quote"]) for e in state["evidence"])).encode()).hexdigest()}
