"""
Gradio UI — 对齐现场检查清单
==============================
清单① 账号与知识库：知识库状态页签（名称/连接状态/接口返回/密钥脱敏）
清单② 任务输入：产品/人群/场景/渠道表单 + 信息不足时提示补充
清单③ 知识与图片检索：图片画廊预览 + 来源路径（现场可抽查）
清单④ 场景与平台策略：策略详情页签（可解释 ContentPlan）
清单⑤ 图文软文生成：标题/正文/CTA/图片引用与插入位置
清单⑥ 事实核验 + 清单⑦ 合规检查：核验结果/明细页签
清单⑧ 修改与导出：临时修改输入框 + 重新生成 + 导出 md/txt + 一键复制

运行： python ui/gradio_app.py   （127.0.0.1:7870）
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import gradio as gr

from agent.layers.kb_connection import check_knowledge_base, mask_secret, DEFAULT_KB_NAME
from agent.layers.task_understanding import parse_task
from agent.layers.scenario_strategy import build_content_plan
from agent.layers.ima_retrieval import retrieve_evidence, list_products
from agent.layers.article_generation import generate_draft
from agent.layers.verification import verify
from agent.layers.revision import revise_and_regenerate, export_article


# ─────────────────────────────────────────────
# 主流程状态（会话级）
# ─────────────────────────────────────────────

class SessionState:
    kb_status = None
    task = None
    plan = None
    emap = None
    draft = None
    report = None


S = SessionState()


# ─────────────────────────────────────────────
# 格式化
# ─────────────────────────────────────────────

def _fmt_kb(s) -> str:
    status_emoji = {"connected": "🟢 已连接（ima OpenAPI）",
                    "local_index": "🟡 本地索引模式（离线可用，来源可抽查）",
                    "failed": "🔴 未找到知识库"}.get(s.connection, s.connection)
    lines = [
        "## 清单① 账号与知识库",
        "",
        "| 检查项 | 结果 |",
        "|---|---|",
        f"| 当前账号（脱敏） | `{s.account_id_masked}` |",
        f"| 凭证来源 | {s.credential_source} |",
        f"| 知识库名称 | **{s.kb_name}** |",
        f"| kb_id | `{s.kb_id[:40]}` |",
        f"| 连接状态 | {status_emoji} |",
        "",
        "### 接口返回摘要",
        "```",
        s.api_return[:500],
        "```",
    ]
    if s.local_product_dirs:
        lines.append(f"\n### 本地索引产品目录（共 {len(s.local_product_dirs)} 个，现场更换产品可直接切换）")
        lines.append("、".join(os.path.basename(d) for d in s.local_product_dirs[:16]))
    lines.append("\n> 🔒 密钥保护：Client ID / API Key 仅脱敏展示前 4 位，完整凭证只存在于环境变量中，代码与界面均不出现完整密钥。")
    return "\n".join(lines)


def _fmt_scene(task, plan) -> str:
    miss = chr(10).join(['- ❓ ' + q for q in task.missing_info]) if task.missing_info else '✅ 信息完整'
    return f"""## 清单② 任务输入（解析结果）

| 字段 | 值 |
|---|---|
| 产品型号 | {task.product_hint} |
| 目标人群 | {task.audience} |
| 业务场景 | {task.scenario} |
| 发布渠道 | {task.platform} |
| 购买阶段 | {task.purchase_stage} |
| 内容目标 | {task.content_goal} |
| 用户需求 | {task.user_question} |

### 信息完整性检查（信息不足时提示补充）
{miss}

## 清单④ 场景与平台策略（可解释 ContentPlan）
- **切角**: {plan.angle}
- **卖点优先级**: {' > '.join(plan.highlight_order)}
- **结构节奏**: {' > '.join(plan.structure)}
- **字数区间**: {plan.length_min}-{plan.length_max}｜**图片数**: {plan.image_min}-{plan.image_max}
- **语气**: {plan.tone}
- **行动引导**: {plan.cta}
- **避坑项**: {'；'.join(plan.avoid)}
"""


def _fmt_evidence(emap) -> str:
    lines = [f"## 清单③ 知识与图片检索（模式：`{emap.retrieval_mode}`，共 {len(emap.facts)} 条事实）", ""]
    for i, f in enumerate(emap.facts, 1):
        lines.append(f"{i}. **{f['key']}**: {f['value'][:120]}")
        lines.append(f"   - 📄 来源: `{f['source']}`")
    lines.append(f"\n---\n**可用图片**: {len(emap.images)} 张（来源见画廊页签，现场可抽查）")
    return "\n".join(lines)


def _fmt_article(draft) -> str:
    img_md = "\n".join([f"  - **位置[{img['position']}]** `{img['image_id']}`: {img['caption']}"
                        for img in draft.image_layout])
    return f"""## 清单⑤ 图文软文

