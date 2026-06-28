import json
import os
import re
import uuid
from urllib.parse import urlencode

from django.contrib.auth import authenticate, login, logout
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_safe

from .models import ConductRecord, ConductRule, LoginAudit, PersonProfile, ResourceCategory, StudentProfile, TrainingResource
from .services import audit, can_manage_conduct, can_manage_people, can_manage_resources, get_client_ip, get_person_for_user, get_user_agent


DEMO_KNOWLEDGE = [
    {
        "keywords": ["课件", "模板", "审核", "标准"],
        "answer": "一期建议先统一课件模板、内容结构、审核口径和版本管理。课件助手可以围绕模板中心、内容生成、场景切换、标准检查四个能力建设。",
        "sources": ["AI课件助手", "标准化建设清单"],
    },
    {
        "keywords": ["教员", "资质", "授权", "复训", "到期"],
        "answer": "教员画像应覆盖基础身份、资质授权、授课记录、训练记录、内容贡献和风险预警。到期证照、待复训、授权冲突适合配置自动提醒。",
        "sources": ["教员全生命周期画像", "近期风险提醒"],
    },
    {
        "keywords": ["组织", "架构", "中心", "科室"],
        "answer": "培训部以三个中心三个科室协同运行：飞行训练中心、乘务训练中心、模拟机维护中心，以及综合业务室、综合培训室、计划质控室。",
        "sources": ["组织架构", "组织说明"],
    },
    {
        "keywords": ["设备", "训练", "教室", "模拟机", "资源"],
        "answer": "训练资源包括飞行训练设备、乘务训练设备和多场景培训教室。现有资料中包含 B737、A320 飞行模拟机、客舱模拟器、灭火模拟器、出口模拟器、CBT 教室和普通教室等。",
        "sources": ["训练资源", "训练资源明细"],
    },
]


@require_safe
def home(request):
    return render(request, "index.html")


@require_safe
def health(request):
    return JsonResponse({"status": "ok", "service": "training-platform-django"})


@require_GET
def current_user(request):
    return JsonResponse(serialize_user_session(request.user))


@csrf_exempt
@require_http_methods(["POST"])
def local_login(request):
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "请求体不是有效 JSON"}, status=400)

    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    user = authenticate(request, username=username, password=password)
    person = get_person_for_user(user)
    LoginAudit.objects.create(
        person=person,
        provider="local",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        success=bool(user),
        message="本地账号登录" if user else f"本地账号登录失败：{username}",
    )
    if not user:
        return JsonResponse({"error": "账号或密码不正确"}, status=401)

    login(request, user)
    audit(request, "login", summary=f"{username} 登录")
    return JsonResponse(serialize_user_session(request.user))


@csrf_exempt
@require_http_methods(["POST"])
def local_logout(request):
    username = request.user.get_username() if request.user.is_authenticated else ""
    audit(request, "logout", summary=f"{username} 退出登录")
    logout(request)
    return JsonResponse({"ok": True})


@csrf_exempt
@require_http_methods(["POST"])
def ask_question(request):
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "请求体不是有效 JSON"}, status=400)

    question = str(payload.get("question", "")).strip()
    if not question:
        return JsonResponse({"answer": "请先输入问题。", "sources": []})

    for item in DEMO_KNOWLEDGE:
        if any(keyword in question for keyword in item["keywords"]):
            return JsonResponse({"answer": item["answer"], "sources": item["sources"]})

    return JsonResponse(
        {
            "answer": "Django 版本已接管本地问答入口。当前未配置外部知识库密钥，因此先返回演示知识库答案；后续可继续把原 Node 知识库接口完整迁移到 Django。",
            "sources": ["Django 本地演示知识库"],
        }
    )


@require_GET
def students(request):
    if not (request.user.is_authenticated or os.environ.get("ALLOW_PUBLIC_STUDENT_API", "1") == "1"):
        return JsonResponse({"error": "请先登录"}, status=401)
    queryset = (
        StudentProfile.objects.select_related("person", "person__department")
        .prefetch_related(
            Prefetch("conduct_records", queryset=ConductRecord.objects.select_related("rule", "recorded_by"))
        )
        .order_by("stage", "person__employee_no")
    )
    students_data = [serialize_student(student) for student in queryset]
    return JsonResponse(
        {
            "departmentName": "飞行学员管理室",
            "syncedAt": None,
            "source": "django-database",
            "students": students_data,
        }
    )


