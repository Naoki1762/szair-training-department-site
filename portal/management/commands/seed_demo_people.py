from django.core.management.base import BaseCommand

from portal.models import Department, PersonProfile, StudentProfile


class Command(BaseCommand):
    help = "生成本地测试用人员和 300 名学员"

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=300, help="学员人数，默认 300")

    def handle(self, *args, **options):
        count = options["count"]
        department, _ = Department.objects.get_or_create(
            name="飞行学员管理室",
            defaults={"sort_order": 10},
        )
        admin_department, _ = Department.objects.get_or_create(
            name="培训部行政",
            defaults={"sort_order": 1},
        )

        for index, name in enumerate(["培训管理岗", "教员用户", "作风管理员"], start=1):
            PersonProfile.objects.update_or_create(
                employee_no=f"M{index:04d}",
                defaults={
                    "name": name,
                    "role": PersonProfile.Role.MANAGER,
                    "department": admin_department,
                    "position": "部门行政人员",
                    "can_manage_conduct": True,
                    "excluded_from_conduct_score": True,
                    "is_active": True,
                },
            )

        surnames = ["赵", "钱", "孙", "李", "周", "吴", "郑", "王", "冯", "陈", "刘", "张"]
        given_names = ["宇航", "子轩", "浩然", "嘉诚", "明远", "思源", "俊杰", "博文", "天佑", "景行"]
        stages = [choice[0] for choice in StudentProfile.Stage.choices]

        for index in range(count):
            name = f"{surnames[index % len(surnames)]}{given_names[index % len(given_names)]}"
            employee_no = f"A{29354 + index}"
            person, _ = PersonProfile.objects.update_or_create(
                employee_no=employee_no,
                defaults={
                    "name": name,
                    "role": PersonProfile.Role.STUDENT,
                    "department": department,
                    "position": "飞行学员",
                    "is_active": (index + 1) % 29 != 0,
                    "can_manage_conduct": False,
                    "excluded_from_conduct_score": False,
                },
            )
            StudentProfile.objects.update_or_create(
                person=person,
                defaults={
                    "stage": stages[index % len(stages)],
                    "initial_score": 100,
                    "current_score": 100,
                },
            )

        self.stdout.write(self.style.SUCCESS(f"已生成 {count} 名测试学员和 3 名管理人员。"))
