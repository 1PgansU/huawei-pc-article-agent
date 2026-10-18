"""Evidence-grounded draft generation with neutral text for missing facts.

优先尝试 article-engine（失败则回退本文件原模板逻辑）。
前端契约不变：仍返回 DraftArticle。
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .task_understanding import TaskSpec
from .scenario_strategy import ContentPlan
from .ima_retrieval import EvidenceMap

# --- ARTICLE_ENGINE_HOOK_V1 ---
_ENGINE_DIR = Path(__file__).resolve().parents[2] / "article-engine"
_PLATFORM_TO_ENGINE = {
    "xhs": "小红书",
    "wechat_mp": "公众号",
    "moments": "朋友圈",
    "poster": "海报",
}
_SCENARIO_TO_ENGINE = {
    "school_season": "学生学习",
    "business_office": "移动办公",
    "content_creation": "内容创作",
    "family_refresh": "移动办公",
    "enterprise_procurement": "企业IT",
    "store_visit": "移动办公",
    "new_launch": "移动办公",
    "holiday": "移动办公",
}


@dataclass
class DraftArticle:
    """Structured article draft."""
    title: str
    lead: str
    body: str
    cta: str
    image_layout: List[Dict] = field(default_factory=list)


def _fact_values(emap: EvidenceMap) -> Dict[str, str]:
    return {str(f.get("key", "")): str(f.get("value", "")) for f in emap.facts if f.get("value")}


def _gen_title(task: TaskSpec, plan: ContentPlan) -> str:
    if plan.platform == "xhs":
        return f"{task.product_hint}怎么选：先核对真实版本"
    if plan.platform == "wechat_mp":
        return f"{task.audience}选购参考：{task.product_hint}场景拆解"
    if plan.platform == "moments":
        return f"{task.product_hint}｜{plan.highlight_order[0]}"
    return task.product_hint


def _gen_lead(task: TaskSpec, plan: ContentPlan) -> str:
    return f"{plan.angle}。{task.audience}在选购前，应先核对具体配置与销售版本。"


def _neutral_fact(key: str) -> str:
    return f"{key}信息需以当前销售 SKU 的官方规格页为准，本文不作未经证实的参数承诺。"


def _gen_body(task: TaskSpec, plan: ContentPlan, emap: EvidenceMap) -> str:
    facts = _fact_values(emap)
    paragraphs = [f"{plan.angle}。以下基于可追溯资料整理，不构成个人体验或兼容承诺。"]
    for highlight in plan.highlight_order[:4]:
        value = facts.get(highlight)
        paragraphs.append(f"**{highlight}**：{value if value else _neutral_fact(highlight)}")
    paragraphs.append("不同销售版本配置可能不同，请以官方规格页及实际销售 SKU 为准。本文不固化价格、库存、赠品与政策，以发布当日授权渠道为准。")
    return "\n\n".join(paragraphs)


def _gen_image_layout(plan: ContentPlan, emap: EvidenceMap) -> List[Dict]:
    selected = emap.images[: min(plan.image_max, len(emap.images))]
    positions = ["开头", "中段", "中段", "结尾", "结尾"]
    return [{"position": positions[i] if i < len(positions) else "中段", "image_id": image["id"], "caption": image.get("desc", "产品图片"), "source": image.get("source", ""), "preview_url": image.get("preview_url", "")} for i, image in enumerate(selected)]


def _pad_body(body: str, task: TaskSpec, plan: ContentPlan, emap: EvidenceMap) -> str:
    """Reach a channel's minimum with useful evidence-review guidance, never new specs."""
    facts = _fact_values(emap)
    topics = list(plan.highlight_order) or ["配置", "使用场景", "售后服务"]
    paragraphs = [
        f"建议将{task.scenario}中的真实任务逐项列出，再对照产品事实与当前销售 SKU。",
        "核对时应区分系列宣传语和具体型号规格；未出现在来源中的数字、价格、权益或兼容承诺不应写成结论。",
        "如果同一产品存在多个销售版本，应记录处理器、内存、存储、屏幕和配件差异，并以授权渠道页面为准。",
        "对于续航、重量、亮度等会受模式或版本影响的描述，发布前应保留测试条件，不把实验室数据改写成个人体验。",
        "购买建议应围绕目标人群的任务优先级展开，同时给读者留下到店核对真机和咨询具体配置的入口。",
    ]
    index = 0
    max_iterations = max(len(paragraphs) * 20, 100)
    while len(body) < plan.length_min and index < max_iterations:
        topic = topics[index % len(topics)]
        value_hint = facts.get(topic)
        extra = paragraphs[index % len(paragraphs)]
        if value_hint and index % 2 == 0:
            extra += f"当前资料中的{topic}依据为：{value_hint}"
        body += "\n\n" + extra
        index += 1
    return body