@csrf_exempt
@require_http_methods(["GET", "POST"])
def conduct_rules(request):
    if request.method == "POST":
        if not can_manage_conduct(request.user):
            return JsonResponse({"error": "没有作风分管理权限"}, status=403)
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "请求体不是有效 JSON"}, status=400)

        rule, error = build_conduct_rule_from_payload(payload)
        if error:
            return JsonResponse({"error": error}, status=400)
        rule.rule_id = str(payload.get("id", "")).strip() or f"custom-{uuid.uuid4().hex[:12]}"
        if ConductRule.objects.filter(rule_id=rule.rule_id).exists():
            return JsonResponse({"error": "规则编号已存在"}, status=400)
        rule.save()
        audit(request, "conduct.rule.create", target=rule, summary=rule.title)
        return JsonResponse({"ok": True, "rule": serialize_conduct_rule(rule)}, status=201)

    rules = ConductRule.objects.filter(is_active=True).order_by("dimension", "module", "rule_id")
    return JsonResponse({"rules": [serialize_conduct_rule(rule) for rule in rules]})


@csrf_exempt
@require_http_methods(["PATCH", "DELETE"])
def conduct_rule_detail(request, rule_id):
    if not can_manage_conduct(request.user):
        return JsonResponse({"error": "没有作风分管理权限"}, status=403)

    rule = ConductRule.objects.filter(rule_id=rule_id).first()
    if not rule:
        return JsonResponse({"error": "未找到制度项目"}, status=404)

    if request.method == "DELETE":
        rule.is_active = False
        rule.save(update_fields=["is_active", "updated_at"])
        audit(request, "conduct.rule.deactivate", target=rule, summary=rule.title)
        return JsonResponse({"ok": True, "rule": serialize_conduct_rule(rule)})

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "请求体不是有效 JSON"}, status=400)

    next_rule, error = build_conduct_rule_from_payload(payload, instance=rule)
    if error:
        return JsonResponse({"error": error}, status=400)
    next_rule.save()
    audit(request, "conduct.rule.update", target=next_rule, summary=next_rule.title)
    return JsonResponse({"ok": True, "rule": serialize_conduct_rule(next_rule)})


@csrf_exempt
@require_http_methods(["POST"])
def match_conduct_rule(request):
    if not can_manage_conduct(request.user):
        return JsonResponse({"error": "没有作风分管理权限"}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "请求体不是有效 JSON"}, status=400)

    behavior = str(payload.get("behavior", "")).strip()
    if len(behavior) < 4:
        return JsonResponse({"error": "请先填写更完整的行为描述"}, status=400)

    suggestions = suggest_conduct_rules(behavior)
    audit(
        request,
        "conduct.match",
        summary=f"智能匹配作风规则：{behavior[:40]}",
        metadata={"behavior": behavior, "matches": [item["rule"]["id"] for item in suggestions]},
    )
    return JsonResponse({"matches": suggestions})


@csrf_exempt
@require_http_methods(["POST"])
def create_conduct_record(request):
    if not can_manage_conduct(request.user):
        return JsonResponse({"error": "没有作风分管理权限"}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "请求体不是有效 JSON"}, status=400)

    student_id = str(payload.get("studentId", "")).strip()
    rule_id = str(payload.get("ruleId", "")).strip()
    reason = str(payload.get("reason", "")).strip()
    try:
        score_delta = int(payload.get("scoreDelta"))
    except (TypeError, ValueError):
        return JsonResponse({"error": "分值不正确"}, status=400)

    student = (
        StudentProfile.objects.select_related("person")
        .filter(person__ding_user_id=student_id)
        .first()
        or StudentProfile.objects.select_related("person").filter(person_id=student_id).first()
    )
    if not student:
        return JsonResponse({"error": "未找到学员"}, status=404)
    if student.person.excluded_from_conduct_score:
        return JsonResponse({"error": "行政人员不计作风分"}, status=400)

    rule = ConductRule.objects.filter(rule_id=rule_id, is_active=True).first()
    if not rule:
        return JsonResponse({"error": "未找到制度项目"}, status=404)
    if score_delta not in [int(value) for value in rule.values]:
        return JsonResponse({"error": "分值不属于该制度项目"}, status=400)

    record = ConductRecord.objects.create(
        student=student,
        rule=rule,
        score_delta=score_delta,
        reason=reason,
        recorded_by=request.user,
    )
    audit(
        request,
        "conduct.create",
        target=record,
        summary=f"{student.person.name} {score_delta:+d}",
        metadata={"student": student.person.employee_no, "rule": rule.rule_id, "reason": reason},
    )
    student.refresh_from_db()
    return JsonResponse({"ok": True, "student": serialize_student(student), "record": serialize_conduct_record(record)})


