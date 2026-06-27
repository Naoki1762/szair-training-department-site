from django.test import TestCase

from .models import ConductRecord, ConductRule, Department, PersonProfile, StudentProfile


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
