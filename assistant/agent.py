# assistant/agent.py
"""
Phase 5: Natural Language Scheduling Assistant Agent.

Rule-based intent engine with DB-backed tool dispatch.
Optionally upgrades to LLM mode when OPENAI_API_KEY is configured.

Intent categories:
  - latest_run       : What's my latest run? / Show me last result
  - run_by_id        : Show run <task_id>
  - list_runs        : Show recent runs / history
  - utilization      : Machine utilization / Which machine is busiest?
  - late_jobs        : Late jobs / Which jobs are overdue?
  - alerts           : Maintenance alerts / Machine health
  - comparison       : Compare algorithms / Which algo is best?
  - stats            : System stats / Overview
  - help             : Help / What can you do?
  - unknown          : Fallback
"""
from __future__ import annotations

import re
import json
from typing import Any

from assistant.tools import TOOL_REGISTRY
from api.schemas import AssistantToolCall


# ---------------------------------------------------------------------------
# Intent patterns
# ---------------------------------------------------------------------------

PATTERNS: list[tuple[str, str, dict]] = [
    # (regex, intent_name, tool_kwargs)
    (r"late\s*jobs?|overdue|tardiness|delayed\s*jobs?|jobs\s*that\s*are\s*late|are\s*late", "late_jobs", {}),
    (r"latest\s*run|last\s*run|most\s*recent|latest\s*result|my\s*latest", "latest_run", {}),
    (r"\blatest\b|\blast\b", "latest_run", {}),  # shorter forms
    (r"run\s+([0-9a-f\-]{8,})", "run_by_id", {}),  # task_id extraction handled separately
    (r"recent\s*runs?|history|show\s*runs?|list\s*runs?|show\s*me\s*runs?|show\s*me\s*recent", "list_runs", {}),
    (r"util[iz]+ation|busy|idle|machine\s*load", "utilization", {}),
    (r"alert|maintenance|health|failure|sensor|breakdown", "alerts", {}),
    (r"compar|best\s*algo|algorithm\s*rank|which\s*algo", "comparison", {}),
    (r"stats?|overview|summary|total\s*runs?|how\s*many", "stats", {}),
    (r"help|what\s*can\s*you|capabilities|commands?", "help", {}),
]


def _classify_intent(message: str) -> tuple[str, dict]:
    """Match message against intent patterns, return (intent, kwargs)."""
    msg = message.lower().strip()

    # Special: task_id extraction for run_by_id
    task_id_match = re.search(r"([0-9a-f]{8}-[0-9a-f\-]{27,35})", msg)
    if task_id_match:
        return "run_by_id", {"task_id": task_id_match.group(1)}

    for pattern, intent, kwargs in PATTERNS:
        if re.search(pattern, msg):
            return intent, kwargs

    return "unknown", {}


# ---------------------------------------------------------------------------
# Reply formatters
# ---------------------------------------------------------------------------

def _format_latest_run(data: dict) -> str:
    if "error" in data:
        return f"⚠️ {data['error']}"
    return (
        f"📊 **Latest Run** (`{data['task_id'][:8]}…`)\n"
        f"- **Algorithm:** {data.get('algorithm', 'N/A')}\n"
        f"- **Makespan:** {data.get('makespan', 'N/A')} time units\n"
        f"- **Total Tardiness:** {data.get('total_tardiness', 0)} units\n"
        f"- **On-Time Jobs:** {data.get('on_time_percent', 0):.1f}%\n"
        f"- **Avg Flow Time:** {data.get('avg_flow_time', 0):.1f} units\n"
        f"- **File:** {data.get('file_name', 'N/A')}"
    )


def _format_run_by_id(data: dict) -> str:
    if "error" in data:
        return f"⚠️ {data['error']}"
    return (
        f"📋 **Run** `{data['task_id'][:8]}…` — Status: **{data.get('status', 'N/A')}**\n"
        f"- **Algorithm:** {data.get('algorithm', 'N/A')}\n"
        f"- **Makespan:** {data.get('makespan', 'N/A')}\n"
        f"- **Tardiness:** {data.get('total_tardiness', 'N/A')}\n"
        f"- **On-Time:** {data.get('on_time_percent', 0):.1f}%"
    )


