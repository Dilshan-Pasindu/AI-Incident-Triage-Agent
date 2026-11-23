"""
agent-client/tests/test_eval_suite.py

Unit and integration tests for the benchmark evaluation suite.
Verifies that all 7 benchmark scenarios evaluate successfully with MockLlmClient,
and that markdown report generation works properly.
"""

import os
import tempfile
from pathlib import Path
import pytest

from incident_agent.eval_suite import SCENARIOS, EvaluationRunner, generate_markdown_report
from incident_agent.llm import MockLlmClient
from incident_agent.mcp_client import MCPHub
from incident_agent.tracing import TraceLogger


@pytest.fixture
def repo_paths():
    repo_root = Path(__file__).resolve().parent.parent.parent
    return {
        "rust_binary": str(repo_root / "mcp-server" / "target" / "release" / "ops-telemetry-mcp"),
        "workspace_dir": str(repo_root / "mock_data" / "workspace"),
        "repo_root": str(repo_root),
    }


@pytest.mark.asyncio
async def test_all_scenarios_pass_evaluation(repo_paths):
    """Verify that all 7 benchmark scenarios pass their evaluation verifiers."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl") as tmp_trace:
        hub = MCPHub(
            ops_binary_path=repo_paths["rust_binary"],
            workspace_dir=repo_paths["workspace_dir"],
        )
        await hub.start()
        try:
            llm = MockLlmClient()
            trace_logger = TraceLogger(tmp_trace.name)
            runner = EvaluationRunner(
                hub=hub,
                llm=llm,
                trace_logger=trace_logger,
                workspace_dir=repo_paths["workspace_dir"],
            )

            results = []
            for scenario in SCENARIOS:
                metric = await runner.run_scenario(scenario, run_index=1)
                results.append(metric)
                assert metric.passed, f"Scenario '{scenario.id}' failed: {metric.failure_reason}"

            assert len(results) == 7
            pass_count = sum(1 for r in results if r.passed)
            assert pass_count == 7

        finally:
            await hub.stop()


def test_markdown_report_generation(repo_paths):
    """Verify that generate_markdown_report produces expected sections and content."""
    from incident_agent.eval_suite import RunMetric

    dummy_metrics = [
        RunMetric(
            scenario_id="auth_logs",
            run_index=1,
            passed=True,
            duration_ms=45.2,
            iterations=2,
            tools_called=["ops__search_logs"],
            injection_detected=False,
            approval_requested=False,
            approval_granted=False,
            final_answer="Auth logs summarized successfully.",
        ),
        RunMetric(
            scenario_id="create_ticket",
            run_index=1,
            passed=True,
            duration_ms=88.5,
            iterations=2,
            tools_called=["ops__create_incident_ticket"],
            injection_detected=False,
            approval_requested=True,
            approval_granted=True,
            final_answer="Ticket created successfully.",
        ),
    ]

    with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp_md:
        tmp_path = tmp_md.name

    try:
        generate_markdown_report(
            metrics=dummy_metrics,
            scenarios=[s for s in SCENARIOS if s.id in ("auth_logs", "create_ticket")],
            model_name="MockLlmClient (test)",
            output_path=tmp_path,
        )

        with open(tmp_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "# Incident Triage & Release Readiness Agent — Evaluation Results" in content
        assert "Executive Summary" in content
        assert "Benchmark Evaluation Summary" in content or "Scenario Results Matrix" in content
        assert "Auth Service Log Retrieval" in content
        assert "Incident Ticket Creation with HITL Approval" in content
        assert "Security and Safety Verification" in content
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
