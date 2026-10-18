"""
清单⑧ 修改与导出
==================
现场检查项：根据临时要求重新生成；支持复制或导出最终文本。

- 修改解析：从用户临时要求中识别 换渠道 / 删减 / 换卖点 / 换人群 / 加长
- 重生成：换平台 → 重建 ContentPlan；其余 → 在原 TaskSpec/Plan 上打修订标记后重走 生成→核验
- 导出：Markdown / 纯文本（含核验结论与配图方案）
"""
import os
import re
from dataclasses import dataclass
from typing import Optional, List, Dict

from .task_understanding import TaskSpec
from .scenario_strategy import build_content_plan, ContentPlan
from .ima_retrieval import EvidenceMap
from .article_generation import generate_draft, DraftArticle
from .verification import verify, VerificationReport

PLATFORM_ALIASES: Dict[str, str] = {
    "公众号": "wechat_mp", "微信": "wechat_mp", "weixin": "wechat_mp",
    "小红书": "xhs", "xhs": "xhs", "红书": "xhs",
    "朋友圈": "moments", "moment": "moments",
    "海报": "poster", "门店": "poster",
    "新闻稿": "news", "新闻": "news",
    "知乎": "zhihu",
    "短视频": "short_video", "抖音": "short_video",
    "直播": "live",
}


@dataclass
class RevisionResult:
    """一次修改重生成的完整结果"""
    revision_note: str            # 解析出的修改说明
    changed: List[str]            # 实际生效的修改项
    task: TaskSpec
    plan: ContentPlan
    draft: DraftArticle
    report: VerificationReport


def parse_feedback(feedback: str, current_task: TaskSpec, current_plan: ContentPlan) -> Dict:
    """
    解析临时修改要求 → 修订指令。
    支持：换渠道（平台）、删减/精简、加长、换卖点/突出XX、换人群。
    """
    text = feedback.strip()
    instructions = {"platform": None, "shorten": False, "lengthen": False,
                    "highlight": None, "audience": None, "raw": text}

    if not text:
        return instructions

    # 换渠道
    for alias, pid in PLATFORM_ALIASES.items():
        if alias in text.lower() and pid != current_plan.platform:
            # "换/改/发/投 到/上 XX" 或直接提到新平台名
            instructions["platform"] = pid
            break

    # 删减 / 加长
    if re.search(r"删减|精简|缩短|太长|减半|简短|去一半", text):
        instructions["shorten"] = True
    if re.search(r"加长|扩充|展开|更详细|字数多", text):
        instructions["lengthen"] = True

    # 换卖点：'突出/重点讲/主打 XX'
    m = re.search(r"(?:突出|重点讲|重点写|主打|换个卖点.{0,4}|聚焦)\s*[:：,，]?\s*([\u4e00-\u9fffa-zA-Z0-9]{2,8})", text)
    if m:
        instructions["highlight"] = m.group(1)

    # 换人群
    m = re.search(r"(?:人群|受众)改为?\s*([\u4e00-\u9fff]{2,10})", text)
    if m:
        instructions["audience"] = m.group(1)

    return instructions