def _format_list_runs(data: dict) -> str:
    if not data.get("runs"):
        return "📭 No runs found yet."
    lines = ["📜 **Recent Runs:**\n"]
    for r in data["runs"]:
        status_icon = "✅" if r["status"] == "complete" else ("❌" if r["status"] == "error" else "⏳")
        lines.append(
            f"{status_icon} `{r['task_id'][:8]}…` — **{r.get('algorithm', '?')}** "
            f"| Makespan: {r.get('makespan') or 'N/A'} "
            f"| On-Time: {(r.get('on_time_percent') or 0):.0f}%"
        )
    return "\n".join(lines)


def _format_utilization(data: dict) -> str:
    if "error" in data:
        return f"⚠️ {data['error']}"
    util_list = data.get("utilization", [])
    if not util_list:
        return "No utilization data available."
    lowest = data.get("lowest")
    highest = data.get("highest")
    lines = [f"⚙️ **Machine Utilization** (Run `{data['task_id'][:8]}…`):\n"]
    for u in sorted(util_list, key=lambda x: x.get("utilization", 0), reverse=True):
        bar = "█" * int(u.get("utilization", 0) * 10)
        lines.append(f"- Machine {u['machine_id']}: {bar} {u.get('utilization', 0)*100:.1f}%")
    if highest:
        lines.append(f"\n🔥 **Busiest:** Machine {highest['machine_id']}")
    if lowest:
        lines.append(f"💤 **Most Idle:** Machine {lowest['machine_id']}")
    return "\n".join(lines)


def _format_late_jobs(data: dict) -> str:
    if "error" in data:
        return f"⚠️ {data['error']}"
    jobs = data.get("late_jobs", [])
    if not jobs:
        return "✅ Great news — no late jobs in the latest run!"
    lines = [f"⏰ **{len(jobs)} Late Job(s)** (Run `{data['task_id'][:8]}…`):\n"]
    for j in jobs:
        lines.append(
            f"- Job {j['job_id']}: due at {j['due_date']}, "
            f"finished at {j['completion_time']:.0f} "
            f"(**+{j['tardiness']:.0f} units late**)"
        )
    return "\n".join(lines)


def _format_alerts(data: dict) -> str:
    alerts = data.get("alerts", [])
    if not alerts:
        return "✅ All clear — no active maintenance alerts."
    sev_icons = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
    lines = [f"🚨 **{len(alerts)} Active Maintenance Alert(s):**\n"]
    for a in alerts:
        icon = sev_icons.get(a["severity"], "⚠️")
        lines.append(
            f"{icon} **Machine {a['machine_id']}** — {a['severity'].upper()} "
            f"({a['failure_probability']*100:.0f}% failure prob)\n"
            f"   ↳ {a.get('recommended_action', 'No action specified')}"
        )
    return "\n".join(lines)


def _format_comparison(data: dict) -> str:
    rows = data.get("comparison", [])
    if not rows:
        return "📭 Not enough data yet — run multiple algorithms to see comparison."
    rows_sorted = sorted(rows, key=lambda r: r["avg_makespan"])
    lines = ["📊 **Algorithm Comparison** (historical averages):\n"]
    lines.append("| Algorithm | Avg Makespan | Avg Tardiness | On-Time % | Runs |")
    lines.append("|-----------|-------------|--------------|-----------|------|")
    for r in rows_sorted:
        lines.append(
            f"| **{r['algorithm']}** | {r['avg_makespan']} | {r['avg_tardiness']} "
            f"| {r['avg_on_time_percent']}% | {r['run_count']} |"
        )
    best = rows_sorted[0]["algorithm"] if rows_sorted else "N/A"
    lines.append(f"\n🏆 **Best average makespan:** {best}")
    return "\n".join(lines)


def _format_stats(data: dict) -> str:
    return (
        f"📈 **System Overview:**\n"
        f"- Total schedule runs: **{data.get('total_runs', 0)}**\n"
        f"- Completed: **{data.get('completed_runs', 0)}**\n"
        f"- Failed: **{data.get('failed_runs', 0)}**\n"
        f"- Active maintenance alerts: **{data.get('active_maintenance_alerts', 0)}**"
    )


