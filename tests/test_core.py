"""Core functional test suite covering the scenarios called out in the
project spec: login/permission restrictions, import validation and
duplicate detection, bulk assignment, reassignment history, call logging,
lead access restriction, follow-up updates, admission stage tracking and
report exports."""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.forms import StaffUserCreationForm
from apps.accounts.models import CustomUser, Role
from apps.admissions.models import AdmissionStageHistory
from apps.assignments.models import LeadAssignment
from apps.assignments.services import (
    AssignmentError,
    capacity_based_assign,
    equal_distribution_assign,
    manual_assign,
    reassign_leads,
)
from apps.courses.models import College, Course
from apps.followups.models import FollowUp, FollowUpStatus
from apps.leads.imports import normalize_phone_number, validate_rows
from apps.leads.models import LeadStage, StudentLead
from apps.telecalling.models import CallAttempt, CallOutcome, OutcomeCategory


def make_lead(phone="9000000001", name="Test Student", owner=None):
    return StudentLead.objects.create(student_name=name, student_phone=phone, current_owner=owner)


class PhoneNormalizationTests(TestCase):
    def test_indian_number_with_country_code_normalizes(self):
        self.assertEqual(normalize_phone_number("+91 90000 00001"), "9000000001")
        self.assertEqual(normalize_phone_number("919000000001"), "9000000001")
        self.assertEqual(normalize_phone_number("09000000001"), "9000000001")
        self.assertEqual(normalize_phone_number("9000000001"), "9000000001")

    def test_short_invalid_number_is_not_padded(self):
        self.assertEqual(normalize_phone_number("12"), "12")


class StaffUserCreationFormTests(TestCase):
    def setUp(self):
        self.college = College.objects.create(name="Only College", code="ONLY")

    def test_college_is_hidden_and_assigned_automatically(self):
        form = StaffUserCreationForm(
            data={
                "username": "newcaller",
                "first_name": "New",
                "last_name": "Caller",
                "email": "caller@example.com",
                "phone_number": "9000012345",
                "role": Role.TELECALLER,
                "branch": "",
                "reporting_manager": "",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            }
        )

        self.assertNotIn("college", form.fields)
        self.assertNotIn("employee_code", form.fields)
        self.assertNotIn("team_name", form.fields)
        self.assertNotIn("max_active_leads", form.fields)
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.college, self.college)
        self.assertEqual(user.telecaller_profile.max_active_leads, 200)


class ImportValidationTests(TestCase):
    def test_duplicate_and_invalid_rows_are_flagged(self):
        rows = [
            {"name": "A", "phone": "9000011111"},
            {"name": "B", "phone": "9000022222"},
            {"name": "B dup", "phone": "9000022222"},
            {"name": "Bad", "phone": "12"},
        ]
        mapping = {"name": "student_name", "phone": "student_phone"}
        results = validate_rows(rows, mapping)

        self.assertTrue(results[0]["is_valid"])
        self.assertFalse(results[0]["is_duplicate_in_file"])
        self.assertTrue(results[2]["is_duplicate_in_file"])
        self.assertFalse(results[3]["is_valid"])

    def test_existing_db_phone_detected_as_duplicate(self):
        make_lead(phone="9000033333")
        rows = [{"name": "C", "phone": "9000033333"}]
        mapping = {"name": "student_name", "phone": "student_phone"}
        results = validate_rows(rows, mapping)
        self.assertTrue(results[0]["is_duplicate_in_db"])