def revise_and_regenerate(feedback: str, task: TaskSpec, plan: ContentPlan,
                          emap: EvidenceMap) -> RevisionResult:
    """
    根据临时要求重新生成（现场检查项）。
    换平台 → 重建 ContentPlan；删减/加长 → 调整字数区间；换卖点 → 调整卖点优先级。
    之后重新走 生成 → 核验。
    """
    ins = parse_feedback(feedback, task, plan)
    changed = []

    new_task = task
    new_plan = plan

    # 1) 换平台 → 重建策略
    if ins["platform"]:
        new_task = TaskSpec(
            product_hint=task.product_hint, audience=task.audience,
            scenario=task.scenario, platform=ins["platform"],
            purchase_stage=task.purchase_stage, user_question=task.user_question,
            content_goal=task.content_goal, missing_info=task.missing_info,
        )
        new_plan = build_content_plan(new_task)
        changed.append(f"发布渠道 → {ins['platform']}（结构/语气/字数/图片数已按新平台策略重建）")

    # 2) 删减 / 加长
    if ins["shorten"] or ins["lengthen"]:
        lo, hi = new_plan.length_min, new_plan.length_max
        if ins["shorten"]:
            new_plan.length_min, new_plan.length_max = max(60, lo // 2), max(200, hi // 2)
            changed.append(f"删减（字数区间 {new_plan.length_min}-{new_plan.length_max}）")
        else:
            new_plan.length_min, new_plan.length_max = lo * 2, hi * 2
            changed.append(f"加长（字数区间 {new_plan.length_min}-{new_plan.length_max}）")

    # 3) 换卖点 → 提到卖点优先级首位
    if ins["highlight"]:
        h = ins["highlight"]
        order = list(new_plan.highlight_order)
        order = [h] + [x for x in order if h not in x]
        new_plan.highlight_order = order
        new_plan.angle = f"以「{h}」为核心卖点" + new_plan.angle.split("，", 1)[-1]
        changed.append(f"核心卖点 → {h}")

    # 4) 换人群
    if ins["audience"]:
        new_task.audience = ins["audience"]
        changed.append(f"目标人群 → {ins['audience']}")

    if not changed:
        changed.append("未识别到明确修改项，已按原要求重新生成")

    # 重新走 生成 → 核验
    draft = generate_draft(new_task, new_plan, emap)
    report = verify(draft, emap, new_plan)

    note = "；".join(changed)
    return RevisionResult(revision_note=note, changed=changed,
                          task=new_task, plan=new_plan, draft=draft, report=report)


# ─────────────────────────────────────────────
# 导出
# ─────────────────────────────────────────────

def _required_tail() -> str:
    return "不同销售版本配置可能不同，请以官方规格页及实际销售 SKU 为准。"


def build_export_markdown(task: TaskSpec, plan: ContentPlan, emap: EvidenceMap,
                          draft: DraftArticle, report: VerificationReport) -> str:
    """导出 Markdown：软文正文 + 配图方案 + 来源记录 + 核验结论"""
    lines = []
    lines.append(f"# {draft.title}")
    lines.append("")
    lines.append(draft.lead)
    lines.append("")
    lines.append(draft.body)
    lines.append("")
    lines.append(f"**{draft.cta}**")
    lines.append("")
    lines.append("## 配图方案")
    for img in draft.image_layout:
        src = img.get("source", "")
        lines.append(f"- 位置[{img['position']}] `{img['image_id']}`：{img['caption']}（来源：{src}）")
    lines.append("")
    lines.append("## 来源记录（现场可抽查）")
    for f in emap.facts[:10]:
        lines.append(f"- {f['key']}：{f['value'][:60]}… — {f['source']}")
    lines.append("")
    lines.append("## 核验结论")
    lines.append(f"- 产品事实：{'✅ 通过' if report.fact_check['pass'] else '❌ 未通过'}")
    lines.append(f"- 图片型号：{'✅ 通过' if report.image_check['pass'] else '❌ 未通过'}")
    lines.append(f"- 合规检查：{'✅ 通过' if report.compliance_check['pass'] else '❌ 未通过'}")
    if report.unconfirmed:
        lines.append("- 待确认：" + "；".join(report.unconfirmed))
    lines.append("")
    lines.append(f"> 发布平台：{plan.platform}｜目标人群：{task.audience}｜{_required_tail()}")
    return "\n".join(lines)


def build_export_text(task: TaskSpec, plan: ContentPlan,
                      draft: DraftArticle) -> str:
    """导出纯文本（可直接复制发布）"""
    lines = [draft.title, "", draft.lead, "", draft.body, "", draft.cta, ""]
    lines.append("配图：" + "；".join(
        f"{i+1}.[{img['position']}]{img['image_id']}({img['caption']})"
        for i, img in enumerate(draft.image_layout)))
    lines.append("")
    lines.append(_required_tail())
    return "\n".join(lines)


def export_article(task: TaskSpec, plan: ContentPlan, emap: EvidenceMap,
                   draft: DraftArticle, report: VerificationReport,
                   out_dir: Optional[str] = None) -> Dict[str, str]:
    """导出 md + txt 两个文件，返回 {格式: 路径}"""
    if out_dir is None:
        out_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "exports")
    os.makedirs(out_dir, exist_ok=True)

    safe_title = re.sub(r"[\\/:*?\"<>|]", "_", draft.title)[:40] or "article"
    md_path = os.path.join(out_dir, f"{safe_title}.md")
    txt_path = os.path.join(out_dir, f"{safe_title}.txt")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(build_export_markdown(task, plan, emap, draft, report))
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(build_export_text(task, plan, draft))

    return {"markdown": md_path, "text": txt_path}
