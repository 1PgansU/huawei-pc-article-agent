"""
第 1 层：任务理解
=================
解析用户输入，输出结构化 TaskSpec。
当信息不足时，返回 missing_info 列表，提示用户追问。
"""
from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class TaskSpec:
    """任务规格"""
    product_hint: str           # 产品提示，如 "HUAWEI MateBook 14"
    audience: str               # 目标人群
    scenario: str               # 使用场景
    platform: str               # 发布平台
    purchase_stage: str         # 购买阶段
    user_question: str          # 用户问题
    content_goal: str           # 内容目标
    missing_info: List[str] = field(default_factory=list)  # 待追问项


# 追问规则：哪些场景下必须追问
SCENARIO_MISSING_RULES: Dict[str, List[str]] = {
    "school_season": [
        "请确认年级：本科新生 / 研究生 / 高中生？",
        "主要使用场景：上课记笔记 / 编程开发 / 设计作业 / 网课？",
        "是否需要与手机/平板协同？",
    ],
    "business_office": [
        "请确认职业：商务人士 / 自由职业 / 学生？",
        "是否经常出差？频率？",
        "主要软件：Office / WPS / 专业软件？",
    ],
    "content_creation": [
        "创作类型：摄影 / 设计 / 视频 / 音乐？",
        "主要软件：Pr / PS / LR / DaVinci？",
        "素材来源：相机 / 手机 / 其他？",
    ],
}


def parse_task(scenario: str, product: str, platform: str, query: str) -> TaskSpec:
    """
    解析任务输入。
    MVP 版本：从 query 中用关键词识别受众/目标，缺失则触发追问。
    """
    task = TaskSpec(
        product_hint=product,
        audience="",     # 留空，等待追问或推断
        scenario=scenario,
        platform=platform,
        purchase_stage="信息收集",  # 默认
        user_question=query,
        content_goal="种草",
    )

    # 根据 scenario 推断 audience
    scenario_to_audience = {
        "school_season": "大学新生及家长",
        "business_office": "商务/移动办公人士",
        "content_creation": "设计/摄影/视频创作者",
        "family_refresh": "家庭用机/旧机换新者",
        "enterprise_procurement": "中小企业采购方",
        "store_visit": "门店附近潜在顾客",
        "new_launch": "关注新品的用户",
        "holiday": "送礼/家庭购机用户",
    }
    task.audience = scenario_to_audience.get(scenario, "通用用户")

    # MVP：演示模式不阻断，但提示 missing_info
    if scenario in SCENARIO_MISSING_RULES:
        # 简单启发式：query 中如果包含"我""想"等代词，认为需要追问
        if any(k in query for k in ["想买", "推荐", "怎么选", "合适"]):
            task.missing_info = SCENARIO_MISSING_RULES[scenario][:2]

    return task