class LoginPermissionTests(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_user("admin1", password="pass1234", role=Role.ADMIN, is_staff=True)
        self.caller = CustomUser.objects.create_user("caller1", password="pass1234", role=Role.TELECALLER)

    def test_telecaller_cannot_access_import_page(self):
        self.client.login(username="caller1", password="pass1234")
        resp = self.client.get(reverse("leads:import_start"))
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_access_import_page(self):
        self.client.login(username="admin1", password="pass1234")
        resp = self.client.get(reverse("leads:import_start"))
        self.assertEqual(resp.status_code, 200)

    def test_login_required_redirects_anonymous(self):
        resp = self.client.get(reverse("dashboard:home"))
        self.assertEqual(resp.status_code, 302)


class LeadAccessRestrictionTests(TestCase):
    def setUp(self):
        self.caller_a = CustomUser.objects.create_user("callerA", password="pass1234", role=Role.TELECALLER)
        self.caller_b = CustomUser.objects.create_user("callerB", password="pass1234", role=Role.TELECALLER)
        self.lead = make_lead(phone="9000044444", owner=self.caller_a)

    def test_owner_can_view_lead(self):
        self.client.login(username="callerA", password="pass1234")
        resp = self.client.get(reverse("leads:detail", args=[self.lead.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_non_owner_telecaller_is_forbidden(self):
        self.client.login(username="callerB", password="pass1234")
        resp = self.client.get(reverse("leads:detail", args=[self.lead.pk]))
        self.assertEqual(resp.status_code, 403)


class AssignmentTests(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_user("admin2", password="pass1234", role=Role.ADMIN)
        self.caller_a = CustomUser.objects.create_user("callerA2", password="pass1234", role=Role.TELECALLER)
        self.caller_b = CustomUser.objects.create_user("callerB2", password="pass1234", role=Role.TELECALLER)
        self.leads = [make_lead(phone=f"90001000{i:02d}") for i in range(6)]

    def test_manual_assign_sets_owner(self):
        lead_ids = [self.leads[0].pk]
        manual_assign(lead_ids, self.caller_a, self.admin)
        self.leads[0].refresh_from_db()
        self.assertEqual(self.leads[0].current_owner, self.caller_a)
        self.assertEqual(LeadAssignment.objects.filter(lead=self.leads[0], is_active=True).count(), 1)

    def test_equal_distribution_splits_evenly(self):
        lead_ids = [l.pk for l in self.leads]
        equal_distribution_assign(lead_ids, [self.caller_a, self.caller_b], self.admin)
        count_a = StudentLead.objects.filter(current_owner=self.caller_a).count()
        count_b = StudentLead.objects.filter(current_owner=self.caller_b).count()
        self.assertEqual(count_a + count_b, 6)
        self.assertEqual(count_a, 3)
        self.assertEqual(count_b, 3)

    def test_reassignment_preserves_history(self):
        lead_ids = [self.leads[0].pk]
        manual_assign(lead_ids, self.caller_a, self.admin)
        reassign_leads(lead_ids, self.caller_b, self.admin, notes="moving to B")

        self.leads[0].refresh_from_db()
        self.assertEqual(self.leads[0].current_owner, self.caller_b)
        history = LeadAssignment.objects.filter(lead=self.leads[0]).order_by("assigned_at")
        self.assertEqual(history.count(), 2)
        self.assertFalse(history.first().is_active)
        self.assertTrue(history.last().is_active)

    def test_capacity_based_respects_max_active_leads(self):
        from apps.accounts.models import TelecallerProfile

        TelecallerProfile.objects.create(user=self.caller_a, max_active_leads=2)
        TelecallerProfile.objects.create(user=self.caller_b, max_active_leads=10)

        lead_ids = [l.pk for l in self.leads]
        capacity_based_assign(lead_ids, [self.caller_a, self.caller_b], self.admin)

        count_a = StudentLead.objects.filter(current_owner=self.caller_a).count()
        self.assertLessEqual(count_a, 2)

    def test_no_duplicate_active_assignment_per_lead(self):
        lead_ids = [self.leads[0].pk]
        manual_assign(lead_ids, self.caller_a, self.admin)
        manual_assign(lead_ids, self.caller_b, self.admin)
        active_count = LeadAssignment.objects.filter(lead=self.leads[0], is_active=True).count()
        self.assertEqual(active_count, 1)


class CallLoggingTests(TestCase):
    def setUp(self):
        self.caller = CustomUser.objects.create_user("caller3", password="pass1234", role=Role.TELECALLER)
        self.lead = make_lead(phone="9000055555", owner=self.caller)
        self.outcome = CallOutcome.objects.create(
            name="Interested", slug="interested-test", category=OutcomeCategory.POSITIVE
        )

    def test_logging_call_creates_attempt_and_updates_stage(self):
        self.client.login(username="caller3", password="pass1234")
        resp = self.client.post(
            reverse("telecalling:log_call", args=[self.lead.pk]),
            {"outcome": self.outcome.pk, "remarks": "Good conversation"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(CallAttempt.objects.filter(lead=self.lead).count(), 1)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.stage, LeadStage.INTERESTED)

    def test_multiple_calls_do_not_overwrite_history(self):
        self.client.login(username="caller3", password="pass1234")
        for _ in range(3):
            self.client.post(
                reverse("telecalling:log_call", args=[self.lead.pk]),
                {"outcome": self.outcome.pk, "remarks": "call"},
            )
        self.assertEqual(CallAttempt.objects.filter(lead=self.lead).count(), 3)


class FollowUpTests(TestCase):
    def setUp(self):
        self.caller = CustomUser.objects.create_user("caller4", password="pass1234", role=Role.TELECALLER)
        self.lead = make_lead(phone="9000066666", owner=self.caller)
        self.followup = FollowUp.objects.create(
            lead=self.lead, assigned_to=self.caller, scheduled_at=timezone.now() + timedelta(hours=1)
        )

    def test_complete_followup(self):
        self.client.login(username="caller4", password="pass1234")
        resp = self.client.post(reverse("followups:complete", args=[self.followup.pk]), {"completion_notes": "done"})
        self.assertEqual(resp.status_code, 302)
        self.followup.refresh_from_db()
        self.assertEqual(self.followup.status, FollowUpStatus.COMPLETED)

    def test_reschedule_followup_creates_new_entry(self):
        self.client.login(username="caller4", password="pass1234")
        new_time = (timezone.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        resp = self.client.post(
            reverse("followups:reschedule", args=[self.followup.pk]), {"scheduled_at": new_time}
        )
        self.assertEqual(resp.status_code, 302)
        self.followup.refresh_from_db()
        self.assertEqual(self.followup.status, FollowUpStatus.RESCHEDULED)
        self.assertEqual(FollowUp.objects.filter(lead=self.lead).count(), 2)


class AdmissionPipelineTests(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_user("admin3", password="pass1234", role=Role.ADMIN)
        self.caller = CustomUser.objects.create_user("caller5", password="pass1234", role=Role.TELECALLER)
        self.lead = make_lead(phone="9000077777", owner=self.caller)

    def test_authorized_user_can_move_stage(self):
        self.client.login(username="admin3", password="pass1234")
        resp = self.client.post(reverse("admissions:move_stage", args=[self.lead.pk]), {"stage": LeadStage.CONTACTED})
        self.assertEqual(resp.status_code, 200)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.stage, LeadStage.CONTACTED)
        self.assertEqual(AdmissionStageHistory.objects.filter(lead=self.lead).count(), 1)

    def test_telecaller_cannot_move_stage(self):
        self.client.login(username="caller5", password="pass1234")
        resp = self.client.post(reverse("admissions:move_stage", args=[self.lead.pk]), {"stage": LeadStage.CONTACTED})
        self.assertEqual(resp.status_code, 403)


class ReportExportTests(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_user("admin4", password="pass1234", role=Role.ADMIN)
        make_lead(phone="9000088888")

    def test_export_all_leads_xlsx(self):
        self.client.login(username="admin4", password="pass1234")
        resp = self.client.get(reverse("reports:export", args=["all_leads"]), {"format": "xlsx"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("spreadsheetml", resp["Content-Type"])

    def test_export_forbidden_for_telecaller(self):
        caller = CustomUser.objects.create_user("caller6", password="pass1234", role=Role.TELECALLER)
        self.client.login(username="caller6", password="pass1234")
        resp = self.client.get(reverse("reports:export", args=["all_leads"]))
        self.assertEqual(resp.status_code, 403)