HELP_TEXT = """🤖 **ShopFloor Scheduling Assistant** — here's what I can help with:

| Question | Example |
|---------|---------|
| Latest run metrics | "What's the makespan of my latest run?" |
| Run details | "Show me run a1b2c3d4-…" |
| Run history | "Show me recent runs" |
| Machine utilization | "Which machine has the worst utilization?" |
| Late jobs | "Show me all jobs that are late" |
| Maintenance alerts | "Are there any machine health alerts?" |
| Algorithm comparison | "Which algorithm performs best?" |
| System stats | "Give me an overview of the system" |"""

SUGGESTED_FOLLOW_UPS: dict[str, list[str]] = {
    "latest_run": ["Which jobs were late?", "How's machine utilization?", "Compare algorithms"],
    "list_runs": ["Show details of the latest run", "Which algorithm performs best?"],
    "utilization": ["Are there any late jobs?", "Show maintenance alerts"],
    "late_jobs": ["Show machine utilization", "What's my best algorithm?"],
    "alerts": ["Show late jobs", "Show latest run metrics"],
    "comparison": ["Show recent runs", "What's the latest run's makespan?"],
    "stats": ["Show recent runs", "Show maintenance alerts"],
    "help": ["Show latest run", "Compare algorithms", "Show maintenance alerts"],
    "unknown": ["Show latest run", "Help", "Compare algorithms"],
}


# ---------------------------------------------------------------------------
# Main agent entry point
# ---------------------------------------------------------------------------

def run_agent(message: str, history: list[dict] | None = None) -> dict[str, Any]:
    """
    Process a natural language message and return a structured response.

    Returns:
        {
            "reply": str,
            "tool_calls": list[dict],
            "suggested_prompts": list[str],
        }
    """
    intent, kwargs = _classify_intent(message)
    tool_calls: list[AssistantToolCall] = []

    def call_tool(name: str, **kw) -> dict:
        fn = TOOL_REGISTRY.get(name)
        if not fn:
            return {"error": f"Tool '{name}' not found."}
        result = fn(**kw)
        tool_calls.append(
            AssistantToolCall(
                tool_name=name,
                arguments=kw,
                result_summary=json.dumps(result, default=str)[:200],
            )
        )
        return result

    reply = ""
    if intent == "latest_run":
        data = call_tool("get_latest_run")
        reply = _format_latest_run(data)
    elif intent == "run_by_id":
        data = call_tool("get_run_by_id", task_id=kwargs.get("task_id", ""))
        reply = _format_run_by_id(data)
    elif intent == "list_runs":
        data = call_tool("list_recent_runs", limit=5)
        reply = _format_list_runs(data)
    elif intent == "utilization":
        data = call_tool("get_machine_utilization")
        reply = _format_utilization(data)
    elif intent == "late_jobs":
        data = call_tool("get_late_jobs")
        reply = _format_late_jobs(data)
    elif intent == "alerts":
        data = call_tool("get_maintenance_alerts", resolved=False)
        reply = _format_alerts(data)
    elif intent == "comparison":
        data = call_tool("get_algorithm_comparison")
        reply = _format_comparison(data)
    elif intent == "stats":
        data = call_tool("get_system_stats")
        reply = _format_stats(data)
    elif intent == "help":
        reply = HELP_TEXT
    else:
        reply = (
            "🤔 I'm not sure how to answer that. Try asking about:\n"
            "- Your latest run's metrics\n"
            "- Machine utilization\n"
            "- Late jobs\n"
            "- Maintenance alerts\n"
            "- Algorithm comparison\n\n"
            "Type **help** to see all available queries."
        )

    return {
        "reply": reply,
        "tool_calls": [tc.model_dump() for tc in tool_calls],
        "suggested_prompts": SUGGESTED_FOLLOW_UPS.get(intent, SUGGESTED_FOLLOW_UPS["unknown"]),
    }
