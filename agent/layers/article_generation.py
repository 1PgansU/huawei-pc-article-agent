"""Evidence-grounded draft generation with neutral text for missing facts.

优先尝试 LLM（合并平台提示词模板）；再试 article-engine；失败则走本文件原模板逻辑。
前端契约不变：仍返回 DraftArticle（可含可选 xhs 旁路字段）。
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

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

# 有专用提示词模板的平台：优先走 LLM + 模板全文
_LLM_TEMPLATE_PLATFORMS = frozenset({"xhs", "moments", "wechat_mp", "小红书", "朋友圈", "公众号"})


@dataclass
class DraftArticle:
    """Structured article draft."""
    title: str
    lead: str
    body: str
    cta: str
    image_layout: List[Dict] = field(default_factory=list)
    # 小红书自动图文旁路（可选；asdict 会进 API，不改路由名）
    xhs_html_path: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


def _fact_values(emap: EvidenceMap) -> Dict[str, str]:
    return {str(f.get("key", "")): str(f.get("value", "")) for f in emap.facts if f.get("value")}


def _gen_title(task: TaskSpec, plan: ContentPlan) -> str:
    if plan.platform == "xhs":
        return f"姐妹们看过来😭｜{task.product_hint}真实上手，这几点别踩坑"
    if plan.platform == "moments":
        return f"🔥 {task.product_hint}｜现货可体验"
    if plan.platform == "wechat_mp":
        return f"{task.audience}选购参考：{task.product_hint}要点梳理"
    return task.product_hint


def _gen_lead(task: TaskSpec, plan: ContentPlan) -> str:
    if plan.platform == "xhs":
        return (
            f"用了几天{task.product_hint}，按{task.scenario}场景实测记录～"
            "下面只写能核对的点，不写没依据的承诺。"
        )
    if plan.platform == "moments":
        return f"✅ {task.product_hint}要点速览｜到店可看实机"
    return (
        f"{plan.angle}。{task.audience}在选购前，应先核对当前在售配置与官方说明，"
        "避免把未证实的参数写进承诺。"
    )


def _neutral_fact(key: str) -> str:
    return f"{key}信息以当前在售 SKU 的官方详情页为准；本文不编造未核实的参数或承诺。"


def _gen_body(task: TaskSpec, plan: ContentPlan, emap: EvidenceMap) -> str:
    facts = _fact_values(emap)
    if plan.platform == "xhs":
        return _body_xhs(task, plan, facts)
    if plan.platform == "moments":
        return _body_moments(task, plan, facts)
    paragraphs = [f"{plan.angle}。下文仅基于可核验参数展开，不把猜测写成事实承诺。"]
    for highlight in plan.highlight_order[:4]:
        value = facts.get(highlight)
        paragraphs.append(f"**{highlight}**：{value if value else _neutral_fact(highlight)}")
    paragraphs.append(
        "不同配置版本参数可能不同，请以官方详情页与实机在售 SKU 为准。"
        "本文不涉及价格、库存、赠品与促销；以发布时官方授权信息为准。"
    )
    return "\n\n".join(paragraphs)


def _body_xhs(task: TaskSpec, plan: ContentPlan, facts: Dict[str, str]) -> str:
    """小红书：种草小节 + emoji 标题 + 话题标签，禁止到店促销体。"""
    bits = [
        f"先说结论：按「{task.audience} / {task.scenario}」来看，{task.product_hint}更像日常种草向笔记，不是销售短帖。",
    ]
    emoji_cycle = ["✨", "📓", "🎒", "📱", "⚠️"]
    for i, highlight in enumerate(plan.highlight_order[:4]):
        value = facts.get(highlight) or _neutral_fact(highlight)
        em = emoji_cycle[i % len(emoji_cycle)]
        bits.append(f"{em} {highlight}｜真实感受\n{value}\n用下来体感比参数表更直观，踩坑点也会单独说。")
    bits.append(
        "避雷提醒｜不同销售版本配置可能不同，请以官方规格页及实机在售 SKU 为准；"
        "不写价格/补贴/库存，也不编绝对化承诺。"
    )
    bits.append(
        "💬 你们同场景都在用什么本？评论区聊聊～\n"
        "📌 建议收藏，选本时对照官方页少踩坑\n"
        f"#学生党笔记本 #{task.product_hint.replace(' ', '')} #真实上手 #避雷指南"
    )
    return "\n\n".join(bits)


def _body_moments(task: TaskSpec, plan: ContentPlan, facts: Dict[str, str]) -> str:
    """朋友圈：短行多次换行 + ✓参数 + 到店/私信 CTA，禁止小红书情绪长文。"""
    lines = [
        f"🔥 {task.product_hint}｜核心卖点速览",
        "",
    ]
    for highlight in plan.highlight_order[:3]:
        value = facts.get(highlight)
        if value:
            lines.append(f"✅ {highlight}：{value}")
        else:
            lines.append(f"✅ {highlight}：以在售 SKU 官方页为准")
    lines.append("")
    lines.append("✓ 配置以官网/门店实机为准")
    lines.append("✓ 到店可上手体验")
    lines.append("✓ 详询可私信预约")
    lines.append("")
    lines.append("欢迎到店咨询，预约体验～")
    lines.append("不同销售版本配置可能不同，请以官方规格页及实际销售 SKU 为准。")
    text = "\n".join(lines)
    # hard trim toward moments length band
    if len(text) > max(plan.length_max, 220):
        text = text[: plan.length_max].rstrip() + "\n…\n不同销售版本配置可能不同，请以官方规格页及实际销售 SKU 为准。"
    return text


def _try_platform_local_draft(task: TaskSpec, plan: ContentPlan, emap: EvidenceMap) -> Optional[DraftArticle]:
    """无 LLM 时：小红书/朋友圈走平台专属骨架，绝不共用 engine 软文报告体。"""
    if plan.platform not in ("xhs", "moments"):
        return None
    title = _gen_title(task, plan)
    lead = _gen_lead(task, plan)
    body = _gen_body(task, plan, emap)
    if len(body) < plan.length_min:
        body = _pad_body(body, task, plan, emap)
    if plan.platform == "moments" and len(body) > plan.length_max and plan.length_max >= 60:
        body = body[: plan.length_max].rstrip()
        if "不同销售版本" not in body:
            body += "\n不同销售版本配置可能不同，请以官方规格页及实际销售 SKU 为准。"
    while plan.platform == "xhs" and len(body) < plan.length_min:
        body += "\n\n再核对一遍官方页参数，比听种草口号靠谱。"
    cta = plan.cta
    if plan.platform == "xhs":
        cta = "💬 评论区聊聊你的使用场景～ 📌 收藏备用"
    elif plan.platform == "moments":
        cta = "详细配置到店咨询，欢迎私信预约体验"
    draft = DraftArticle(
        title=title,
        lead=lead,
        body=body,
        cta=cta,
        image_layout=_gen_image_layout(plan, emap),
    )
    if plan.platform == "xhs":
        draft = _attach_xhs(draft, task, plan)
    meta_platform = plan.platform or task.platform
    return _stamp_fallback_extra(
        draft,
        meta_platform,
        "platform-local",
        "LLM unavailable; used platform-local skeleton (not article-engine soft report)",
    )



def _gen_image_layout(plan: ContentPlan, emap: EvidenceMap) -> List[Dict]:
    selected = emap.images[: min(plan.image_max, len(emap.images))]
    positions = ["开头", "中段", "中段", "文尾", "文尾"]
    return [{"position": positions[i] if i < len(positions) else "中段", "image_id": image["id"], "caption": image.get("desc", "产品图片"), "source": image.get("source", ""), "preview_url": image.get("preview_url", "")} for i, image in enumerate(selected)]


def _pad_body(body: str, task: TaskSpec, plan: ContentPlan, emap: EvidenceMap) -> str:
    """Reach a channel's minimum with useful evidence-review guidance, never new specs."""
    facts = _fact_values(emap)
    topics = list(plan.highlight_order) or ["外观", "使用场景", "综合体验"]
    paragraphs = [
        f"建议将{task.scenario}中的真实使用路径过一遍，再对照产品参数与当前在售 SKU。",
        "核对时应区分系统参数与用途描述；型号规格未在证据源中出现时，不应写成结论。",
        "若同一产品存在多个配置版本，应分别记录处理器、内存、存储与屏幕等差异，并以官方详情页为准。",
        "续航、散热等体验类表述受使用模式与版本影响较大，发布前应回到证据源复核，避免把体验写成硬参数。",
        "正文应围绕目标人群与内容目标展开，同时保留可核对的核验路径，方便门店与客服引用。",
    ]
    index = 0
    max_iterations = max(len(paragraphs) * 20, 100)
    while len(body) < plan.length_min and index < max_iterations:
        topic = topics[index % len(topics)]
        value_hint = facts.get(topic)
        extra = paragraphs[index % len(paragraphs)]
        if value_hint and index % 2 == 0:
            extra += f"当前证据中的{topic}相关为：{value_hint}"
        body += "\n\n" + extra
        index += 1
    return body


