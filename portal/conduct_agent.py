import re


class ConductBehaviorAgent:
    name = "作风分识别 Agent"
    provider = "local-policy-agent"

    positive_keywords = [
        "帮助",
        "协助",
        "支援",
        "支持",
        "参与",
        "承担",
        "完成",
        "贡献",
        "优秀",
        "主动",
        "拍摄",
        "摄影",
        "宣传",
        "新闻",
        "稿件",
        "文章",
        "媒体",
        "报道",
        "入列",
        "仪式",
        "活动",
        "公司级",
        "部门级",
        "科室建设",
        "表彰",
        "获奖",
        "创新",
        "开发",
        "制作",
    ]
    negative_keywords = [
        "未",
        "没有",
        "迟到",
        "早退",
        "旷",
        "缺席",
        "违反",
        "违规",
        "违纪",
        "不合格",
        "擅自",
        "拒绝",
        "瞒报",
        "漏报",
        "离开",
        "未请假",
        "作弊",
        "冲突",
        "投诉",
        "损坏",
        "防疫",
        "口罩",
        "饮酒",
        "打架",
        "不服从",
    ]
    contribution_domains = [
        ("宣传保障", ["拍摄", "摄影", "宣传", "新闻", "稿件", "文章", "媒体", "报道", "入列", "仪式"]),
        ("公司建设", ["公司级", "公司", "建设", "贡献", "活动", "支援", "支持", "协助"]),
        ("教学训练支持", ["课件", "教学", "训练", "教研", "教员", "模拟机", "开发", "制作"]),
        ("团队帮带", ["帮助", "同学", "团队", "帮带", "困难"]),
    ]

    def analyze(self, behavior):
        normalized_behavior = normalize_match_text(behavior)
        positive_hits = [keyword for keyword in self.positive_keywords if keyword in normalized_behavior]
        negative_hits = [keyword for keyword in self.negative_keywords if keyword in normalized_behavior]
        domain_hits = [
            domain
            for domain, keywords in self.contribution_domains
            if any(keyword in normalized_behavior for keyword in keywords)
        ]

        polarity = self._detect_polarity(positive_hits, negative_hits)
        if polarity == "positive":
            action = "建议优先匹配加分项"
        elif polarity == "negative":
            action = "建议优先匹配扣分项"
        elif polarity == "mixed":
            action = "行为同时包含正向和负向信号，需管理员复核"
        else:
            action = "未识别明确倾向，按制度文本相似度匹配"

        confidence = self._confidence(positive_hits, negative_hits, domain_hits)
        return {
            "agent": self.name,
            "provider": self.provider,
            "polarity": polarity,
            "action": action,
            "confidence": confidence,
            "positiveSignals": positive_hits[:6],
            "negativeSignals": negative_hits[:6],
            "domains": domain_hits[:4],
        }

    def suggest(self, behavior, rules, limit=5):
        normalized_behavior = normalize_match_text(behavior)
        behavior_tokens = set(extract_match_tokens(normalized_behavior))
        analysis = self.analyze(behavior)
        results = []

        for rule in rules:
            serialized_rule = serialize_rule_for_agent(rule)
            haystack = normalize_match_text(" ".join([rule.dimension, rule.module, rule.item, rule.title, rule.source]))
            rule_tokens = set(extract_match_tokens(haystack))
            overlap = behavior_tokens & rule_tokens
            rule_polarity = get_rule_polarity(rule)
            direct_bonus = 0
            for field in [rule.item, rule.title, rule.module, rule.source]:
                normalized_field = normalize_match_text(field)
                if normalized_field and (normalized_field in normalized_behavior or normalized_behavior in normalized_field):
                    direct_bonus += 12

            score = len(overlap) * 4 + direct_bonus
            score += len(set(normalized_behavior) & set(haystack))
            score += self._polarity_bonus(analysis["polarity"], rule_polarity)
            score += self._domain_bonus(analysis, haystack)
            if score <= 0:
                continue

            confidence = min(98, max(35, score * 3))
            reason_words = sorted(overlap, key=len, reverse=True)[:4]
            reason = self._reason(analysis, reason_words)
            results.append(
                {
                    "score": score,
                    "confidence": confidence,
                    "reason": reason,
                    "agentDecision": {
                        "behaviorPolarity": analysis["polarity"],
                        "rulePolarity": rule_polarity,
                    },
                    "rule": serialized_rule,
                }
            )

        results.sort(key=lambda item: (item["score"], item["confidence"]), reverse=True)
        matches = [
            {
                "confidence": item["confidence"],
                "reason": item["reason"],
                "agentDecision": item["agentDecision"],
                "rule": item["rule"],
            }
            for item in results[:limit]
        ]
        return {"analysis": analysis, "matches": matches}

    def _detect_polarity(self, positive_hits, negative_hits):
        positive_score = len(positive_hits)
        negative_score = len(negative_hits)
        if positive_score and negative_score:
            if positive_score >= negative_score + 2:
                return "positive"
            if negative_score >= positive_score + 2:
                return "negative"
            return "mixed"
        if positive_score:
            return "positive"
        if negative_score:
            return "negative"
        return "neutral"

    def _confidence(self, positive_hits, negative_hits, domain_hits):
        signal_count = len(positive_hits) + len(negative_hits) + len(domain_hits)
        return min(96, 45 + signal_count * 9)

    def _polarity_bonus(self, behavior_polarity, rule_polarity):
        if behavior_polarity == "positive":
            return 34 if rule_polarity == "positive" else -24
        if behavior_polarity == "negative":
            return 34 if rule_polarity == "negative" else -18
        if behavior_polarity == "mixed" and rule_polarity == "mixed":
            return 10
        return 0

    def _domain_bonus(self, analysis, haystack):
        bonus = 0
        for domain, keywords in self.contribution_domains:
            if domain in analysis["domains"] and any(keyword in haystack for keyword in keywords):
                bonus += 10
        return bonus

    def _reason(self, analysis, reason_words):
        parts = [analysis["action"]]
        if analysis["domains"]:
            parts.append("场景：" + "、".join(analysis["domains"]))
        if reason_words:
            parts.append("关键词：" + "、".join(reason_words))
        return "；".join(parts)


def serialize_rule_for_agent(rule):
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


def get_rule_polarity(rule):
    values = [int(value) for value in rule.values]
    has_positive = any(value > 0 for value in values)
    has_negative = any(value < 0 for value in values)
    if has_positive and has_negative:
        return "mixed"
    if has_positive:
        return "positive"
    if has_negative:
        return "negative"
    return "neutral"


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
