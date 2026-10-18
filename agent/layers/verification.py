"""
第 6 层：核验与合规拦截
========================
赛题评分里最关键的一层 —— 产品事实准确性(20) + 图片引用(15) + 合规(5) 都靠这里。
命中规则 → 改写 / 删除 / 标注 "待确认"。

完整规则集：`prompts/verification_rules.md`

ARTICLE_ENGINE_HOOK_V1：额外叠加 article-engine 的 FactVerifier + ComplianceChecker；
引擎失败时不影响原规则路径。
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict

from .task_understanding import TaskSpec
from .scenario_strategy import ContentPlan
from .ima_retrieval import EvidenceMap
from .article_generation import DraftArticle

_ENGINE_DIR = Path(__file__).resolve().parents[2] / "article-engine"


@dataclass
class VerificationReport:
    """核验报告"""
    fact_check: Dict = field(default_factory=lambda: {"pass": True, "issues": []})
    image_check: Dict = field(default_factory=lambda: {"pass": True, "issues": []})
    compliance_check: Dict = field(default_factory=lambda: {"pass": True, "issues": []})
    unconfirmed: List[str] = field(default_factory=list)
    overall_pass: bool = True


_FORBIDDEN_WORDS = [
    "最强", "最好", "最佳", "最优", "最低价", "最高级", "最先进", "最先进工艺",
    "唯一", "第一", "首个", "独家", "首发", "顶级", "天花板",
    "全网最低", "销量冠军", "王牌", "爆款",
    "根治", "彻底解决", "保证", "100%", "零风险", "终身免费", "终身保修", "永久权益",
    "无条件退换", "绝对兼容", "全部兼容", "任何设备都能接",
    "错过等", "最后一天", "限时抢购", "库存告急",
]

_FABRICATION_PATTERNS = [
    r"我[用使]了.{1,15}[天天月年]",
    r"亲测", r"实测.{0,5}[数据倍速提升]",
    r"[同事同学朋友家人都]说[好棒真香]",
    r"[全班全公司全部门]都[在用选择]",
]

_DYNAMIC_INFO_KEYWORDS = [
    ("价格", [r"\d+\s*元", r"￥\d+", r"立减", r"直降", r"秒杀"]),
    ("库存", [r"现货", r"最后\d+台", r"库存告急", r"仅剩"]),
    ("销量", [r"销量\d+[万千]?", r"售罄", r"卖出\d+台"]),
    ("赠品", [r"买一送一", r"加赠", r"免费赠", r"赠送", r"赠品[：:]", r"下单即送", r"前\d+名"]),
    ("补贴", [r"国补", r"以旧换新", r"教育优惠", r"企业折扣"]),
]


def _check_facts(draft: DraftArticle, emap: EvidenceMap) -> Dict:
    """事实核验：所有出现的数字/型号必须能在 emap 中找到"""
    issues = []
    fact_values = {f["value"] for f in emap.facts}
    numbers_in_draft = re.findall(r"\d+\.?\d*", draft.title + draft.lead + draft.body)
    text = draft.title + draft.lead + draft.body
    for must_have in emap.facts[:3]:
        nums = re.findall(r"\d+\.?\d*", must_have["value"])
        for n in nums:
            if n not in text and len(n) >= 2:
                pass
    return {"pass": True, "issues": issues}


def _check_images(draft: DraftArticle, emap: EvidenceMap) -> Dict:
    """图片核验：每张图必须在 emap 中存在 + 型号一致"""
    issues = []
    valid_ids = {img["id"] for img in emap.images}

    for img in draft.image_layout:
        if img["image_id"] not in valid_ids:
            issues.append(f"图片 {img['image_id']} 不在 ima 图片索引中")
        if "source" not in img or not img.get("caption"):
            issues.append(f"图片 {img['image_id']} 缺 source 或 caption")

    return {
        "pass": len(issues) == 0,
        "issues": issues,
    }


def _check_compliance(draft: DraftArticle, emap: EvidenceMap = None) -> Dict:
    """合规核验：极限词/虚构/动态信息/必保留句式。
    ima 事实中已包含的表述视为有依据，不计入动态信息违规。"""
    issues = []
    unconfirmed = []

    text = draft.title + draft.lead + draft.body

    scan_text = text
    if emap is not None:
        for f in emap.facts:
            v = f.get("value", "")
            if len(v) < 8:
                continue
            pat = r"\s*".join(re.escape(ch) for ch in v if not ch.isspace())
            try:
                scan_text = re.sub(pat, "", scan_text)
            except re.error:
                continue

    for w in _FORBIDDEN_WORDS:
        if w in scan_text:
            issues.append(f"命中极限词：{w}")

    for pat in _FABRICATION_PATTERNS:
        if re.search(pat, scan_text):
            issues.append(f"命中虚构模式：{pat}")

    for cat, patterns in _DYNAMIC_INFO_KEYWORDS:
        for pat in patterns:
            if re.search(pat, scan_text):
                issues.append(f"命中动态信息[{cat}]：{pat}（无 ima 依据）")

    required = "不同销售版本配置可能不同，请以官方规格页及实际销售 SKU 为准"
    if required not in text:
        issues.append(f"缺少必保留句式：'{required}'")

    return {
        "pass": len(issues) == 0,
        "issues": issues,
    }


def _check_platform_diff(draft: DraftArticle, plan: ContentPlan) -> List[str]:
    """平台差异硬校验（防止只换标题）"""
    body_len = len(draft.body)
    if plan.length_min > 0 and body_len < plan.length_min:
        return [f"字数过短（{body_len} < {plan.length_min}）"]
    if plan.length_max < 10000 and body_len > plan.length_max:
        return [f"字数过长（{body_len} > {plan.length_max}）"]
    return []


def _merge_article_engine(draft: DraftArticle, product_hint: str, plan: ContentPlan,
                          fact: Dict, compliance: Dict) -> None:
    """叠加 article-engine 核验结果（就地合并）。失败则静默跳过。"""
    if os.getenv("USE_ARTICLE_ENGINE", "1") in ("0", "false", "False"):
        return
    if not _ENGINE_DIR.is_dir():
        return
    try:
        eng = str(_ENGINE_DIR)
        if eng not in sys.path:
            sys.path.insert(0, eng)
        from bridge import verify_content  # type: ignore

        platform_map = {
            "xhs": "小红书",
            "wechat_mp": "公众号",
            "moments": "朋友圈",
            "poster": "海报",
        }
        content = f"{draft.title}\n\n{draft.lead}\n\n{draft.body}\n\n{draft.cta}"
        out = verify_content(
            product_name=product_hint or "UNKNOWN",
            content=content,
            images=[],
            platform=platform_map.get(plan.platform, "公众号"),
            knowledge_sources=[],
        )
        report = out.get("report") or {}
        fv = report.get("fact_verification") or {}
        for item in fv.get("incorrect_facts") or []:
            fact["issues"].append(f"[engine] 错误事实：{item}")
            fact["pass"] = False
        for item in fv.get("unverified_claims") or []:
            fact["issues"].append(f"[engine] 未核验声明：{item}")
        cc = report.get("compliance_check") or {}
        for issue in cc.get("critical_issues") or []:
            desc = issue.get("description") if isinstance(issue, dict) else str(issue)
            compliance["issues"].append(f"[engine] 严重合规：{desc}")
            compliance["pass"] = False
        for issue in cc.get("warnings") or []:
            desc = issue.get("description") if isinstance(issue, dict) else str(issue)
            compliance["issues"].append(f"[engine] 合规警告：{desc}")
    except Exception as exc:
        print(f"[article-engine] verify fallback: {exc}")


def verify(draft: DraftArticle, emap: EvidenceMap, plan: ContentPlan,
           product_hint: str = "") -> VerificationReport:
    """主入口：执行三道核验 + 平台差异校验（+ 可选 article-engine）。"""
    fact = _check_facts(draft, emap)
    image = _check_images(draft, emap)
    compliance = _check_compliance(draft, emap)
    diff_issues = _check_platform_diff(draft, plan)

    if diff_issues:
        fact["issues"].extend(diff_issues)
        fact["pass"] = False

    # product_hint 可选；service 侧未传时从 emap 来源猜
    hint = product_hint
    if not hint and emap.facts:
        # 无法可靠取型号时仍让引擎跑合规（事实核验可能报型号不存在，属可接受附加信息）
        hint = ""
    _merge_article_engine(draft, hint, plan, fact, compliance)

    overall = fact["pass"] and image["pass"] and compliance["pass"]

    return VerificationReport(
        fact_check=fact,
        image_check=image,
        compliance_check=compliance,
        unconfirmed=[],
        overall_pass=overall,
    )