def _parse_llm_markdown(text: str) -> Optional[Dict[str, str]]:
    """Parse LLM markdown (# title / > lead / ## body / ## CTA) into parts."""
    if not text or not text.strip():
        return None
    raw = text.strip()
    title = ""
    lead = ""
    body = ""
    cta = ""

    m_title = re.search(r"^#\s+(.+)$", raw, re.MULTILINE)
    if m_title:
        title = m_title.group(1).strip()

    m_lead = re.search(r"^>\s*(.+)$", raw, re.MULTILINE)
    if m_lead:
        lead = m_lead.group(1).strip()

    # Split by ## headings
    sections = re.split(r"^##\s+", raw, flags=re.MULTILINE)
    for sec in sections[1:]:
        lines = sec.strip().splitlines()
        if not lines:
            continue
        head = lines[0].strip()
        content = "\n".join(lines[1:]).strip()
        if any(k in head for k in ("行动", "CTA", "引导", "号召")):
            cta = content
        elif any(k in head for k in ("正文", "内容", "文案", "正文内容")):
            body = content
        elif not body:
            body = content

    if not body:
        # fallback: strip title/lead lines, take the rest
        cleaned = re.sub(r"^#\s+.+$", "", raw, flags=re.MULTILINE)
        cleaned = re.sub(r"^>\s*.+$", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"^##\s*.+$", "", cleaned, flags=re.MULTILINE)
        body = cleaned.strip()

    if not title:
        first = raw.splitlines()[0].strip().lstrip("#").strip()
        title = first[:80] if first else ""

    if not title or not body:
        return None
    return {"title": title, "lead": lead, "body": body, "cta": cta}


