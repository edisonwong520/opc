import json
from concurrent.futures import Future
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import AgentRun, AgentTemplate, ApprovalDecision, AuditLog, FounderProfile, Invitation, Mission, Organization, PricingProfile, QualityGate, Workstream
from .openclaw import _estimate_cost, _run_mission, _run_agent_turn, dashboard_metrics
from .openclaw import serialize_mission


def default_organization():
    return Organization.objects.get_or_create(slug="default", defaults={"name": "Default OPC"})[0]


class TemplateApiTests(TestCase):
    def test_create_update_get_and_delete_template(self):
        create_response = self.client.post(
            reverse("desk:template-list-create"),
            data=json.dumps(
                {
                    "id": "legal",
                    "name": "Legal",
                    "title": "General Counsel",
                    "mission": "Review contracts and compliance exposure.",
                    "reportsTo": "ceo",
                    "status": "standby",
                    "tools": "contracts, policy",
                    "budgetLimitUsd": 12.5,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(create_response.json()["tools"], ["contracts", "policy"])

        detail_response = self.client.get(reverse("desk:template-detail-update", kwargs={"template_id": "legal"}))
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["name"], "Legal")

        update_response = self.client.post(
            reverse("desk:template-detail-update", kwargs={"template_id": "legal"}),
            data=json.dumps({"status": "ready", "tools": ["risk"]}),
            content_type="application/json",
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["status"], "ready")
        self.assertEqual(update_response.json()["tools"], ["risk"])
        self.assertTrue(AuditLog.objects.filter(action="template.updated", entity_id="legal").exists())

        delete_response = self.client.delete(reverse("desk:template-detail-update", kwargs={"template_id": "legal"}))
        self.assertEqual(delete_response.status_code, 200)
        self.assertFalse(AgentTemplate.objects.filter(id="legal").exists())
        self.assertTrue(AuditLog.objects.filter(action="template.deleted", entity_id="legal").exists())


class AuthApiTests(TestCase):
    def test_bootstrap_login_logout_and_session(self):
        bootstrap_response = self.client.post(
            reverse("desk:auth-bootstrap"),
            data=json.dumps({"username": "founder", "password": "secret-pass", "organizationName": "OPC Lab"}),
            content_type="application/json",
        )
        self.assertEqual(bootstrap_response.status_code, 201)
        self.assertTrue(bootstrap_response.json()["authenticated"])
        self.assertEqual(bootstrap_response.json()["username"], "founder")
        self.assertEqual(bootstrap_response.json()["role"], "admin")
        self.assertTrue(AuditLog.objects.filter(action="auth.bootstrap", actor="founder").exists())

        logout_response = self.client.post(reverse("desk:auth-logout"))
        self.assertEqual(logout_response.status_code, 200)
        self.assertFalse(logout_response.json()["authenticated"])

        login_response = self.client.post(
            reverse("desk:auth-login"),
            data=json.dumps({"username": "founder", "password": "secret-pass"}),
            content_type="application/json",
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertTrue(login_response.json()["authenticated"])

        me_response = self.client.get(reverse("desk:auth-me"))
        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.json()["organization"]["slug"], "default")
        self.assertEqual(me_response.json()["role"], "admin")

    def test_authenticated_user_reads_own_organization_scope(self):
        default = default_organization()
        other = Organization.objects.create(name="Other OPC", slug="other")
        user = User.objects.create_user(username="other", password="secret-pass")
        FounderProfile.objects.create(user=user, organization=other)
        AgentTemplate.objects.create(id="other-agent", organization=other, name="Other", title="Other", mission="Other")
        AgentTemplate.objects.create(id="default-agent", organization=default, name="Default", title="Default", mission="Default")

        self.client.login(username="other", password="secret-pass")
        response = self.client.get(reverse("desk:template-list-create"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.json()["templates"]], ["other-agent"])

    @override_settings(OPC_REQUIRE_AUTH=True)
    def test_strict_auth_requires_login_for_workspace_reads(self):
        response = self.client.get(reverse("desk:template-list-create"))

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"], "Authentication required.")

    @override_settings(OPC_REQUIRE_AUTH=True)
    def test_viewer_cannot_operate_or_manage_templates(self):
        organization = default_organization()
        user = User.objects.create_user(username="viewer", password="secret-pass")
        FounderProfile.objects.create(user=user, organization=organization, role=FounderProfile.Role.VIEWER)
        AgentTemplate.objects.create(id="viewer-agent", organization=organization, name="Viewer", title="Viewer", mission="Read only.")

        self.client.login(username="viewer", password="secret-pass")

        read_response = self.client.get(reverse("desk:template-list-create"))
        command_response = self.client.post(
            reverse("desk:create-command"),
            data=json.dumps({"command": "Launch beta"}),
            content_type="application/json",
        )
        template_response = self.client.post(
            reverse("desk:template-list-create"),
            data=json.dumps({"id": "new", "name": "New", "mission": "Manage templates."}),
            content_type="application/json",
        )

        self.assertEqual(read_response.status_code, 200)
        self.assertEqual(command_response.status_code, 403)
        self.assertEqual(template_response.status_code, 403)

    @override_settings(OPC_REQUIRE_AUTH=True)
    def test_operator_can_operate_but_cannot_manage_templates(self):
        organization = default_organization()
        user = User.objects.create_user(username="operator", password="secret-pass")
        FounderProfile.objects.create(user=user, organization=organization, role=FounderProfile.Role.OPERATOR)

        self.client.login(username="operator", password="secret-pass")
        with patch("apps.desk.views.start_mission"):
            command_response = self.client.post(
                reverse("desk:create-command"),
                data=json.dumps({"command": "Launch beta"}),
                content_type="application/json",
            )
        template_response = self.client.post(
            reverse("desk:template-list-create"),
            data=json.dumps({"id": "new", "name": "New", "mission": "Manage templates."}),
            content_type="application/json",
        )

        self.assertEqual(command_response.status_code, 201)
        self.assertEqual(template_response.status_code, 403)


class ApprovalApiTests(TestCase):
    def test_approve_and_reject_record_decisions_and_update_gate(self):
        mission = Mission.objects.create(organization=default_organization(), command="Ship MVP", session_id="opc-test")
        QualityGate.objects.create(mission=mission, name="founder-approval")

        approve_response = self.client.post(
            reverse("desk:mission-approve", kwargs={"mission_id": mission.id}),
            data=json.dumps({"notes": "Looks ready."}),
            content_type="application/json",
        )
        self.assertEqual(approve_response.status_code, 200)
        self.assertEqual(approve_response.json()["qualityGates"][0]["status"], "passed")
        self.assertEqual(approve_response.json()["approvalDecisions"][0]["decision"], "approved")
        self.assertEqual(ApprovalDecision.objects.filter(mission=mission, decision="approved").count(), 1)
        self.assertTrue(AuditLog.objects.filter(action="mission.approved", entity_id=str(mission.id)).exists())

        reject_response = self.client.post(
            reverse("desk:mission-reject", kwargs={"mission_id": mission.id}),
            data=json.dumps({"notes": "Needs another pass."}),
            content_type="application/json",
        )
        self.assertEqual(reject_response.status_code, 200)
        self.assertEqual(reject_response.json()["qualityGates"][0]["status"], "failed")
        self.assertEqual(reject_response.json()["approvalDecisions"][0]["decision"], "rejected")
        self.assertEqual(ApprovalDecision.objects.filter(mission=mission, decision="rejected").count(), 1)
        self.assertTrue(AuditLog.objects.filter(action="mission.rejected", entity_id=str(mission.id)).exists())


class MissionControlApiTests(TestCase):
    def test_abort_retry_and_archive_mission(self):
        mission = Mission.objects.create(organization=default_organization(), command="Ship MVP", session_id="opc-control", status=Mission.Status.RUNNING)

        abort_response = self.client.post(reverse("desk:mission-abort", kwargs={"mission_id": mission.id}))
        self.assertEqual(abort_response.status_code, 200)
        self.assertEqual(abort_response.json()["status"], "aborted")
        self.assertTrue(abort_response.json()["abortRequested"])

        with patch("apps.desk.views.start_mission") as start_mission:
            retry_response = self.client.post(reverse("desk:mission-retry", kwargs={"mission_id": mission.id}))

        self.assertEqual(retry_response.status_code, 200)
        self.assertEqual(retry_response.json()["status"], "queued")
        self.assertFalse(retry_response.json()["abortRequested"])
        self.assertTrue(start_mission.called)
        self.assertTrue(AuditLog.objects.filter(action="mission.retried", entity_id=str(mission.id)).exists())

        mission.status = Mission.Status.FAILED
        mission.save(update_fields=["status"])
        archive_response = self.client.post(reverse("desk:mission-archive", kwargs={"mission_id": mission.id}))
        self.assertEqual(archive_response.status_code, 200)
        self.assertIsNotNone(archive_response.json()["archivedAt"])
        self.assertTrue(AuditLog.objects.filter(action="mission.archived", entity_id=str(mission.id)).exists())

        list_response = self.client.get(reverse("desk:list-missions"))
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["missions"], [])

    def test_list_filters_and_markdown_export(self):
        organization = default_organization()
        keep = Mission.objects.create(organization=organization, command="Launch paid beta", session_id="opc-keep", status=Mission.Status.SUCCEEDED)
        Mission.objects.create(organization=organization, command="Internal cleanup", session_id="opc-skip", status=Mission.Status.FAILED)

        list_response = self.client.get(reverse("desk:list-missions"), {"status": "succeeded", "search": "beta"})
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual([item["sessionId"] for item in list_response.json()["missions"]], ["opc-keep"])

        export_response = self.client.get(reverse("desk:mission-export", kwargs={"mission_id": keep.id}))
        self.assertEqual(export_response.status_code, 200)
        self.assertEqual(export_response["Content-Type"], "text/markdown; charset=utf-8")
        self.assertIn("# OPC Mission opc-keep", export_response.content.decode())

    def test_audit_log_list_is_scoped_to_default_organization(self):
        organization = default_organization()
        other = Organization.objects.create(name="Other OPC", slug="other")
        AuditLog.objects.create(organization=organization, action="mission.archived", entity_type="Mission", entity_id="a")
        AuditLog.objects.create(organization=other, action="mission.archived", entity_type="Mission", entity_id="b")

        response = self.client.get(reverse("desk:audit-logs"), {"action": "mission.archived"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["entityId"] for item in response.json()["logs"]], ["a"])

    def test_failed_workstream_retry_records_audit_log(self):
        mission = Mission.objects.create(organization=default_organization(), command="Ship MVP", session_id="opc-workstream", status=Mission.Status.FAILED)
        workstream = Workstream.objects.create(
            mission=mission,
            owner="CTO",
            title="Technical review",
            description="Assess implementation risk.",
            status=Workstream.Status.FAILED,
        )

        with patch("apps.desk.views.retry_workstream") as retry_workstream:
            response = self.client.post(reverse("desk:workstream-retry", kwargs={"mission_id": mission.id, "workstream_id": workstream.id}))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(retry_workstream.called)
        self.assertTrue(AuditLog.objects.filter(action="workstream.retried", entity_id=str(workstream.id)).exists())


class AgentRunSerializationTests(TestCase):
    def test_mission_serialization_includes_workstream_agent_runs(self):
        mission = Mission.objects.create(command="Ship MVP", session_id="opc-test")
        workstream = Workstream.objects.create(
            mission=mission,
            owner="CTO",
            title="Technical review",
            description="Assess implementation risk.",
            status=Workstream.Status.SUCCEEDED,
            result="Use the smallest durable architecture.",
        )
        AgentRun.objects.create(
            workstream=workstream,
            session_id="opc-test-cto-1",
            status=AgentRun.Status.SUCCEEDED,
            input_tokens=120,
            output_tokens=80,
            estimated_cost_usd="0.004",
            result_text="Use the smallest durable architecture.",
            logs=[{"level": "info", "message": "done"}],
        )

        data = serialize_mission(mission)

        self.assertEqual(data["workstreams"][0]["agentRuns"][0]["sessionId"], "opc-test-cto-1")
        self.assertEqual(data["workstreams"][0]["agentRuns"][0]["usage"]["input"], 120)
        self.assertEqual(data["workstreams"][0]["agentRuns"][0]["resultText"], "Use the smallest durable architecture.")


class ImmediateExecutor:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def submit(self, fn, *args, **kwargs):
        future = Future()
        try:
            future.set_result(fn(*args, **kwargs))
        except Exception as exc:
            future.set_exception(exc)
        return future


class FakeOpenClawProcess:
    def __init__(self, *args, **kwargs):
        payload = {
            "meta": {
                "finalAssistantVisibleText": "Workstream complete.",
                "agentMeta": {"usage": {"input": 10, "output": 5, "total": 15}},
            }
        }
        self.stdout = iter([json.dumps(payload)])

    def wait(self, timeout=None):
        return 0


class MissionOrchestrationTests(TestCase):
    def test_run_mission_creates_independent_agent_runs_for_each_workstream(self):
        mission = Mission.objects.create(command="Ship MVP", session_id="opc-test")

        with (
            patch("apps.desk.openclaw.gateway_status", return_value={"ok": True, "raw": ""}),
            patch("apps.desk.openclaw.model_status", return_value={"ok": True, "missingProvidersInUse": [], "resolvedDefault": "opc/test"}),
            patch("apps.desk.openclaw.ThreadPoolExecutor", ImmediateExecutor),
            patch("apps.desk.openclaw.subprocess.Popen", FakeOpenClawProcess),
        ):
            _run_mission(str(mission.id))

        mission.refresh_from_db()

        self.assertEqual(mission.status, Mission.Status.SUCCEEDED)
        self.assertEqual(mission.workstreams.count(), 5)
        self.assertEqual(AgentRun.objects.filter(workstream__mission=mission, status=AgentRun.Status.SUCCEEDED).count(), 5)
        self.assertEqual(mission.input_tokens, 50)
        self.assertEqual(mission.output_tokens, 25)
        self.assertTrue(mission.board_brief.summary)


class PricingAndBudgetTests(TestCase):
    def test_estimate_cost_uses_active_pricing_profile(self):
        PricingProfile.objects.create(provider="opc", model_id="test-model", input_per_1k_usd="0.100000", output_per_1k_usd="0.200000")

        cost = _estimate_cost(1000, 2000, "opc/test-model")

        self.assertEqual(str(cost), "0.500000")

    def test_agent_turn_fails_before_openclaw_when_budget_is_exhausted(self):
        template = AgentTemplate.objects.create(
            id="budget",
            name="Budget",
            title="Budget Guard",
            mission="Guard spend.",
            budget_limit_usd="0.0100",
        )
        mission = Mission.objects.create(command="Ship MVP", session_id="opc-budget")
        first = Workstream.objects.create(mission=mission, agent_template=template, owner="Budget", title="First", status=Workstream.Status.SUCCEEDED)
        workstream = Workstream.objects.create(mission=mission, agent_template=template, owner="Budget", title="Second")
        AgentRun.objects.create(workstream=first, session_id="opc-budget-first", status=AgentRun.Status.SUCCEEDED, estimated_cost_usd="0.0100")

        with patch("apps.desk.openclaw.subprocess.Popen") as popen:
            agent_run = _run_agent_turn(workstream)

        self.assertEqual(agent_run.status, AgentRun.Status.FAILED)
        self.assertIn("Budget exceeded", agent_run.error)
        self.assertFalse(popen.called)


class DashboardMetricsTests(TestCase):
    def test_dashboard_metrics_counts_agent_runs_and_success_rate(self):
        succeeded = Mission.objects.create(command="A", session_id="opc-a", status=Mission.Status.SUCCEEDED, estimated_cost_usd="0.100000")
        Mission.objects.create(command="B", session_id="opc-b", status=Mission.Status.FAILED)
        workstream = Workstream.objects.create(mission=succeeded, owner="CTO", title="Technical review")
        AgentRun.objects.create(workstream=workstream, session_id="opc-a-cto", status=AgentRun.Status.SUCCEEDED)

        metrics = dashboard_metrics()

        self.assertEqual(metrics["agentRuns"], 1)
        self.assertEqual(metrics["successRate"], 0.5)
        self.assertEqual(metrics["budgetUsedUsd"], 0.1)


class InvitationApiTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Test Org", slug="test-org")
        self.admin_user = User.objects.create_user(username="admin", password="adminpass")
        FounderProfile.objects.create(user=self.admin_user, organization=self.organization, role=FounderProfile.Role.ADMIN)
        self.client.force_login(self.admin_user)

    def test_create_list_and_revoke_invitation(self):
        create_response = self.client.post(
            reverse("desk:invitation-create"),
            json.dumps({"email": "newuser@example.com", "role": "operator"}),
            content_type="application/json",
        )
        self.assertEqual(create_response.status_code, 201)
        invitation_id = create_response.json()["id"]

        list_response = self.client.get(reverse("desk:invitation-list"))
        self.assertEqual(list_response.status_code, 200)
        invitations = list_response.json()["invitations"]
        self.assertEqual(len(invitations), 1)
        self.assertEqual(invitations[0]["email"], "newuser@example.com")

        revoke_response = self.client.delete(reverse("desk:invitation-revoke", kwargs={"invitation_id": invitation_id}))
        self.assertEqual(revoke_response.status_code, 200)

        list_response = self.client.get(reverse("desk:invitation-list"))
        self.assertEqual(len(list_response.json()["invitations"]), 0)

    def test_accept_invitation_creates_user_and_profile(self):
        invitation = Invitation.objects.create(
            email="joiner@example.com",
            organization=self.organization,
            invited_by=self.admin_user,
            role=FounderProfile.Role.OPERATOR,
            expires_at=timezone.now() + timezone.timedelta(days=7),
        )
        self.client.logout()

        accept_response = self.client.post(
            reverse("desk:invitation-accept", kwargs={"token": invitation.token}),
            json.dumps({"username": "joiner", "password": "joinerpass"}),
            content_type="application/json",
        )
        self.assertEqual(accept_response.status_code, 201)
        data = accept_response.json()
        self.assertEqual(data["authenticated"], True)
        self.assertEqual(data["role"], "operator")

        user = User.objects.get(username="joiner")
        self.assertEqual(user.founder_profile.organization, self.organization)
        self.assertEqual(user.founder_profile.role, FounderProfile.Role.OPERATOR)

        invitation.refresh_from_db()
        self.assertEqual(invitation.status, Invitation.Status.ACCEPTED)

    def test_expired_invitation_cannot_be_accepted(self):
        invitation = Invitation.objects.create(
            email="expired@example.com",
            organization=self.organization,
            invited_by=self.admin_user,
            role=FounderProfile.Role.VIEWER,
            expires_at=timezone.now() - timezone.timedelta(days=1),
        )

        accept_response = self.client.post(
            reverse("desk:invitation-accept", kwargs={"token": invitation.token}),
            json.dumps({"username": "expireduser", "password": "pass"}),
            content_type="application/json",
        )
        self.assertEqual(accept_response.status_code, 410)
        self.assertIn("expired", accept_response.json()["error"].lower())