### 标题
**{draft.title}**

### 导语
{draft.lead}

### 正文
{draft.body}

### 行动引导
{draft.cta}

### 图片引用与插入位置（共 {len(draft.image_layout)} 张）
{img_md}
"""


def _fmt_verify(report, plan) -> str:
    status = "✅ 全部通过" if report.overall_pass else "⚠️ 存在未通过项"
    return f"""## 清单⑥⑦ 核验结果（事实核验 + 合规检查）

**总评**: {status}

| 项目 | 状态 |
|---|---|
| ⑥ 产品事实核验 | {'✅ 通过' if report.fact_check['pass'] else '❌ 失败'} |
| ⑥ 图片型号核验 | {'✅ 通过' if report.image_check['pass'] else '❌ 失败'} |
| ⑦ 合规检查 | {'✅ 通过' if report.compliance_check['pass'] else '❌ 失败'} |

### 待确认信息
{chr(10).join(['- ' + u for u in report.unconfirmed]) if report.unconfirmed else '无'}

> 字数区间: {plan.length_min}-{plan.length_max}｜合规规则集见 `prompts/verification_rules.md`
"""


def _fmt_verify_detail(report) -> str:
    def block(name, check):
        lines = [f"### {name}"]
        if check.get("issues"):
            lines += [f"- ❌ {i}" for i in check["issues"]]
        else:
            lines.append("- ✅ 全部通过")
        return lines

    lines = ["## 核验明细（逐项检查）"] + block("事实核验", report.fact_check) \
        + block("图片核验", report.image_check) + block("合规核验", report.compliance_check)
    lines.append("""
**合规检查覆盖**：绝对化用语 / 虚假承诺 / 价格误导（无依据数字、补贴）/ 无依据对比 / 竞品贬低 / 虚构体验""")
    return "\n".join(lines)


# ─────────────────────────────────────────────
# 事件：知识库检测
# ─────────────────────────────────────────────

def on_check_kb():
    from agent.env_config import load_env
    load_env(force=True)  # 强制从 .env 重读最新凭证（开发调试用）
    S.kb_status = check_knowledge_base(DEFAULT_KB_NAME)
    return _fmt_kb(S.kb_status)


# ─────────────────────────────────────────────
# 事件：生成
# ─────────────────────────────────────────────

def on_run(scenario_label, product, platform_label, query):
    scenario_id = dict(SCENARIOS)[scenario_label]
    platform_id = dict(PLATFORMS)[platform_label]

    if S.kb_status is None:
        S.kb_status = check_knowledge_base(DEFAULT_KB_NAME)

    S.task = parse_task(scenario_id, product, platform_id, query)
    S.plan = build_content_plan(S.task)
    S.emap = retrieve_evidence(DEFAULT_KB_NAME, product, scenario_id)
    S.draft = generate_draft(S.task, S.plan, S.emap)
    S.report = verify(S.draft, S.emap, S.plan)

    gallery = [(img["path"], img["desc"]) for img in S.emap.images if img.get("path") and os.path.exists(img["path"])]
    gallery_src = "\n".join(f"- `{img['source']}` — {img['desc']}" for img in S.emap.images)

    return (_fmt_scene(S.task, S.plan), _fmt_evidence(S.emap), _fmt_article(S.draft),
            _fmt_verify(S.report, S.plan), _fmt_verify_detail(S.report),
            gallery, gallery_src)


# ─────────────────────────────────────────────
# 事件：修改重生成（清单⑧）
# ─────────────────────────────────────────────

def on_revise(feedback):
    if S.draft is None:
        return ("请先生成一篇软文，再输入临时修改要求。", "", "", "")
    result = revise_and_regenerate(feedback, S.task, S.plan, S.emap)
    S.task, S.plan = result.task, result.plan
    S.draft, S.report = result.draft, result.report

    note_md = f"## 修改说明\n" + "\n".join(f"- {c}" for c in result.changed)
    return (note_md + "\n\n" + _fmt_article(S.draft),
            _fmt_verify(S.report, S.plan),
            _fmt_verify_detail(S.report),
            _fmt_scene(S.task, S.plan))


# ─────────────────────────────────────────────
# 事件：导出（清单⑧）
# ─────────────────────────────────────────────

def on_export():
    if S.draft is None:
        return "", "请先生成软文。"
    paths = export_article(S.task, S.plan, S.emap, S.draft, S.report)
    return paths["markdown"], f"✅ 已导出：\n- {paths['markdown']}\n- {paths['text']}"


def on_copy_text():
    if S.draft is None:
        return ""
    from agent.layers.revision import build_export_text
    return build_export_text(S.task, S.plan, S.draft)


# ─────────────────────────────────────────────
# 界面
# ─────────────────────────────────────────────

SCENARIOS = [
    ("开学季", "school_season"), ("职场办公", "business_office"),
    ("内容创作", "content_creation"), ("家庭换新", "family_refresh"),
    ("企业采购", "enterprise_procurement"), ("门店到访", "store_visit"),
    ("新品首发", "new_launch"), ("节日营销", "holiday"),
]

PLATFORMS = [
    ("小红书", "xhs"), ("公众号", "wechat_mp"), ("朋友圈", "moments"),
    ("门店海报", "poster"), ("新闻稿", "news"), ("知乎", "zhihu"),
    ("短视频", "short_video"), ("直播", "live"),
]


def build_ui():
    with gr.Blocks(title="华为PC营销软文智能体") as demo:
        gr.Markdown("""# 🚀 华为PC营销软文智能体
