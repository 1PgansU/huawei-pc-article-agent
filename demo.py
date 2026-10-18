"""
手动 demo 测试（UTF-8 输出）
"""
import io
import sys
import json

# 强制 stdout UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 直接调用 main 流程
from agent.main import main as main_fn
from agent.layers.task_understanding import parse_task
from agent.layers.scenario_strategy import build_content_plan
from agent.layers.ima_retrieval import retrieve_evidence
from agent.layers.article_generation import generate_draft
from agent.layers.verification import verify

# 重写参数
class Args:
    scenario = "school_season"
    product = "HUAWEI MateBook 14 鸿蒙版"
    platform = "xhs"
    query = "大学新生想买轻薄本兼顾学习和续航"

args = Args()

print("=" * 70)
print("  华为PC营销软文智能体 — MVP 演示")
print("=" * 70)
print(f"  场景:   {args.scenario}")
print(f"  产品:   {args.product}")
print(f"  平台:   {args.platform}")
print(f"  需求:   {args.query}")
print()

# 第 1 层
print("[1/6] 任务理解层...")
task_spec = parse_task(args.scenario, args.product, args.platform, args.query)
print(f"  [OK] 任务规格已生成（追问项：{task_spec.missing_info or '无'}）")
if task_spec.missing_info:
    print("  [!] 任务信息不完整，需追问用户：")
    for q in task_spec.missing_info:
        print(f"     - {q}")
    print("  → 演示模式：忽略追问，继续生成\n")

# 第 2 层
print("[2/6] 场景与平台策略层...")
content_plan = build_content_plan(task_spec)
print(f"  [OK] 切角: {content_plan.angle}")
print(f"  [OK] 卖点顺序: {' > '.join(content_plan.highlight_order[:3])}...")
print(f"  [OK] 字数区间: {content_plan.length_min}-{content_plan.length_max}")
print(f"  [OK] 图片数: {content_plan.image_min}-{content_plan.image_max}")
print()

# 第 3 层
print("[3/6] ima 知识库检索 + 事实点提取...")
evidence_map = retrieve_evidence("任德耀新建华为PC知识库", args.product, args.scenario)
print(f"  [OK] 检索到 {len(evidence_map.facts)} 条事实点")
print(f"  [OK] 检索到 {len(evidence_map.images)} 张可用图片")
print()

# 第 4 层
print("[4/6] 图文软文生成层...")
draft = generate_draft(task_spec, content_plan, evidence_map)
print(f"  [OK] 标题: {draft.title[:30]}...")
print(f"  [OK] 配图: {len(draft.image_layout)} 张")
print()

# 第 5 层
print("[5/6] 核验与合规拦截层...")
report = verify(draft, evidence_map, content_plan)
print(f"  事实核验: {'[OK] 通过' if report.fact_check['pass'] else '[X] 失败'}")
print(f"  图片核验: {'[OK] 通过' if report.image_check['pass'] else '[X] 失败'}")
print(f"  合规核验: {'[OK] 通过' if report.compliance_check['pass'] else '[X] 失败'}")
print()

# 第 6 层
print("[6/6] 统一输出格式（赛题要求）")
print("=" * 70)

# 一、场景判断
print("一、场景判断")
print(f"- 目标人群: {task_spec.audience}")
print(f"- 使用场景: {task_spec.scenario}")
print(f"- 用户问题: {task_spec.user_question}")
print(f"- 内容目标: {task_spec.content_goal}")
print(f"- 发布平台: {task_spec.platform}")
print(f"- 切角: {content_plan.angle}")
print()

# 二、知识库依据
print("二、知识库依据")
for f in evidence_map.facts[:5]:
    print(f"- {f['key']}: {f['value']}  [来源: {f['source']}]")
if len(evidence_map.facts) > 5:
    print(f"- ...（共 {len(evidence_map.facts)} 条事实）")
print()

# 三、图文软文
print("三、图文软文")
print(f"标题: {draft.title}")
print(f"导语: {draft.lead}")
print("正文:")
print(draft.body)
print(f"行动引导: {draft.cta}")
print("配图方案:")
for img in draft.image_layout:
    print(f"  - 位置[{img['position']}] {img['image_id']}: {img['caption']}")
print()

# 四、核验结果
print("四、核验结果")
print(f"- 产品事实: {'通过' if report.fact_check['pass'] else '失败'}")
print(f"- 图片型号: {'通过' if report.image_check['pass'] else '失败'}")
print(f"- 合规检查: {'通过' if report.compliance_check['pass'] else '失败'}")
if report.unconfirmed:
    print("- 待确认信息:")
    for u in report.unconfirmed:
        print(f"  · {u}")
print("=" * 70)

if report.overall_pass:
    print("\n[OK] 生成成功！软文已通过核验与合规检查。")
