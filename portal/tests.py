from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from .models import ConductRecord, ConductRule, Department, PersonProfile, ResourceCategory, StudentProfile, TrainingResource


class StudentApiTests(TestCase):
    def test_students_api_returns_database_students(self):
        department = Department.objects.create(name="飞行学员管理室")
        person = PersonProfile.objects.create(
            name="测试学员",
            employee_no="A30001",
            role=PersonProfile.Role.STUDENT,
            department=department,
            position="飞行学员",
        )
        StudentProfile.objects.create(person=person, stage=StudentProfile.Stage.S1)

        response = self.client.get("/api/students")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["source"], "django-database")
        self.assertEqual(len(payload["students"]), 1)
        self.assertEqual(payload["students"][0]["jobNumber"], "A30001")


class ConductScoreTests(TestCase):
    def test_conduct_record_recalculates_student_score(self):
        person = PersonProfile.objects.create(
            name="测试学员",
            employee_no="A30002",
            role=PersonProfile.Role.STUDENT,
            position="飞行学员",
        )
        student = StudentProfile.objects.create(person=person, initial_score=100, current_score=100)
        rule = ConductRule.objects.create(
            rule_id="rule-test",
            dimension="训练作风",
            module="测试",
            item="测试",
            title="测试扣分",
            values=[-2],
        )

        ConductRecord.objects.create(student=student, rule=rule, score_delta=-2)

        student.refresh_from_db()
        self.assertEqual(student.current_score, 98)

    def test_conduct_api_requires_permission_and_writes_record(self):
        User = get_user_model()
        user = User.objects.create_user(username="manager", password="pass")
        PersonProfile.objects.create(
            user=user,
            name="管理员",
            employee_no="M10001",
            role=PersonProfile.Role.MANAGER,
            can_manage_conduct=True,
            excluded_from_conduct_score=True,
        )
        person = PersonProfile.objects.create(
            name="测试学员",
            employee_no="A30003",
            role=PersonProfile.Role.STUDENT,
            position="飞行学员",
        )
        student = StudentProfile.objects.create(person=person, initial_score=100, current_score=100)
        rule = ConductRule.objects.create(
            rule_id="rule-api",
            dimension="训练作风",
            module="测试",
            item="测试",
            title="测试扣分",
            values=[-2],
        )

        self.client.login(username="manager", password="pass")
        response = self.client.post(
            "/api/conduct/records",
            data={"studentId": str(person.pk), "ruleId": rule.rule_id, "scoreDelta": -2, "reason": "测试"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        student.refresh_from_db()
        self.assertEqual(student.current_score, 98)

    def test_conduct_rules_api_returns_active_rules(self):
        ConductRule.objects.create(
            rule_id="rule-active",
            dimension="训练作风",
            module="课堂纪律",
            item="迟到",
            title="训练迟到扣分",
            values=[-2],
        )
        ConductRule.objects.create(
            rule_id="rule-inactive",
            dimension="训练作风",
            module="课堂纪律",
            item="停用",
            title="停用规则",
            values=[-1],
            is_active=False,
        )

        response = self.client.get("/api/conduct/rules")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["rules"]), 1)
        self.assertEqual(payload["rules"][0]["id"], "rule-active")

    def test_conduct_rule_match_requires_permission_and_returns_suggestion(self):
        User = get_user_model()
        user = User.objects.create_user(username="conduct-manager", password="pass")
        PersonProfile.objects.create(
            user=user,
            name="作风管理员",
            employee_no="M10002",
            role=PersonProfile.Role.MANAGER,
            can_manage_conduct=True,
            excluded_from_conduct_score=True,
        )
        rule = ConductRule.objects.create(
            rule_id="rule-match",
            dimension="训练作风",
            module="课堂纪律",
            item="训练迟到",
            title="训练迟到扣分",
            values=[-2],
            source="教员反馈",
        )

        self.client.login(username="conduct-manager", password="pass")
        response = self.client.post(
            "/api/conduct/rules/match",
            data={"behavior": "该学员今天训练迟到，教员已反馈。"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["matches"][0]["rule"]["id"], rule.rule_id)


class AuthApiTests(TestCase):
    def test_local_login_returns_permissions(self):
        User = get_user_model()
        user = User.objects.create_user(username="admin", password="shfx6688", is_staff=True)

        response = self.client.post(
            "/api/auth/login",
            data={"username": "admin", "password": "shfx6688"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["authenticated"])
        self.assertTrue(payload["permissions"]["managePeople"])
        user.refresh_from_db()


class ResourceApiTests(TestCase):
    def test_resource_list_returns_active_public_resources(self):
        category = ResourceCategory.objects.create(name="制度文件")
        TrainingResource.objects.create(
            title="测试资源",
            category=category,
            file=SimpleUploadedFile("test.txt", b"hello", content_type="text/plain"),
            file_size=5,
            content_type="text/plain",
        )

        response = self.client.get("/api/resources")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["categories"][0]["name"], "制度文件")
        self.assertEqual(payload["resources"][0]["title"], "测试资源")