基于 ima 共享知识库的**自研 Agent**：理解需求 → 检索资料 → 策略决策 → 生成内容 → 事实/合规核验 → 修改导出。
ima 仅作为产品事实与图片来源；业务编排、平台策略与核验拦截全部由自研系统完成。""")

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 📡 知识库连接（清单①）")
                kb_btn = gr.Button("🔌 检测知识库连接", variant="secondary")
                with gr.Accordion("账号与知识库状态", open=True):
                    kb_out = gr.Markdown()

                gr.Markdown("### 📝 任务输入（清单②）")
                scenario_dd = gr.Dropdown([s[0] for s in SCENARIOS], label="业务场景", value=SCENARIOS[0][0])
                product_dd = gr.Dropdown(list_products() or ["HUAWEI MateBook 14 鸿蒙版"],
                                         label="产品型号", allow_custom_value=True,
                                         value="HUAWEI MateBook 14 鸿蒙版")
                platform_dd = gr.Dropdown([p[0] for p in PLATFORMS], label="发布渠道", value=PLATFORMS[0][0])
                query_in = gr.Textbox(label="用户需求", lines=3,
                                      value="大学新生想买轻薄本兼顾学习和续航",
                                      placeholder="不完整也没关系——系统会提示需要补充的信息")
                run_btn = gr.Button("🚀 生成软文", variant="primary", size="lg")

                gr.Markdown("### ✏️ 修改与导出（清单⑧）")
                feedback_in = gr.Textbox(label="临时修改要求",
                                         placeholder="例：换成公众号 / 删减一半 / 突出续航 / 人群改为研究生",
                                         lines=2)
                revise_btn = gr.Button("🔄 按要求重新生成")
                export_btn = gr.Button("💾 导出 Markdown/文本")
                export_info = gr.Markdown()
                copy_btn = gr.Button("📋 生成可复制纯文本")
                copy_out = gr.Textbox(label="最终文本（可复制）", lines=6)

            with gr.Column(scale=2):
                with gr.Tabs():
                    with gr.Tab("任务理解与策略"):
                        scene_out = gr.Markdown()
                    with gr.Tab("知识库依据"):
                        evidence_out = gr.Markdown()
                    with gr.Tab("图文软文"):
                        article_out = gr.Markdown()
                    with gr.Tab("核验结果"):
                        verify_out = gr.Markdown()
                    with gr.Tab("核验明细"):
                        detail_out = gr.Markdown()
                    with gr.Tab("图片画廊（来源可抽查）"):
                        gallery = gr.Gallery(label="ima 知识库图片", columns=3, height=420)
                        gallery_src = gr.Markdown()

        # 事件绑定
        kb_btn.click(on_check_kb, outputs=kb_out)
        run_btn.click(on_run, inputs=[scenario_dd, product_dd, platform_dd, query_in],
                      outputs=[scene_out, evidence_out, article_out, verify_out, detail_out, gallery, gallery_src])
        revise_btn.click(on_revise, inputs=feedback_in,
                         outputs=[article_out, verify_out, detail_out, scene_out])
        export_btn.click(on_export, outputs=[copy_out, export_info])
        copy_btn.click(on_copy_text, outputs=copy_out)

        demo.load(on_check_kb, outputs=kb_out)

    return demo


if __name__ == "__main__":
    demo = build_ui()
    demo.queue().launch(server_name="127.0.0.1", server_port=7870,
                        share=False, show_error=True)
