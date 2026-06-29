import json
import os
import re
import ssl
import urllib.error
import urllib.request

import certifi
from django.db.models import Q

from .models import ConductRule, KnowledgeChunk, KnowledgeDocument, TrainingResource


def tokenize(text):
    compact = re.sub(r"\s+", "", str(text or "").lower())
    chinese_terms = re.findall(r"[\u4e00-\u9fff]{2,}", compact)
    latin_terms = re.findall(r"[a-z0-9]{2,}", compact)
    terms = set(latin_terms)
    for term in chinese_terms:
      terms.add(term)
      if len(term) > 4:
          terms.update(term[index : index + 2] for index in range(len(term) - 1))
          terms.update(term[index : index + 3] for index in range(len(term) - 2))
    return {term for term in terms if term}


def split_text_into_chunks(text, *, size=900, overlap=120):
    text = re.sub(r"\n{3,}", "\n\n", str(text or "").strip())
    if not text:
        return []
    paragraphs = [item.strip() for item in re.split(r"\n\s*\n", text) if item.strip()]
    chunks = []
    current = ""
    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 <= size:
            current = f"{current}\n\n{paragraph}".strip()
            continue
        if current:
            chunks.append(current)
        current = paragraph
    if current:
        chunks.append(current)

    expanded = []
    for chunk in chunks:
        if len(chunk) <= size:
            expanded.append(chunk)
            continue
        start = 0
        while start < len(chunk):
            expanded.append(chunk[start : start + size])
            start += max(1, size - overlap)
    return expanded


def rebuild_document_chunks(document):
    document.chunks.all().delete()
    body = document.content or document.summary
    chunks = split_text_into_chunks(body)
    KnowledgeChunk.objects.bulk_create(
        [
            KnowledgeChunk(
                document=document,
                title=document.title,
                content=chunk,
                sort_order=index,
                metadata={"category": document.category, "version": document.version},
            )
            for index, chunk in enumerate(chunks, start=1)
        ]
    )
    return len(chunks)


def visible_document_filter(user):
    if user.is_authenticated and (user.is_staff or user.is_superuser):
        return Q(document__is_active=True)
    person = getattr(user, "person_profile", None) if user.is_authenticated else None
    if person and person.role in {"department_admin", "manager"}:
        return Q(document__is_active=True)
    if person and person.role == "instructor":
        return Q(document__is_active=True) & ~Q(document__visibility=KnowledgeDocument.Visibility.MANAGERS)
    return Q(document__is_active=True, document__visibility=KnowledgeDocument.Visibility.ALL)


def score_text(question_terms, text):
    text_terms = tokenize(text)
    if not text_terms:
        return 0
    exact = len(question_terms & text_terms)
    contains = sum(1 for term in question_terms if len(term) >= 3 and term in str(text).lower())
    return exact * 4 + contains


def search_knowledge(question, user, *, limit=6):
    question_terms = tokenize(question)
    candidates = []

    chunks = KnowledgeChunk.objects.select_related("document").filter(visible_document_filter(user))[:400]
    for chunk in chunks:
        score = score_text(question_terms, f"{chunk.title}\n{chunk.content}")
        if score:
            candidates.append(
                {
                    "score": score,
                    "title": chunk.document.title,
                    "content": chunk.content,
                    "source": {
                        "title": chunk.document.title,
                        "category": chunk.document.category,
                        "version": chunk.document.version,
                    },
                }
            )

    rules = ConductRule.objects.filter(is_active=True)[:300]
    for rule in rules:
        text = f"{rule.dimension} {rule.module} {rule.item} {rule.title} {rule.source} {rule.values}"
        score = score_text(question_terms, text)
        if score:
            candidates.append(
                {
                    "score": score + 2,
                    "title": rule.title,
                    "content": f"{rule.title}；分值：{'/'.join(str(value) for value in rule.values)}；维度：{rule.dimension}；模块：{rule.module}；来源：{rule.source or '未注明'}",
                    "source": {
                        "title": rule.title,
                        "category": "作风量化规则",
                        "version": rule.rule_id,
                    },
                }
            )

    resources = TrainingResource.objects.select_related("category").filter(is_active=True)[:200]
    for resource in resources:
        text = f"{resource.title} {resource.description} {resource.category} {resource.version}"
        score = score_text(question_terms, text)
        if score:
            candidates.append(
                {
                    "score": score,
                    "title": resource.title,
                    "content": f"{resource.title}：{resource.description or '暂无说明'}",
                    "source": {
                        "title": resource.title,
                        "category": resource.category.name if resource.category else "训练资源",
                        "version": resource.version,
                        "url": resource.file.url if resource.file else "",
                    },
                }
            )

    candidates.sort(key=lambda item: item["score"], reverse=True)
    deduped = []
    seen = set()
    for item in candidates:
        key = (item["source"].get("title"), item["content"][:80])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= limit:
            break
    return deduped


def build_fallback_answer(question, contexts):
    if not contexts:
        return "当前知识库未找到明确依据。请联系培训部管理人员补充相关手册、制度或流程文件。"
    lines = ["根据当前知识库，检索到以下可能相关依据："]
    for index, item in enumerate(contexts[:4], start=1):
        lines.append(f"{index}. {item['content'][:220]}")
    lines.append("请以正式制度原文和管理人员确认为准。")
    return "\n".join(lines)


def call_deepseek(question, contexts, user_label):
    api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("LLM_API_KEY")
    if not api_key:
        return "", "未配置 DeepSeek API Key"

    api_url = os.environ.get("DEEPSEEK_API_URL") or os.environ.get(
        "LLM_API_URL", "https://api.deepseek.com/chat/completions"
    )
    model = os.environ.get("DEEPSEEK_MODEL") or os.environ.get("LLM_MODEL", "deepseek-chat")
    context_text = "\n\n".join(
        f"[资料{index}] {item['title']}\n{item['content']}"
        for index, item in enumerate(contexts, start=1)
    ) or "未检索到资料。"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是深圳航空培训部管理平台的制度知识库助手。"
                    "必须优先依据给定资料回答，不得编造制度条款。"
                    "如果资料不足，要明确说明当前知识库未找到明确依据。"
                    "回答结构固定为：结论、依据、提醒。"
                    "语气专业、简洁，面向培训部内部用户。"
                ),
            },
            {
                "role": "user",
                "content": f"提问人：{user_label}\n问题：{question}\n\n可用资料：\n{context_text}",
            },
        ],
        "temperature": 0.2,
        "max_tokens": 900,
    }
    request = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        context = ssl.create_default_context(cafile=certifi.where())
        with urllib.request.urlopen(request, timeout=45, context=context) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="ignore")[:300]
        return "", f"DeepSeek HTTP {error.code}: {detail}"
    except Exception as error:
        return "", str(error)

    answer = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    return answer, ""


def answer_question(question, user):
    contexts = search_knowledge(question, user)
    user_label = user.get_username() if user.is_authenticated else "未登录用户"
    answer, error = call_deepseek(question, contexts, user_label)
    if not answer:
        answer = build_fallback_answer(question, contexts)
    sources = [item["source"] for item in contexts]
    return {
        "answer": answer,
        "sources": sources,
        "model": os.environ.get("DEEPSEEK_MODEL") or os.environ.get("LLM_MODEL", "deepseek-chat"),
        "error": error,
        "usedFallback": bool(error),
    }
