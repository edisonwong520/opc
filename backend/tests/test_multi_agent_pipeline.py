"""
OPC Multi-Agent Parallel Execution Test

Tests the full mission pipeline:
- CEO Intake → COO Decomposition → CTO/CFO/CMO Parallel → SRE Quality → Board Brief

Usage:
    cd backend
    uv run pytest tests/test_multi_agent_pipeline.py -v -s
"""

import json
import time
import urllib.request
import urllib.error
from http.cookiejar import CookieJar

import pytest

# Test configuration
BASE_URL = "http://127.0.0.1:8000"
TEST_COMMAND = "分析 OPC 项目 README.md，从技术架构、成本效益、市场定位三个视角各给出50字内评估"

# Shared cookie jar for maintaining session
COOKIE_JAR = CookieJar()
OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(COOKIE_JAR))


def api_request(path: str, method: str = "GET", data: dict | None = None, csrf_token: str = "") -> dict:
    """Make API request and return JSON response."""
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if csrf_token:
        headers["X-CSRFToken"] = csrf_token

    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with OPENER.open(req, timeout=120) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": str(e), "status": e.code}


def get_csrf_token() -> str:
    """Get CSRF token from cookie jar."""
    url = f"{BASE_URL}/api/opc/auth/me/"
    req = urllib.request.Request(url)
    try:
        with OPENER.open(req, timeout=10) as response:
            # Extract CSRF token from cookie jar
            for cookie in COOKIE_JAR:
                if cookie.name == "csrftoken":
                    return cookie.value
    except Exception:
        pass
    return ""


