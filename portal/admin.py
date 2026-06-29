from django.contrib import admin

from .models import (
    ConductRecord,
    ConductRule,
    Department,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeQueryLog,
    LoginAudit,
    OperationAudit,
    PersonProfile,
    ResourceCategory,
    StudentProfile,
    SystemSetting,
    TrainingResource,
)
from .knowledge_agent import rebuild_document_chunks


admin.site.site_header = "深圳航空培训部管理后台"
admin.site.site_title = "培训部管理后台"
admin.site.index_title = "后台管理"


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "ding_department_id", "sort_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "ding_department_id")
    ordering = ("sort_order", "name")


class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    extra = 0
    fields = ("stage", "class_name", "entry_date", "initial_score", "current_score", "note")
    readonly_fields = ("current_score",)


@admin.register(PersonProfile)
class PersonProfileAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "employee_no",
        "role",
        "department",
        "position",
        "is_active",
        "can_manage_conduct",
        "excluded_from_conduct_score",
    )
    list_filter = ("role", "department", "is_active", "can_manage_conduct", "excluded_from_conduct_score")
    search_fields = ("name", "employee_no", "mobile", "ding_user_id", "ding_union_id")
    autocomplete_fields = ("user", "department")
    inlines = (StudentProfileInline,)
    ordering = ("department__sort_order", "employee_no")


class ConductRecordInline(admin.TabularInline):
    model = ConductRecord
    extra = 0
    autocomplete_fields = ("rule", "recorded_by")
    fields = ("occurred_on", "rule", "score_delta", "reason", "recorded_by")
    readonly_fields = ()


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = (
        "person_name",
        "employee_no",
        "stage",
        "class_name",
        "current_score",
        "department",
        "updated_at",
    )
    list_filter = ("stage", "person__department", "person__is_active")
    search_fields = ("person__name", "person__employee_no", "class_name")
    autocomplete_fields = ("person",)
    readonly_fields = ("current_score", "created_at", "updated_at")
    inlines = (ConductRecordInline,)
    actions = ("recalculate_scores",)
    ordering = ("stage", "person__employee_no")

    @admin.display(description="姓名", ordering="person__name")
    def person_name(self, obj):
        return obj.person.name

    @admin.display(description="工号", ordering="person__employee_no")
    def employee_no(self, obj):
        return obj.person.employee_no

    @admin.display(description="科室", ordering="person__department")
    def department(self, obj):
        return obj.person.department

    @admin.action(description="重新计算所选学员作风分")
    def recalculate_scores(self, request, queryset):
        count = 0
        for student in queryset:
            student.recalculate_score()
            count += 1
        self.message_user(request, f"已重新计算 {count} 名学员作风分。")


@admin.register(ConductRule)
class ConductRuleAdmin(admin.ModelAdmin):
    list_display = ("rule_id", "dimension", "module", "title", "values", "source", "is_active")
    list_editable = ("is_active",)
    list_filter = ("dimension", "module", "is_active")
    search_fields = ("rule_id", "dimension", "module", "item", "title", "source")
    fields = ("rule_id", "dimension", "module", "item", "title", "values", "source", "is_active")
    actions = ("activate_rules", "deactivate_rules")
    ordering = ("rule_id",)

    @admin.action(description="启用所选作风规则")
    def activate_rules(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"已启用 {count} 条作风规则。")

    @admin.action(description="停用所选作风规则")
    def deactivate_rules(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"已停用 {count} 条作风规则。")


@admin.register(ConductRecord)
class ConductRecordAdmin(admin.ModelAdmin):
    list_display = ("student", "rule", "score_delta", "occurred_on", "recorded_by", "created_at")
    list_filter = ("occurred_on", "rule__dimension", "rule__module")
    search_fields = ("student__person__name", "student__person__employee_no", "rule__title", "reason")
    autocomplete_fields = ("student", "rule", "recorded_by")
    date_hierarchy = "occurred_on"
    ordering = ("-occurred_on", "-created_at")


@admin.register(LoginAudit)
class LoginAuditAdmin(admin.ModelAdmin):
    list_display = ("person", "provider", "success", "ip_address", "message", "created_at")
    list_filter = ("provider", "success", "created_at")
    search_fields = ("person__name", "person__employee_no", "ip_address", "message")
    readonly_fields = ("person", "provider", "ip_address", "user_agent", "success", "message", "created_at")
    ordering = ("-created_at",)


@admin.register(ResourceCategory)
class ResourceCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "sort_order", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name",)
    ordering = ("sort_order", "name")


@admin.register(TrainingResource)
class TrainingResourceAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "visibility",
        "applicable_stage",
        "version",
        "file_size",
        "uploaded_by",
        "is_active",
        "updated_at",
    )
    list_filter = ("visibility", "category", "applicable_stage", "is_active")
    search_fields = ("title", "description", "version", "file")
    autocomplete_fields = ("category", "uploaded_by")
    readonly_fields = ("file_size", "content_type", "created_at", "updated_at")
    ordering = ("-updated_at",)

    def save_model(self, request, obj, form, change):
        if obj.file:
            obj.file_size = getattr(obj.file, "size", 0) or 0
            obj.content_type = getattr(obj.file.file, "content_type", "") or obj.content_type
        if not obj.uploaded_by:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)


class KnowledgeChunkInline(admin.TabularInline):
    model = KnowledgeChunk
    extra = 0
    fields = ("sort_order", "title", "content")
    readonly_fields = ()


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "version", "visibility", "is_active", "uploaded_by", "updated_at")
    list_filter = ("category", "visibility", "is_active")
    search_fields = ("title", "category", "content", "summary")
    readonly_fields = ("created_at", "updated_at")
    inlines = (KnowledgeChunkInline,)
    actions = ("rebuild_chunks",)
    ordering = ("category", "title")

    def save_model(self, request, obj, form, change):
        if not obj.uploaded_by:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)
        rebuild_document_chunks(obj)

    @admin.action(description="重建所选资料的知识片段")
    def rebuild_chunks(self, request, queryset):
        total = 0
        for document in queryset:
            total += rebuild_document_chunks(document)
        self.message_user(request, f"已重建 {queryset.count()} 份资料，共 {total} 个知识片段。")


@admin.register(KnowledgeChunk)
class KnowledgeChunkAdmin(admin.ModelAdmin):
    list_display = ("document", "sort_order", "title", "created_at")
    list_filter = ("document__category", "document__visibility")
    search_fields = ("document__title", "title", "content")
    autocomplete_fields = ("document",)
    ordering = ("document", "sort_order")


@admin.register(KnowledgeQueryLog)
class KnowledgeQueryLogAdmin(admin.ModelAdmin):
    list_display = ("question", "user", "model", "success", "created_at")
    list_filter = ("success", "model", "created_at")
    search_fields = ("question", "answer", "user__username", "error")
    readonly_fields = ("user", "question", "answer", "sources", "model", "success", "error", "ip_address", "created_at")
    ordering = ("-created_at",)


@admin.register(OperationAudit)
class OperationAuditAdmin(admin.ModelAdmin):
    list_display = ("actor", "action", "target_type", "target_id", "summary", "ip_address", "created_at")
    list_filter = ("action", "target_type", "created_at")
    search_fields = ("actor__username", "summary", "target_type", "target_id")
    readonly_fields = ("actor", "action", "target_type", "target_id", "summary", "metadata", "ip_address", "user_agent", "created_at")
    ordering = ("-created_at",)


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ("key", "description", "updated_at")
    search_fields = ("key", "value", "description")
    ordering = ("key",)
