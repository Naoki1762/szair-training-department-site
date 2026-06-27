import json
import os
from urllib.parse import urlencode

from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_safe


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
    return JsonResponse(
        {
            "error": "Django 学员同步接口尚未配置钉钉凭证。",
            "code": "STUDENT_SYNC_NOT_CONFIGURED",
        },
        status=503,
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

# Create your views here.