def _task_as_dict(task: TaskSpec) -> Dict[str, Any]:
    try:
        return asdict(task)
    except Exception:
        return {
            "product_hint": task.product_hint,
            "audience": task.audience,
            "scenario": task.scenario,
            "platform": task.platform,
            "purchase_stage": getattr(task, "purchase_stage", ""),
            "user_question": getattr(task, "user_question", ""),
            "content_goal": task.content_goal,
        }


def _plan_as_dict(plan: ContentPlan) -> Dict[str, Any]:
    try:
        return asdict(plan)
    except Exception:
        return {
            "platform": plan.platform,
            "angle": plan.angle,
            "highlight_order": list(plan.highlight_order),
            "length_min": plan.length_min,
            "length_max": plan.length_max,
            "image_min": plan.image_min,
            "image_max": plan.image_max,
            "cta": plan.cta,
        }


def _emap_as_dict(emap: EvidenceMap) -> Dict[str, Any]:
    try:
        return asdict(emap)
    except Exception:
        return {"facts": list(emap.facts), "images": list(emap.images), "retrieval_mode": emap.retrieval_mode}


def _platform_meta(platform: str) -> Dict[str, Any]:
    """Resolve platform template path for debug/API extra (does not call LLM)."""
    try:
        from agent.llm_client import resolve_platform_template_path, load_platform_template
    except Exception:
        try:
            from ..llm_client import resolve_platform_template_path, load_platform_template  # type: ignore
        except Exception as exc:
            return {
                "platform": platform,
                "platform_template": "",
                "platform_template_chars": 0,
                "platform_template_resolve_error": str(exc),
            }
    path = resolve_platform_template_path(platform)
    tpl = load_platform_template(platform) if path else ""
    return {
        "platform": platform,
        "platform_template": str(path) if path else "",
        "platform_template_name": path.name if path else "",
        "platform_template_chars": len(tpl),
    }


