"""
第 2 层：场景与平台策略
========================
根据 (scenario, platform) 输出 ContentPlan。
ContentPlan 完全由配置文件驱动（scenario_platform_strategy.yaml），
而非由 LLM 自由生成，确保平台/场景变化带来内容实质变化。
"""
import os
import yaml
from dataclasses import dataclass, field
from typing import List

from .task_understanding import TaskSpec


@dataclass
class ContentPlan:
    """内容策略"""
    scenario_id: str
    platform: str
    angle: str
    highlight_order: List[str]
    structure: List[str]
    length_min: int
    length_max: int
    image_min: int
    image_max: int
    tone: str
    cta: str
    avoid: List[str]


_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..", "prompts", "scenario_platform_strategy.yaml"
)


def _load_config() -> dict:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_content_plan(task: TaskSpec) -> ContentPlan:
    """
    根据 task 构造 ContentPlan。
    流程：
      1. 加载策略表
      2. 取场景策略 → 切角、卖点、避坑
      3. 取平台策略 → 结构、字数、图片数
      4. 拼接语气 = 场景语气 ⊕ 平台语气
      5. 取 CTA = 场景模板[平台]
    """
    cfg = _load_config()

    scenarios = cfg["scenario_profiles"]
    platforms = cfg["platform_profiles"]

    if task.scenario not in scenarios:
        raise ValueError(f"未知场景: {task.scenario}")
    if task.platform not in platforms:
        raise ValueError(f"未知平台: {task.platform}")

    s = scenarios[task.scenario]
    p = platforms[task.platform]

    # 取 CTA 模板
    cta = s.get("default_cta_templates", {}).get(
        task.platform,
        p["cta_style"]
    )

    # 构造 angle：场景 angle + 受众修饰
    angle = s["default_angle"]
    if task.audience:
        angle = f"{angle}（针对{task.audience}）"

    return ContentPlan(
        scenario_id=task.scenario,
        platform=task.platform,
        angle=angle,
        highlight_order=s["priority_highlights"][:5],
        structure=p["structure"],
        length_min=p["length_min"],
        length_max=p["length_max"],
        image_min=p["image_min"],
        image_max=p["image_max"],
        tone=f"{p['tone']} + {s['emotional_tone']}",
        cta=cta,
        avoid=s["avoid"],
    )