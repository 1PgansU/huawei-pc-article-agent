"""
AI+华为PC营销软文智能体 — MVP 入口
====================================
7 层架构的最小可运行版本（CLI 演示用）。

运行：
    python -m agent.main --scenario school_season --product "HUAWEI MateBook 14" \
        --platform xhs --query "大学新生想买轻薄本兼顾学习和续航"

环境变量：
    IMA_OPENAPI_CLIENTID、IMA_OPENAPI_APIKEY（由 ima 客户端 Claw 配置获取）
    LLM_API_KEY（如使用真实大模型；未设置时进入 mock 模式）

设计原则：
    - ima 仅作产品事实和图片来源
    - 自研Agent做业务编排与核验拦截
    - 所有事实/图片/合规核验在交付前完成
"""
import argparse
import json
import os
from dataclasses import asdict

from .layers.task_understanding import parse_task, TaskSpec
from .layers.scenario_strategy import build_content_plan, ContentPlan
from .layers.ima_retrieval import retrieve_evidence, EvidenceMap
from .layers.article_generation import generate_draft, DraftArticle
from .layers.verification import verify, VerificationReport


def main():
    parser = argparse.ArgumentParser(description="华为PC营销软文智能体 MVP")
    parser.add_argument("--scenario", required=True,
                        choices=["school_season", "business_office", "content_creation",
                                 "family_refresh", "enterprise_procurement", "store_visit",
                                 "new_launch", "holiday"])
    parser.add_argument("--product", required=True, help="目标产品，如 'HUAWEI MateBook 14 鸿蒙版'")
    parser.add_argument("--platform", required=True,
                        choices=["wechat_mp", "xhs", "moments", "poster",
                                 "news", "zhihu", "short_video", "live"])
    parser.add_argument("--query", required=True, help="用户原始需求")
    args = parser.parse_args()

    print("=" * 70)
    print("  华为PC营销软文智能体 — MVP 演示")
    print("=" * 70)
    print(f"  场景:   {args.scenario}")
    print(f"  产品:   {args.product}")
    print(f"  平台:   {args.platform}")
    print(f"  需求:   {args.query}")
    print()

    # ─── 第 1 层：任务理解 ───
    print("[1/6] 任务理解层...")
    task_spec: TaskSpec = parse_task(
        scenario=args.scenario,
        product=args.product,
        platform=args.platform,
        query=args.query,
    )
    print(f"  [OK] 任务规格已生成（追问项：{task_spec.missing_info or '无'}）")
    if task_spec.missing_info:
        print("  [!] 任务信息不完整，需追问用户：")
        for q in task_spec.missing_info:
            print(f"     - {q}")
        # 演示用：若信息不完整，仍然继续（生产环境应阻塞）
        print("  → 演示模式：忽略追问，继续生成\n")
    else:
        print()

    # ─── 第 2 层：场景与平台策略 ───
    print("[2/6] 场景与平台策略层...")
    content_plan: ContentPlan = build_content_plan(task_spec)
    print(f"  [OK] 切角: {content_plan.angle}")
    print(f"  [OK] 卖点顺序: {' > '.join(content_plan.highlight_order[:3])}...")
    print(f"  [OK] 字数区间: {content_plan.length_min}-{content_plan.length_max}")
    print(f"  [OK] 图片数: {content_plan.image_min}-{content_plan.image_max}")
    print()

    # ─── 第 3 层：ima 检索 + 第 4 层：事实点提取 ───
    print("[3/6] ima 知识库检索 + 事实点提取...")
    evidence_map: EvidenceMap = retrieve_evidence(
        kb_name="任德耀新建华为PC知识库",
        product=args.product,
        scenario=args.scenario,
    )
    print(f"  [OK] 检索到 {len(evidence_map.facts)} 条事实点")
    print(f"  [OK] 检索到 {len(evidence_map.images)} 张可用图片")
    print()

    # ─── 第 5 层：图文软文生成 ───
    print("[4/6] 图文软文生成层...")
    draft: DraftArticle = generate_draft(task_spec, content_plan, evidence_map)
    print(f"  [OK] 标题: {draft.title[:30]}...")
    print(f"  [OK] 配图: {len(draft.image_layout)} 张")
    print()

    # ─── 第 6 层：核验与合规拦截 ───
    print("[5/6] 核验与合规拦截层...")
    report: VerificationReport = verify(draft, evidence_map, content_plan)
    print(f"  事实核验: {'[OK] 通过' if report.fact_check['pass'] else '[X] 失败'}")
    print(f"  图片核验: {'[OK] 通过' if report.image_check['pass'] else '[X] 失败'}")
    print(f"  合规核验: {'[OK] 通过' if report.compliance_check['pass'] else '[X] 失败'}")
    if report.unconfirmed:
        print(f"  待确认项: {len(report.unconfirmed)}")
    print()

    # ─── 输出 ───
    print("[6/6] 统一输出格式（赛题要求）")
    print("=" * 70)
    print(format_output(task_spec, content_plan, evidence_map, draft, report))
    print("=" * 70)

    if report.overall_pass:
        print("\n[OK] 生成成功！软文已通过核验与合规检查。")
    else:
        print("\n[!] 生成完成，但有未通过项，请检查核验报告。")


def format_output(task: TaskSpec, plan: ContentPlan,
                  emap: EvidenceMap, draft: DraftArticle,
                  report: VerificationReport) -> str:
    """赛题统一输出格式：场景判断 / 知识库依据 / 图文软文 / 核验结果"""
    lines = []

    # 一、场景判断
    lines.append("一、场景判断")
    lines.append(f"- 目标人群: {task.audience}")
    lines.append(f"- 使用场景: {task.scenario}")
    lines.append(f"- 用户问题: {task.user_question}")
    lines.append(f"- 内容目标: {task.content_goal}")
    lines.append(f"- 发布平台: {task.platform}")
    lines.append(f"- 切角: {plan.angle}")
    lines.append("")

    # 二、知识库依据
    lines.append("二、知识库依据")
    for f in emap.facts[:5]:
        lines.append(f"- {f['key']}: {f['value']}  [来源: {f['source']}]")
    if len(emap.facts) > 5:
        lines.append(f"- ...（共 {len(emap.facts)} 条事实）")
    lines.append("")

    # 三、图文软文
    lines.append("三、图文软文")
    lines.append(f"标题: {draft.title}")
    lines.append(f"导语: {draft.lead}")
    lines.append("正文:")
    lines.append(draft.body)
    lines.append(f"行动引导: {draft.cta}")
    lines.append("配图方案:")
    for img in draft.image_layout:
        lines.append(f"  - 位置[{img['position']}] {img['image_id']}: {img['caption']}")
    lines.append("")

    # 四、核验结果
    lines.append("四、核验结果")
    lines.append(f"- 产品事实: {'通过' if report.fact_check['pass'] else '失败'}")
    lines.append(f"- 图片型号: {'通过' if report.image_check['pass'] else '失败'}")
    lines.append(f"- 合规检查: {'通过' if report.compliance_check['pass'] else '失败'}")
    if report.unconfirmed:
        lines.append("- 待确认信息:")
        for u in report.unconfirmed:
            lines.append(f"  · {u}")
    return "\n".join(lines)


if __name__ == "__main__":
    main()