def _try_llm_draft(task: TaskSpec, plan: ContentPlan, emap: EvidenceMap):
    """LLM + 平台提示词模板。

    Returns (DraftArticle|None, skip_reason:str).
    skip_reason 非空表示未走 LLM（供 extra / 日志）。
    """
    if os.getenv("USE_LLM_GENERATION", "1") in ("0", "false", "False"):
        return None, "USE_LLM_GENERATION=0"
    try:
        from agent.llm_client import (
            check_llm_config,
            generate_article_with_llm,
            resolve_platform_template_path,
            build_system_prompt_for_platform,
        )
    except Exception:
        try:
            from ..llm_client import (  # type: ignore
                check_llm_config,
                generate_article_with_llm,
                resolve_platform_template_path,
                build_system_prompt_for_platform,
            )
        except Exception as exc:
            print(f"[llm] import skipped: {exc}")
            return None, f"import_failed:{exc}"

    cfg = check_llm_config()
    if not cfg.get("llm_configured"):
        reason = "LLM_API_KEY empty (set in .env to use platform md templates)"
        print(f"[llm] skip: {reason}")
        return None, reason

    platform = plan.platform or task.platform
    tpl_path = resolve_platform_template_path(platform)
    system_prompt = build_system_prompt_for_platform(platform)
    if not system_prompt.strip():
        return None, "system_prompt_empty"

    try:
        print(
            f"[llm] calling model; platform={platform}; "
            f"template={tpl_path.name if tpl_path else '(none)'}; "
            f"system_prompt_chars={len(system_prompt)}"
        )
        md = generate_article_with_llm(
            _task_as_dict(task),
            _plan_as_dict(plan),
            _emap_as_dict(emap),
            system_prompt=system_prompt,
        )
        if not md:
            return None, "llm_returned_empty"
        parts = _parse_llm_markdown(md)
        if not parts:
            print("[llm] parse failed; fallback")
            return None, "llm_parse_failed"
        body = parts["body"]
        if len(body) < plan.length_min:
            body = _pad_body(body, task, plan, emap)
        if len(body) > plan.length_max and plan.length_max >= plan.length_min:
            tail = "不同配置版本参数可能不同，请以官方详情页与实机在售 SKU 为准。"
            body = body.replace(tail, "").rstrip()
            limit = max(plan.length_min, plan.length_max - len(tail) - 2)
            body = body[:limit].rstrip() + "\n\n" + tail
        while len(body) < plan.length_min:
            body += "\n\n发布前请再次核对当前在售 SKU 的官方说明与参数信息。"
        meta = _platform_meta(platform)
        draft = DraftArticle(
            title=parts["title"],
            lead=parts["lead"] or _gen_lead(task, plan),
            body=body,
            cta=parts["cta"] or plan.cta,
            image_layout=_gen_image_layout(plan, emap),
            extra={
                **meta,
                "generation": "llm",
                "used_platform_template": bool(tpl_path),
                "llm_skip_reason": "",
                "system_prompt_chars": len(system_prompt),
            },
        )
        if plan.platform == "xhs":
            draft = _attach_xhs(draft, task, plan)
        return draft, ""
    except Exception as exc:  # noqa: BLE001
        print(f"[llm] generate fallback: {exc}")
        return None, f"llm_exception:{exc}"


def _stamp_fallback_extra(draft: DraftArticle, platform: str, generation: str, llm_skip_reason: str) -> DraftArticle:
    """Ensure engine/local drafts declare that platform md templates were NOT injected."""
    meta = _platform_meta(platform)
    note = (
        "platform md template is only injected on the LLM path; "
        "this draft used " + generation + " (does not read prompts/templates/*.md as LLM system prompt)"
    )
    draft.extra = {
        **(draft.extra or {}),
        **meta,
        "generation": generation,
        "used_platform_template": False,
        "llm_skip_reason": llm_skip_reason or "unknown",
        "template_injection_note": note,
    }
    print(
        f"[gen] fallback={generation}; used_platform_template=false; "
        f"reason={llm_skip_reason}; resolved_tpl={meta.get('platform_template_name') or '(none)'}"
    )
    return draft