@require_GET
def resources(request):
    queryset = TrainingResource.objects.select_related("category", "uploaded_by").filter(is_active=True)
    person = get_person_for_user(request.user)
    if not request.user.is_authenticated or (person and person.role == PersonProfile.Role.STUDENT):
        queryset = queryset.filter(visibility=TrainingResource.Visibility.ALL)
    elif not can_manage_people(request.user):
        queryset = queryset.exclude(visibility=TrainingResource.Visibility.MANAGERS)

    category = request.GET.get("category", "").strip()
    if category:
        queryset = queryset.filter(category__name=category)
    return JsonResponse(
        {
            "categories": [serialize_resource_category(item) for item in ResourceCategory.objects.filter(is_active=True)],
            "resources": [serialize_resource(item, request) for item in queryset[:200]],
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
def upload_resource(request):
    if not can_manage_resources(request.user):
        return JsonResponse({"error": "没有资源库管理权限"}, status=403)

    file_obj = request.FILES.get("file")
    title = request.POST.get("title", "").strip()
    if not file_obj:
        return JsonResponse({"error": "请选择上传文件"}, status=400)
    if not title:
        title = file_obj.name

    category = None
    category_id = request.POST.get("categoryId", "").strip()
    if category_id:
        category = ResourceCategory.objects.filter(pk=category_id, is_active=True).first()

    resource = TrainingResource.objects.create(
        title=title,
        category=category,
        description=request.POST.get("description", "").strip(),
        file=file_obj,
        file_size=file_obj.size or 0,
        content_type=getattr(file_obj, "content_type", "") or "",
        version=request.POST.get("version", "").strip(),
        visibility=request.POST.get("visibility", TrainingResource.Visibility.ALL),
        applicable_stage=request.POST.get("applicableStage", "").strip(),
        uploaded_by=request.user,
    )
    audit(request, "resource.upload", target=resource, summary=resource.title, metadata={"file": resource.file.name})
    return JsonResponse({"ok": True, "resource": serialize_resource(resource, request)}, status=201)
    students_data = [serialize_student(student) for student in queryset]
    if students_data:
        return JsonResponse(
            {
                "departmentName": "飞行学员管理室",
                "syncedAt": None,
                "source": "django-database",
                "students": students_data,
            }
        )

    return JsonResponse(
        {
            "departmentName": "飞行学员管理室",
            "syncedAt": None,
            "source": "django-database",
            "students": [],
        },
    )


@require_GET
def dingtalk_start(request):
    login_url = os.environ.get(
        "TRAINING_DINGTALK_LOGIN_URL",
        "https://training-qa-api-naoki1762.onrender.com/api/auth/dingtalk/start",
    )
    return redirect(login_url)


@require_GET
def dingtalk_callback(request):
    params = urlencode(request.GET, doseq=True)
    suffix = f"?{params}" if params else ""
    return redirect(f"/{suffix}")


def serialize_student(student):
    person = student.person
    records = [serialize_conduct_record(record) for record in student.conduct_records.all()[:20]]
    return {
        "userId": person.ding_user_id or str(person.pk),
        "name": person.name,
        "title": person.position or person.get_role_display(),
        "jobNumber": person.employee_no,
        "active": person.is_active,
        "avatar": "",
        "department": person.department.name if person.department else "",
        "conductRole": "admin" if person.excluded_from_conduct_score else "student",
        "conductStage": "" if person.excluded_from_conduct_score else student.stage,
        "conductScore": None if person.excluded_from_conduct_score else student.current_score,
        "conductRecords": records,
    }


def serialize_user_session(user):
    person = get_person_for_user(user)
    return {
        "authenticated": user.is_authenticated,
        "username": user.get_username() if user.is_authenticated else "",
        "isStaff": bool(user.is_staff) if user.is_authenticated else False,
        "permissions": {
            "managePeople": can_manage_people(user),
            "manageConduct": can_manage_conduct(user),
            "manageResources": can_manage_resources(user),
        },
        "person": serialize_person(person) if person else None,
    }


def serialize_person(person):
    return {
        "id": person.pk,
        "name": person.name,
        "employeeNo": person.employee_no,
        "role": person.role,
        "roleName": person.get_role_display(),
        "department": person.department.name if person.department else "",
        "position": person.position,
        "canManageConduct": person.can_manage_conduct,
        "excludedFromConductScore": person.excluded_from_conduct_score,
    }


def serialize_resource_category(category):
    return {
        "id": category.pk,
        "name": category.name,
        "parentId": category.parent_id,
    }


def serialize_resource(resource, request):
    return {
        "id": resource.pk,
        "title": resource.title,
        "category": resource.category.name if resource.category else "",
        "description": resource.description,
        "url": request.build_absolute_uri(resource.file.url) if resource.file else "",
        "fileName": resource.file.name.rsplit("/", 1)[-1] if resource.file else "",
        "fileSize": resource.file_size,
        "contentType": resource.content_type,
        "version": resource.version,
        "visibility": resource.visibility,
        "applicableStage": resource.applicable_stage,
        "uploadedBy": resource.uploaded_by.get_username() if resource.uploaded_by else "",
        "updatedAt": resource.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
    }


def serialize_conduct_rule(rule):
    return {
        "id": rule.rule_id,
        "dimension": rule.dimension,
        "module": rule.module,
        "item": rule.item,
        "title": rule.title,
        "values": [int(value) for value in rule.values],
        "source": rule.source,
        "isActive": rule.is_active,
    }


def serialize_conduct_record(record):
    value = int(record.score_delta)
    return {
        "type": "+" if value > 0 else "-",
        "value": abs(value),
        "reason": record.reason,
        "ruleId": record.rule.rule_id if record.rule else "",
        "ruleTitle": record.rule.title if record.rule else "手工调整",
        "dimension": record.rule.dimension if record.rule else "手工调整",
        "module": record.rule.module if record.rule else "",
        "source": record.rule.source if record.rule else "",
        "operator": record.recorded_by.get_username() if record.recorded_by else "后台管理员",
        "time": record.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    }


def suggest_conduct_rules(behavior, limit=5):
    normalized_behavior = normalize_match_text(behavior)
    behavior_tokens = set(extract_match_tokens(normalized_behavior))
    results = []
    for rule in ConductRule.objects.filter(is_active=True):
        haystack = normalize_match_text(" ".join([rule.dimension, rule.module, rule.item, rule.title, rule.source]))
        rule_tokens = set(extract_match_tokens(haystack))
        overlap = behavior_tokens & rule_tokens
        direct_bonus = 0
        for field in [rule.item, rule.title, rule.module, rule.source]:
            normalized_field = normalize_match_text(field)
            if normalized_field and (normalized_field in normalized_behavior or normalized_behavior in normalized_field):
                direct_bonus += 12

        score = len(overlap) * 4 + direct_bonus
        score += len(set(normalized_behavior) & set(haystack))
        if score <= 0:
            continue

        confidence = min(98, max(35, score * 3))
        reason_words = sorted(overlap, key=len, reverse=True)[:4]
        reason = "匹配到关键词：" + "、".join(reason_words) if reason_words else "行为描述与规则文本相近"
        results.append(
            {
                "score": score,
                "confidence": confidence,
                "reason": reason,
                "rule": serialize_conduct_rule(rule),
            }
        )

    results.sort(key=lambda item: (item["score"], item["confidence"]), reverse=True)
    return [
        {
            "confidence": item["confidence"],
            "reason": item["reason"],
            "rule": item["rule"],
        }
        for item in results[:limit]
    ]


def build_conduct_rule_from_payload(payload, instance=None):
    rule = instance or ConductRule()
    values = payload.get("values", rule.values if instance else [])
    if isinstance(values, str):
        values = [value.strip() for value in re.split(r"[,，/、\s]+", values) if value.strip()]
    try:
        values = [int(value) for value in values]
    except (TypeError, ValueError):
        return rule, "分值必须是数字，可填写多个，例如 -2,-4 或 2,4"
    values = list(dict.fromkeys(values))
    if not values:
        return rule, "请至少填写一个加减分值"
    if 0 in values:
        return rule, "分值不能为 0"

    fields = {
        "dimension": str(payload.get("dimension", rule.dimension if instance else "")).strip() or "自定义规则",
        "module": str(payload.get("module", rule.module if instance else "")).strip() or "科室补充",
        "item": str(payload.get("item", rule.item if instance else "")).strip(),
        "title": str(payload.get("title", rule.title if instance else "")).strip(),
        "source": str(payload.get("source", rule.source if instance else "")).strip(),
    }
    if not fields["title"]:
        return rule, "请填写制度项目"
    if not fields["item"]:
        fields["item"] = fields["title"]

    for field, value in fields.items():
        setattr(rule, field, value)
    rule.values = values
    rule.is_active = bool(payload.get("isActive", rule.is_active if instance else True))
    return rule, ""


def normalize_match_text(value):
    return re.sub(r"\s+", "", str(value or "").lower())


def extract_match_tokens(value):
    tokens = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]{2,}", value)
    expanded = []
    for token in tokens:
        expanded.append(token)
        if re.fullmatch(r"[\u4e00-\u9fff]{2,}", token):
            expanded.extend(token[index : index + 2] for index in range(len(token) - 1))
            expanded.extend(token[index : index + 3] for index in range(len(token) - 2))
    return [token for token in expanded if len(token) >= 2]
