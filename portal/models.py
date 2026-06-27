from django.conf import settings
from django.db import models
from django.utils import timezone


class Department(models.Model):
    name = models.CharField("科室/部门名称", max_length=100, unique=True)
    parent = models.ForeignKey(
        "self",
        verbose_name="上级部门",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )
    ding_department_id = models.CharField("钉钉部门ID", max_length=80, blank=True)
    sort_order = models.PositiveIntegerField("排序", default=0)
    is_active = models.BooleanField("启用", default=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "科室/部门"
        verbose_name_plural = "科室/部门"

    def __str__(self):
        return self.name


class PersonProfile(models.Model):
    class Role(models.TextChoices):
        DEPARTMENT_ADMIN = "department_admin", "部门行政人员"
        MANAGER = "manager", "管理人员"
        INSTRUCTOR = "instructor", "培训教员"
        STUDENT = "student", "飞行学员"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name="登录账号",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="person_profile",
    )
    name = models.CharField("姓名", max_length=60)
    employee_no = models.CharField("工号", max_length=40, unique=True)
    role = models.CharField("角色", max_length=30, choices=Role.choices, default=Role.STUDENT)
    department = models.ForeignKey(
        Department,
        verbose_name="所属科室",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="people",
    )
    position = models.CharField("岗位", max_length=80, blank=True)
    mobile = models.CharField("手机号", max_length=30, blank=True)
    email = models.EmailField("邮箱", blank=True)
    ding_user_id = models.CharField("钉钉UserId", max_length=100, blank=True, db_index=True)
    ding_union_id = models.CharField("钉钉UnionId", max_length=100, blank=True, db_index=True)
    is_active = models.BooleanField("在用", default=True)
    can_manage_conduct = models.BooleanField("可管理作风分", default=False)
    excluded_from_conduct_score = models.BooleanField("不计作风分", default=False)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        ordering = ["department__sort_order", "employee_no", "name"]
        verbose_name = "人员档案"
        verbose_name_plural = "人员档案"

    def __str__(self):
        return f"{self.name}（{self.employee_no}）"


class StudentProfile(models.Model):
    class Stage(models.TextChoices):
        S1 = "S1", "S1 基础理论"
        S2 = "S2", "S2 模拟机训练"
        S3 = "S3", "S3 本场训练"
        S4 = "S4", "S4 跟飞训练"

    person = models.OneToOneField(
        PersonProfile,
        verbose_name="人员档案",
        on_delete=models.CASCADE,
        related_name="student_profile",
    )
    stage = models.CharField("阶段", max_length=10, choices=Stage.choices, default=Stage.S1)
    class_name = models.CharField("班级/队别", max_length=80, blank=True)
    entry_date = models.DateField("入队日期", blank=True, null=True)
    initial_score = models.IntegerField("初始作风分", default=100)
    current_score = models.IntegerField("当前作风分", default=100)
    note = models.TextField("备注", blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        ordering = ["stage", "person__employee_no"]
        verbose_name = "学员档案"
        verbose_name_plural = "学员档案"

    def __str__(self):
        return str(self.person)

    def recalculate_score(self):
        delta = self.conduct_records.aggregate(total=models.Sum("score_delta"))["total"] or 0
        self.current_score = max(0, self.initial_score + delta)
        self.save(update_fields=["current_score", "updated_at"])
        return self.current_score


class ConductRule(models.Model):
    rule_id = models.CharField("规则编号", max_length=20, unique=True)
    dimension = models.CharField("维度", max_length=80)
    module = models.CharField("模块", max_length=120)
    item = models.CharField("条目", max_length=200)
    title = models.CharField("制度项目", max_length=300)
    values = models.JSONField("可选分值", default=list)
    source = models.CharField("信息来源/渠道", max_length=200, blank=True)
    is_active = models.BooleanField("启用", default=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        ordering = ["rule_id"]
        verbose_name = "作风量化规则"
        verbose_name_plural = "作风量化规则"

    def __str__(self):
        values = "/".join(str(value) for value in self.values)
        return f"{self.rule_id} {self.title}（{values}）"


class ConductRecord(models.Model):
    student = models.ForeignKey(
        StudentProfile,
        verbose_name="学员",
        on_delete=models.CASCADE,
        related_name="conduct_records",
    )
    rule = models.ForeignKey(
        ConductRule,
        verbose_name="制度项目",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="records",
    )
    score_delta = models.IntegerField("调整分值")
    reason = models.TextField("补充说明", blank=True)
    occurred_on = models.DateField("发生日期", default=timezone.localdate)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="记录人",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="conduct_records",
    )
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        ordering = ["-occurred_on", "-created_at"]
        verbose_name = "作风分记录"
        verbose_name_plural = "作风分记录"

    def __str__(self):
        sign = "+" if self.score_delta > 0 else ""
        return f"{self.student.person.name} {sign}{self.score_delta}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.student.recalculate_score()

    def delete(self, *args, **kwargs):
        student = self.student
        result = super().delete(*args, **kwargs)
        student.recalculate_score()
        return result


class LoginAudit(models.Model):
    person = models.ForeignKey(
        PersonProfile,
        verbose_name="人员",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="login_audits",
    )
    provider = models.CharField("登录方式", max_length=40, default="dingtalk")
    ip_address = models.GenericIPAddressField("IP地址", blank=True, null=True)
    user_agent = models.TextField("浏览器/客户端", blank=True)
    success = models.BooleanField("是否成功", default=True)
    message = models.CharField("说明", max_length=200, blank=True)
    created_at = models.DateTimeField("登录时间", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "登录审计"
        verbose_name_plural = "登录审计"

    def __str__(self):
        status = "成功" if self.success else "失败"
        return f"{self.person or '未知人员'} {status}"
