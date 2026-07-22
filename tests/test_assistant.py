"""
tests/test_assistant.py
Phase 5: Tests for the Natural Language Scheduling Assistant.
"""
import pytest


# ---------------------------------------------------------------------------
# Unit tests: intent classification
# ---------------------------------------------------------------------------

class TestIntentClassification:
    def test_latest_run_intent(self):
        from assistant.agent import _classify_intent
        intent, _ = _classify_intent("What's the makespan of my latest run?")
        assert intent == "latest_run"

    def test_utilization_intent(self):
        from assistant.agent import _classify_intent
        intent, _ = _classify_intent("Which machine has the worst utilization?")
        assert intent == "utilization"

    def test_late_jobs_intent(self):
        from assistant.agent import _classify_intent
        intent, _ = _classify_intent("Show me all jobs that are late")
        assert intent == "late_jobs"

    def test_alerts_intent(self):
        from assistant.agent import _classify_intent
        intent, _ = _classify_intent("Are there any maintenance alerts?")
        assert intent == "alerts"

    def test_comparison_intent(self):
        from assistant.agent import _classify_intent
        intent, _ = _classify_intent("Compare algorithm performance")
        assert intent == "comparison"

    def test_stats_intent(self):
        from assistant.agent import _classify_intent
        intent, _ = _classify_intent("Give me a system overview")
        assert intent == "stats"

    def test_help_intent(self):
        from assistant.agent import _classify_intent
        intent, _ = _classify_intent("help")
        assert intent == "help"

    def test_list_runs_intent(self):
        from assistant.agent import _classify_intent
        intent, _ = _classify_intent("Show me recent runs")
        assert intent == "list_runs"

    def test_unknown_intent_fallback(self):
        from assistant.agent import _classify_intent
        intent, _ = _classify_intent("How do I bake a pizza?")
        assert intent == "unknown"

    def test_task_id_extraction(self):
        from assistant.agent import _classify_intent
        tid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        intent, kwargs = _classify_intent(f"Show me run {tid}")
        assert intent == "run_by_id"
        assert kwargs.get("task_id") == tid


# ---------------------------------------------------------------------------
# Unit tests: agent responses
# ---------------------------------------------------------------------------

class TestAgentResponses:
    def test_run_agent_help_response(self):
        from assistant.agent import run_agent
        result = run_agent("help")
        assert "reply" in result
        assert "tool_calls" in result
        assert "suggested_prompts" in result
        assert len(result["reply"]) > 50

    def test_run_agent_unknown_returns_reply(self):
        from assistant.agent import run_agent
        result = run_agent("How do I fly a helicopter?")
        assert isinstance(result["reply"], str)
        assert len(result["reply"]) > 0

    def test_run_agent_latest_run_calls_tool(self):
        from assistant.agent import run_agent
        result = run_agent("Show me the latest run")
        # Tool call should be recorded even if no data exists
        assert any(tc["tool_name"] == "get_latest_run" for tc in result["tool_calls"])

    def test_run_agent_stats_calls_tool(self):
        from assistant.agent import run_agent
        result = run_agent("Give me a system overview")
        assert any(tc["tool_name"] == "get_system_stats" for tc in result["tool_calls"])

    def test_run_agent_comparison_calls_tool(self):
        from assistant.agent import run_agent
        result = run_agent("Compare algorithms")
        assert any(tc["tool_name"] == "get_algorithm_comparison" for tc in result["tool_calls"])

    def test_suggested_prompts_are_strings(self):
        from assistant.agent import run_agent
        result = run_agent("help")
        for prompt in result["suggested_prompts"]:
            assert isinstance(prompt, str)

    def test_run_agent_late_jobs_calls_tool(self):
        from assistant.agent import run_agent
        result = run_agent("Which jobs are overdue?")
        assert any(tc["tool_name"] == "get_late_jobs" for tc in result["tool_calls"])

    def test_run_agent_alerts_calls_tool(self):
        from assistant.agent import run_agent
        result = run_agent("Machine health alerts")
        assert any(tc["tool_name"] == "get_maintenance_alerts" for tc in result["tool_calls"])


# ---------------------------------------------------------------------------
# Tool function tests
# ---------------------------------------------------------------------------

class TestAssistantTools:
    def test_get_system_stats_structure(self, test_db):
        from assistant.tools import get_system_stats
        result = get_system_stats()
        assert "total_runs" in result
        assert "completed_runs" in result
        assert "failed_runs" in result
        assert "active_maintenance_alerts" in result

    def test_list_recent_runs_returns_list(self, test_db):
        from assistant.tools import list_recent_runs
        result = list_recent_runs(limit=3)
        assert "runs" in result
        assert "count" in result
        assert isinstance(result["runs"], list)

    def test_get_latest_run_no_data(self, test_db):
        """Should return an error dict if no completed runs exist."""
        from assistant.tools import get_latest_run
        result = get_latest_run()
        # Either returns a run or an error — both are valid structures
        assert isinstance(result, dict)
        if "error" in result:
            assert "No completed" in result["error"]

    def test_get_algorithm_comparison_returns_structure(self, test_db):
        from assistant.tools import get_algorithm_comparison
        result = get_algorithm_comparison()
        assert "comparison" in result
        assert isinstance(result["comparison"], list)

    def test_get_maintenance_alerts_structure(self, test_db):
        from assistant.tools import get_maintenance_alerts
        result = get_maintenance_alerts(resolved=False)
        assert "alerts" in result
        assert "count" in result


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

class TestAssistantAPI:
    def test_chat_help_query(self, client, auth_headers):
        resp = client.post("/api/assistant/chat", json={
            "message": "help",
            "history": [],
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "reply" in data
        assert "tool_calls" in data
        assert "suggested_prompts" in data
        assert len(data["reply"]) > 0

    def test_chat_stats_query(self, client, auth_headers):
        resp = client.post("/api/assistant/chat", json={
            "message": "Give me a system overview",
            "history": [],
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert any(tc["tool_name"] == "get_system_stats" for tc in data["tool_calls"])

    def test_chat_requires_auth(self, client):
        resp = client.post("/api/assistant/chat", json={"message": "help", "history": []})
        assert resp.status_code == 401

    def test_chat_empty_message_rejected(self, client, auth_headers):
        resp = client.post("/api/assistant/chat", json={
            "message": "",
            "history": [],
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_get_starter_prompts(self, client, auth_headers):
        resp = client.get("/api/assistant/prompts", headers=auth_headers)
        assert resp.status_code == 200
        prompts = resp.json()
        assert isinstance(prompts, list)
        assert len(prompts) >= 5
        for p in prompts:
            assert isinstance(p, str) and len(p) > 0

    def test_chat_with_history(self, client, auth_headers):
        resp = client.post("/api/assistant/chat", json={
            "message": "And the utilization?",
            "history": [
                {"role": "user", "content": "Show latest run"},
                {"role": "assistant", "content": "Latest run makespan is 100"},
            ],
        }, headers=auth_headers)
        assert resp.status_code == 200