def _attach_xhs(draft: DraftArticle, task: TaskSpec, plan: ContentPlan) -> DraftArticle:
    """平台为小红书时尝试自动图文 HTML；失败不影响主草稿。"""
    if plan.platform != "xhs":
        return draft
    if os.getenv("USE_ARTICLE_ENGINE", "1") in ("0", "false", "False"):
        return draft
    if not _ENGINE_DIR.is_dir():
        return draft
    try:
        eng = str(_ENGINE_DIR)
        if eng not in sys.path:
            sys.path.insert(0, eng)
        from bridge import generate_xhs_html  # type: ignore

        style = "颜值种草"
        blob = f"{task.scenario} {task.audience} {task.content_goal}"
        if any(k in blob for k in ("学生", "开学", "校园", "school")):
            style = "学生党"
        elif any(k in blob for k in ("性能", "创作", "content_creation", "Pro")):
            style = "性能实测"
        elif any(k in blob for k in ("职场", "办公", "商务", "企业", "business")):
            style = "职场办公"

        xhs = generate_xhs_html(
            product_name=task.product_hint,
            style=style,
            target_audience=task.audience or "学生党",
        )
        draft.xhs_html_path = str(xhs.get("html_path") or "")
        draft.extra = {**(draft.extra or {}), "xhs": xhs}
    except Exception as exc:  # noqa: BLE001
        print(f"[article-engine] xhs auto html skipped: {exc}")
        draft.extra = {**(draft.extra or {}), "xhs_error": str(exc)}
    return draft


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
            if not result or not result.get("article"):
                return None
        art = result.get("article") or {}
        title = (art.get("selected_title") or result.get("title") or "").strip()
        opening = (art.get("opening") or "").strip()
        body = (art.get("body") or "").strip()
        cta = (art.get("cta") or plan.cta or "").strip()
        if not title or not body:
            return None
        if len(body) < plan.length_min:
            body = _pad_body(body, task, plan, emap)
        if len(body) > plan.length_max and plan.length_max >= plan.length_min:
            tail = "不同配置版本参数可能不同，请以官方详情页与实机在售 SKU 为准。"
            body = body.replace(tail, "").rstrip()
            limit = max(plan.length_min, plan.length_max - len(tail) - 2)
            body = body[:limit].rstrip() + "\n\n" + tail
        while len(body) < plan.length_min:
            body += "\n\n发布前请再次核对当前在售 SKU 的官方说明与参数信息。"
        lead = opening or _gen_lead(task, plan)
        draft = DraftArticle(
            title=title,
            lead=lead,
            body=body,
            cta=cta or plan.cta,
            image_layout=_gen_image_layout(plan, emap),
            xhs_html_path=str(result.get("xhs_html_path") or ""),
            extra=dict(result.get("extra") or {}),
        )
        # 若 bridge 未附上 xhs（例如 platform 映射异常），layer 再补一次
        if plan.platform == "xhs" and not draft.xhs_html_path:
            draft = _attach_xhs(draft, task, plan)
        return draft
    except Exception as exc:
        print(f"[article-engine] generate fallback: {exc}")
        return None


def generate_draft(task: TaskSpec, plan: ContentPlan, emap: EvidenceMap) -> DraftArticle:
    """Order: LLM+平台md → 平台本地骨架(xhs/moments) → article-engine → 通用本地。

    小红书/朋友圈在无 LLM 时也绝不共用同一篇软文报告骨架。
    """
    platform = plan.platform or task.platform

    llm_draft, llm_skip = _try_llm_draft(task, plan, emap)
    if llm_draft is not None:
        return llm_draft

    # 关键：xhs/moments 优先平台本地分叉，避免 engine 软文两平台长得一样
    plat_local = _try_platform_local_draft(task, plan, emap)
    if plat_local is not None:
        # keep llm_skip_reason from LLM attempt
        plat_local.extra = {
            **(plat_local.extra or {}),
            "llm_skip_reason": llm_skip or (plat_local.extra or {}).get("llm_skip_reason") or "",
        }
        return plat_local

    engine_draft = _try_article_engine(task, plan, emap)
    if engine_draft is not None:
        return _stamp_fallback_extra(engine_draft, platform, "article-engine", llm_skip)

    body = _gen_body(task, plan, emap)
    if len(body) < plan.length_min:
        body = _pad_body(body, task, plan, emap)
    if len(body) > plan.length_max and plan.length_max >= plan.length_min:
        tail = "不同配置版本参数可能不同，请以官方详情页与实机在售 SKU 为准。"
        body = body.replace(tail, "").rstrip()
        limit = max(plan.length_min, plan.length_max - len(tail) - 2)
        body = body[:limit].rstrip() + "\n\n" + tail
    while len(body) < plan.length_min:
        body += "\n\n发布前请再次核对当前在售 SKU 的官方说明与参数信息。"
    draft = DraftArticle(
        title=_gen_title(task, plan),
        lead=_gen_lead(task, plan),
        body=body,
        cta=plan.cta,
        image_layout=_gen_image_layout(plan, emap),
    )
    draft = _attach_xhs(draft, task, plan)
    return _stamp_fallback_extra(draft, platform, "local-template", llm_skip)