else:
    print("\n[!] 生成完成，但有未通过项，请检查核验报告。")

# 同时写入 UTF-8 文件
with open(r'c:\Users\phobi\Desktop\demo_output.txt', 'w', encoding='utf-8') as f:
    f.write("=" * 70 + "\n")
    f.write("  华为PC营销软文智能体 — MVP 演示\n")
    f.write("=" * 70 + "\n")
    f.write(f"  场景:   {args.scenario}\n")
    f.write(f"  产品:   {args.product}\n")
    f.write(f"  平台:   {args.platform}\n")
    f.write(f"  需求:   {args.query}\n\n")

    f.write("[1/6] 任务理解层...\n")
    f.write(f"  [OK] 任务规格已生成（追问项：{task_spec.missing_info or '无'}）\n")
    if task_spec.missing_info:
        f.write("  [!] 任务信息不完整，需追问用户：\n")
        for q in task_spec.missing_info:
            f.write(f"     - {q}\n")
        f.write("  → 演示模式：忽略追问，继续生成\n\n")

    f.write("[2/6] 场景与平台策略层...\n")
    f.write(f"  [OK] 切角: {content_plan.angle}\n")
    f.write(f"  [OK] 卖点顺序: {' > '.join(content_plan.highlight_order[:3])}...\n")
    f.write(f"  [OK] 字数区间: {content_plan.length_min}-{content_plan.length_max}\n")
    f.write(f"  [OK] 图片数: {content_plan.image_min}-{content_plan.image_max}\n\n")

    f.write("[3/6] ima 知识库检索 + 事实点提取...\n")
    f.write(f"  [OK] 检索到 {len(evidence_map.facts)} 条事实点\n")
    f.write(f"  [OK] 检索到 {len(evidence_map.images)} 张可用图片\n\n")

    f.write("[4/6] 图文软文生成层...\n")
    f.write(f"  [OK] 标题: {draft.title[:30]}...\n")
    f.write(f"  [OK] 配图: {len(draft.image_layout)} 张\n\n")

    f.write("[5/6] 核验与合规拦截层...\n")
    f.write(f"  事实核验: {'[OK] 通过' if report.fact_check['pass'] else '[X] 失败'}\n")
    f.write(f"  图片核验: {'[OK] 通过' if report.image_check['pass'] else '[X] 失败'}\n")
    f.write(f"  合规核验: {'[OK] 通过' if report.compliance_check['pass'] else '[X] 失败'}\n\n")

    f.write("[6/6] 统一输出格式（赛题要求）\n")
    f.write("=" * 70 + "\n")
    f.write("一、场景判断\n")
    f.write(f"- 目标人群: {task_spec.audience}\n")
    f.write(f"- 使用场景: {task_spec.scenario}\n")
    f.write(f"- 用户问题: {task_spec.user_question}\n")
    f.write(f"- 内容目标: {task_spec.content_goal}\n")
    f.write(f"- 发布平台: {task_spec.platform}\n")
    f.write(f"- 切角: {content_plan.angle}\n\n")

    f.write("二、知识库依据\n")
    for fact in evidence_map.facts[:5]:
        f.write(f"- {fact['key']}: {fact['value']}  [来源: {fact['source']}]\n")
    if len(evidence_map.facts) > 5:
        f.write(f"- ...（共 {len(evidence_map.facts)} 条事实）\n")
    f.write("\n")

    f.write("三、图文软文\n")
    f.write(f"标题: {draft.title}\n")
    f.write(f"导语: {draft.lead}\n")
    f.write("正文:\n")
    f.write(draft.body + "\n")
    f.write(f"行动引导: {draft.cta}\n")
    f.write("配图方案:\n")
    for img in draft.image_layout:
        f.write(f"  - 位置[{img['position']}] {img['image_id']}: {img['caption']}\n")
    f.write("\n")

    f.write("四、核验结果\n")
    f.write(f"- 产品事实: {'通过' if report.fact_check['pass'] else '失败'}\n")
    f.write(f"- 图片型号: {'通过' if report.image_check['pass'] else '失败'}\n")
    f.write(f"- 合规检查: {'通过' if report.compliance_check['pass'] else '失败'}\n")
    if report.unconfirmed:
        f.write("- 待确认信息:\n")
        for u in report.unconfirmed:
            f.write(f"  · {u}\n")
    f.write("=" * 70 + "\n")

    if report.overall_pass:
        f.write("\n[OK] 生成成功！软文已通过核验与合规检查。\n")
    else:
        f.write("\n[!] 生成完成，但有未通过项，请检查核验报告。\n")

print(f"\n[INFO] 同时已写入 {r'c:\Users\phobi\Desktop\demo_output.txt'}")