def _try_article_engine(task: TaskSpec, plan: ContentPlan, emap: EvidenceMap) -> Optional[DraftArticle]:
    """调用 article-engine；失败返回 None。配图仍用 emap，保证图片核验可过。"""
    if os.getenv("USE_ARTICLE_ENGINE", "1") in ("0", "false", "False"):
        return None
    if not _ENGINE_DIR.is_dir():
        return None
    try:
        eng = str(_ENGINE_DIR)
        if eng not in sys.path:
            sys.path.insert(0, eng)
        from bridge import generate_article  # type: ignore

        platform = _PLATFORM_TO_ENGINE.get(plan.platform, plan.platform)
        scenario = _SCENARIO_TO_ENGINE.get(task.scenario, "移动办公")
        result = generate_article(
            product_name=task.product_hint,
            scenario=scenario,
            platform=platform,
            target_audience=task.audience or "通用用户",
            auto_fix=True,
        )
        if not result or result.get("status") not in ("success", "failed"):
            # failed 仍可能带 article；仅完全无稿时放弃
            if not result or not result.get("article"):
                return None
        art = result.get("article") or {}
        title = (art.get("selected_title") or result.get("title") or "").strip()
        opening = (art.get("opening") or "").strip()
        body = (art.get("body") or "").strip()
        cta = (art.get("cta") or plan.cta or "").strip()
        if not title or not body:
            return None
        # 与原模板对齐：补长度 / 截断 / 必保留句式
        if len(body) < plan.length_min:
            body = _pad_body(body, task, plan, emap)
        if len(body) > plan.length_max and plan.length_max >= plan.length_min:
            tail = "不同销售版本配置可能不同，请以官方规格页及实际销售 SKU 为准。"
            body = body.replace(tail, "").rstrip()
            limit = max(plan.length_min, plan.length_max - len(tail) - 2)
            body = body[:limit].rstrip() + "\n\n" + tail
        while len(body) < plan.length_min:
            body += "\n\n发布前请再次核对当前销售 SKU 的官方资料与渠道信息。"
        lead = opening or _gen_lead(task, plan)
        return DraftArticle(
            title=title,
            lead=lead,
            body=body,
            cta=cta or plan.cta,
            image_layout=_gen_image_layout(plan, emap),
        )
    except Exception as exc:
        print(f"[article-engine] generate fallback: {exc}")
        return None


def generate_draft(task: TaskSpec, plan: ContentPlan, emap: EvidenceMap) -> DraftArticle:
    """Generate only evidence-backed values; absent facts remain neutral.

    Prefer article-engine when available; otherwise original template path.
    """
    engine_draft = _try_article_engine(task, plan, emap)
    if engine_draft is not None:
        return engine_draft

    body = _gen_body(task, plan, emap)
    if len(body) < plan.length_min:
        body = _pad_body(body, task, plan, emap)
    if len(body) > plan.length_max and plan.length_max >= plan.length_min:
        tail = "不同销售版本配置可能不同，请以官方规格页及实际销售 SKU 为准。"
        body = body.replace(tail, "").rstrip()
        limit = max(plan.length_min, plan.length_max - len(tail) - 2)
        body = body[:limit].rstrip() + "\n\n" + tail
    while len(body) < plan.length_min:
        body += "\n\n发布前请再次核对当前销售 SKU 的官方资料与渠道信息。"
    return DraftArticle(title=_gen_title(task, plan), lead=_gen_lead(task, plan), body=body, cta=plan.cta, image_layout=_gen_image_layout(plan, emap))