def wait_for_mission(mission_id: str, timeout: int = 300, poll_interval: int = 5) -> dict:
    """Wait for mission to complete and return final state."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        result = api_request(f"/api/opc/missions/{mission_id}/")
        if result.get("status") in ["succeeded", "failed", "aborted"]:
            return result
        time.sleep(poll_interval)
    return {"error": "Timeout waiting for mission", "mission_id": mission_id}


def print_mission_status(mission: dict, label: str = "") -> None:
    """Print mission status summary."""
    print(f"\n=== {label} ===")
    print(f"Status: {mission.get('status', 'unknown')}")
    print(f"Session: {mission.get('sessionId', 'unknown')}")

    gates = mission.get("qualityGates", [])
    print(f"Quality Gates ({len(gates)}):")
    for gate in gates:
        print(f"  - {gate['name']}: {gate['status']}")

    workstreams = mission.get("workstreams", [])
    print(f"Workstreams ({len(workstreams)}):")
    for ws in workstreams:
        runs = len(ws.get("agentRuns", []))
        print(f"  - {ws['owner']}: {ws['status']} (runs: {runs})")

    usage = mission.get("usage", {})
    print(f"Tokens: input={usage.get('input', 0)}, output={usage.get('output', 0)}, total={usage.get('total', 0)}")


def print_workstream_details(mission: dict) -> None:
    """Print detailed workstream results."""
    print("\n=== Workstream Results ===")
    for ws in mission.get("workstreams", []):
        print(f"\n[{ws['owner']}] {ws['title']}")
        print(f"Status: {ws['status']}")
        result = ws.get("result", "")
        if result:
            # Truncate long results
            display = result[:150] + "..." if len(result) > 150 else result
            print(f"Result: {display}")

        for run in ws.get("agentRuns", []):
            usage = run.get("usage", {})
            print(f"  AgentRun: session={run.get('sessionId', 'unknown')}")
            print(f"    Tokens: in={usage.get('input', 0)}, out={usage.get('output', 0)}")
            print(f"    Status: {run.get('status', 'unknown')}")

            # Check for gateway issues in logs
            logs = run.get("logs", [])
            gateway_issues = [
                log for log in logs
                if "gateway connect failed" in log.get("message", "").lower()
                or "pairing required" in log.get("message", "").lower()
            ]
            if gateway_issues:
                print(f"    ⚠️  Gateway issues detected: {len(gateway_issues)}")


def print_board_brief(mission: dict) -> None:
    """Print board brief summary."""
    bb = mission.get("boardBrief")
    if not bb:
        print("\n=== Board Brief: Not Generated ===")
        return

    print("\n=== Board Brief ===")
    print(f"Title: {bb.get('title', 'unknown')}")
    summary = bb.get("summary", "")
    display = summary[:200] + "..." if len(summary) > 200 else summary
    print(f"Summary: {display}")
    print(f"Recommendations: {bb.get('recommendations', [])}")
    print(f"Risks: {bb.get('risks', [])}")


class TestMultiAgentPipeline:
    """Test suite for OPC multi-agent parallel execution."""

    def test_backend_health(self) -> None:
        """Verify backend API is running."""
        result = api_request("/api/health/")
        assert result.get("status") == "ok", f"Backend health check failed: {result}"
        print("\n✅ Backend API is healthy")

    def test_gateway_health(self) -> None:
        """Verify OpenClaw Gateway is running."""
        result = api_request("/api/opc/openclaw/health/")
        gateway = result.get("gateway", {})
        model = result.get("model", {})

        print(f"\nGateway Status:")
        print(f"  OK: {gateway.get('ok', False)}")
        print(f"  RPC OK: {gateway.get('rpcOk', False)}")
        print(f"  Pairing Required: {gateway.get('pairingRequired', False)}")
        print(f"  Listening: {gateway.get('listening', False)}")

        print(f"\nModel Status:")
        print(f"  OK: {model.get('ok', False)}")
        print(f"  Default Model: {model.get('defaultModel', 'unknown')}")

        assert gateway.get("ok") is True, f"Gateway not healthy: {gateway}"
        assert model.get("ok") is True, f"Model not configured: {model}"
        print("\n✅ OpenClaw Gateway and Model are healthy")

    def test_mission_pipeline(self) -> None:
        """Test full mission pipeline with parallel agent execution."""
        # Get CSRF token
        csrf_token = get_csrf_token()
        assert csrf_token, "Failed to get CSRF token"
        print(f"\n✅ CSRF token obtained: {csrf_token[:20]}...")

        # Create mission
        print(f"\n🚀 Creating mission with command: '{TEST_COMMAND[:50]}...'")
        result = api_request(
            "/api/opc/commands/",
            method="POST",
            data={"command": TEST_COMMAND},
            csrf_token=csrf_token,
        )

        if result.get("error"):
            pytest.fail(f"Failed to create mission: {result}")

        mission_id = result.get("id")
        assert mission_id, "Mission ID not returned"
        print(f"✅ Mission created: {mission_id}")

        # Monitor execution
        print("\n⏳ Waiting for mission execution...")
        print_mission_status(result, "T+0s: Initial State")

        # Wait for completion
        final_mission = wait_for_mission(mission_id, timeout=300, poll_interval=5)
        if final_mission.get("error"):
            pytest.fail(f"Mission execution error: {final_mission}")

        print_mission_status(final_mission, "Final State")

        # Check mission succeeded
        status = final_mission.get("status")
        assert status == "succeeded", f"Mission did not succeed: status={status}"

        # Check quality gates
        gates = final_mission.get("qualityGates", [])
        gate_status = {g["name"]: g["status"] for g in gates}
        assert gate_status.get("gateway-health") == "passed", "Gateway health gate failed"
        assert gate_status.get("model-provider") == "passed", "Model provider gate failed"
        assert gate_status.get("agent-result") == "passed", "Agent result gate failed"

        # Check workstreams
        workstreams = final_mission.get("workstreams", [])
        assert len(workstreams) >= 4, f"Expected at least 4 workstreams, got {len(workstreams)}"

        # Check parallel execution (CTO, CFO, CMO should all have runs)
        parallel_agents = ["CTO", "CFO", "CMO"]
        for ws in workstreams:
            if ws["owner"] in parallel_agents:
                assert ws["status"] == "succeeded", f"{ws['owner']} workstream failed"
                assert len(ws.get("agentRuns", [])) > 0, f"{ws['owner']} has no agent runs"

        print("\n✅ All parallel workstreams executed successfully")

        # Print detailed results
        print_workstream_details(final_mission)
        print_board_brief(final_mission)

        # Check for gateway issues (warning, not failure)
        has_gateway_issues = False
        for ws in workstreams:
            for run in ws.get("agentRuns", []):
                logs = run.get("logs", [])
                for log in logs:
                    if "pairing required" in log.get("message", "").lower():
                        has_gateway_issues = True
                        break

        if has_gateway_issues:
            print("\n⚠️  WARNING: Gateway pairing issues detected (agents used embedded mode)")

        # Final assertion
        print("\n" + "=" * 50)
        print("✅ MULTI-AGENT PARALLEL PIPELINE TEST PASSED")
        print("=" * 50)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])