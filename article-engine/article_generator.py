"""
软文生成器 - 生成标题、正文、配图方案
"""
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from knowledge_retriever import KnowledgeRetriever


@dataclass
class TitleOption:
    """标题选项"""
    title: str
    style: str  # 疑问式、陈述式、利益式、场景式
    reason: str  # 选择理由


@dataclass
class ImagePlan:
    """配图方案"""
    filename: str
    source: str  # ima知识库路径
    position: str  # 插入位置
    purpose: str  # 画面用途
    caption: str  # 图注
    limitation: str = ""  # 限制说明


@dataclass
class ArticleContent:
    """文章内容"""
    platform: str  # 平台
    scenario: str  # 场景
    target_audience: str  # 目标人群
    product_name: str  # 产品型号

    # 标题
    title_options: List[TitleOption] = field(default_factory=list)
    selected_title: str = ""

    # 正文
    opening: str = ""  # 开头
    body: str = ""  # 正文主体
    cta: str = ""  # 行动引导
    version_note: str = ""  # 版本提醒

    # 配图
    images: List[ImagePlan] = field(default_factory=list)

    # 知识依据
    knowledge_sources: List[str] = field(default_factory=list)
    facts_used: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "platform": self.platform,
            "scenario": self.scenario,
            "target_audience": self.target_audience,
            "product_name": self.product_name,
            "title_options": [
                {"title": opt.title, "style": opt.style, "reason": opt.reason}
                for opt in self.title_options
            ],
            "selected_title": self.selected_title,
            "opening": self.opening,
            "body": self.body,
            "cta": self.cta,
            "version_note": self.version_note,
            "images": [
                {
                    "filename": img.filename,
                    "source": img.source,
                    "position": img.position,
                    "purpose": img.purpose,
                    "caption": img.caption,
                    "limitation": img.limitation
                }
                for img in self.images
            ],
            "knowledge_sources": self.knowledge_sources,
            "facts_used": self.facts_used
        }

    def to_markdown(self) -> str:
        """生成Markdown格式输出"""
        lines = []

        # 场景判断
        lines.append("# 图文软文成稿\n")
        lines.append("## 一、场景判断\n")
        lines.append(f"- **平台**: {self.platform}\n")
        lines.append(f"- **目标人群**: {self.target_audience}\n")
        lines.append(f"- **使用场景**: {self.scenario}\n")
        lines.append(f"- **产品型号**: {self.product_name}\n")

        # 知识依据
        lines.append("\n## 二、知识依据\n")
        if self.knowledge_sources:
            lines.append("**来源文件**:\n")
            for source in self.knowledge_sources:
                lines.append(f"- {source}\n")

        if self.facts_used:
            lines.append("\n**使用的事实**:\n")
            for fact in self.facts_used:
                lines.append(f"- {fact}\n")

        # 标题
        lines.append("\n## 三、标题方案\n")
        for i, opt in enumerate(self.title_options, 1):
            lines.append(f"### 方案{i}: {opt.style}\n")
            lines.append(f"**{opt.title}**\n\n")
            lines.append(f"*{opt.reason}*\n\n")

        lines.append(f"**采用标题**: {self.selected_title}\n")

        # 正文
        lines.append("\n## 四、正文内容\n")
        lines.append(f"{self.opening}\n\n")
        lines.append(f"{self.body}\n\n")

        # CTA
        if self.cta:
            lines.append(f"**行动引导**: {self.cta}\n\n")

        # 版本提醒
        if self.version_note:
            lines.append(f"*{self.version_note}*\n\n")

        # 配图方案
        lines.append("\n## 五、配图方案\n")
        for i, img in enumerate(self.images, 1):
            lines.append(f"### 图片{i}\n")
            lines.append(f"- **文件名**: {img.filename}\n")
            lines.append(f"- **来源**: {img.source}\n")
            lines.append(f"- **插入位置**: {img.position}\n")
            lines.append(f"- **画面用途**: {img.purpose}\n")
            lines.append(f"- **图注**: {img.caption}\n")
            if img.limitation:
                lines.append(f"- **限制**: {img.limitation}\n")
            lines.append("\n")

        return "".join(lines)


class ArticleGenerator:
    """软文生成器"""

    def __init__(self, knowledge_base_path: str):
        """
        初始化生成器

        Args:
            knowledge_base_path: 知识库根目录
        """
        self.retriever = KnowledgeRetriever(knowledge_base_path)

    def generate_titles(self,
                       product_name: str,
                       scenario: str,
                       platform: str,
                       target_audience: str) -> List[TitleOption]:
        """
        生成标题方案

        Args:
            product_name: 产品型号
            scenario: 使用场景
            platform: 发布平台
            target_audience: 目标人群

        Returns:
            标题选项列表
        """
        titles = []

        # 获取产品信息
        facts = self.retriever.get_product_facts(product_name)
        if not facts:
            return titles

        # 提取关键信息
        os_info = facts.get("os", "")
        screen_size = facts.get("screen_size", "")
        is_harmonyos = "HarmonyOS" in os_info or "鸿蒙" in os_info

        # 方案1: 场景式（具体人物+任务）
        if "学生" in target_audience or "学习" in scenario:
            title1 = f"{product_name}：开学季选笔记本，这几点要注意"
            reason1 = "场景式开头，指出目标人群和关键任务"
        elif "办公" in scenario:
            title1 = f"移动办公换新机？{product_name}实际体验分享"
            reason1 = "疑问式引入，贴近办公人群痛点"
        elif "创作" in scenario:
            title1 = f"内容创作者选本指南：{product_name}上手体验"
            reason1 = "明确人群定位，降低阅读门槛"
        else:
            title1 = f"{product_name}：适合哪些人？"
            reason1 = "直接疑问，引导读者对号入座"

        titles.append(TitleOption(
            title=title1,
            style="场景式",
            reason=reason1
        ))

        # 方案2: 利益式（解决问题）
        if is_harmonyos:
            title2 = f"华为生态用户换新本：{product_name}协同体验如何？"
            reason2 = "突出鸿蒙生态协同利益点，筛选精准人群"
        else:
            title2 = f"轻薄本怎么选？从{product_name}说起"
            reason2 = "从常见问题切入，自然引出产品"

        titles.append(TitleOption(
            title=title2,
            style="利益式",
            reason=reason2
        ))

        # 方案3: 陈述式（直接信息）
        if screen_size:
            title3 = f"{product_name}：{screen_size}轻薄本选购要点"
            reason3 = "包含关键参数，吸引搜索流量"
        else:
            title3 = f"{product_name}选购指南（附配置建议）"
            reason3 = "信息密度高，适合搜索场景"

        titles.append(TitleOption(
            title=title3,
            style="陈述式",
            reason=reason3
        ))

        # 根据平台调整（硬分叉，禁止两平台仅差分隔符）
        if platform == "小红书":
            titles[0].title = f"姐妹们看过来😭｜{product_name}真实上手，这几点别踩坑"
            titles[0].reason = "小红书情绪种草标题，区别于朋友圈销售短帖"
            titles[1].title = f"用了一周才敢说｜{product_name}适不适合{target_audience}"
            titles[2].title = f"{product_name}避雷笔记｜买前先看这3点"
        elif platform == "朋友圈":
            titles[0].title = f"🔥 {product_name}｜现货可体验"
            titles[0].reason = "朋友圈销售短帖标题，禁止种草长句"
            titles[1].title = f"✅ {product_name}到店可看实机"
            titles[2].title = f"{product_name}｜配置以官网为准，欢迎咨询"

        return titles

    def generate_opening(self,
                        product_name: str,
                        scenario: str,
                        target_audience: str,
                        platform: str) -> str:
        """
        生成开头段落

        Args:
            product_name: 产品型号
            scenario: 场景
            target_audience: 目标人群
            platform: 平台

        Returns:
            开头段落
        """
        if "学生" in target_audience:
            opening = (
                "新学期开始，选择一台适合学习的笔记本电脑是很多学生和家长关注的问题。"
                "轻薄便携、续航够用、价格合理，同时还要考虑系统和软件兼容性。"
                f"{product_name}是否适合学生使用？下面从实际需求出发，说明几个关键点。"
            )
        elif "办公" in scenario:
            opening = (
                "移动办公对笔记本的要求：轻薄便携、续航长、接口够用、协同方便。"
                f"{product_name}在这些方面表现如何？适合哪些办公场景？"
                "本文从实际使用角度，梳理几个需要确认的要点。"
            )
        elif "创作" in scenario:
            opening = (
                "内容创作者选笔记本，除了性能参数，还要考虑屏幕素质、文件管理和多设备协作。"
                f"{product_name}能满足哪些创作需求？有哪些限制？"
                "下面从常见工作流程说起。"
            )
        else:
            opening = (
                "选购笔记本电脑，参数固然重要，但更关键的是了解自己的使用场景和限制条件。"
                f"{product_name}有哪些特点？适合谁？不适合谁？"
                "本文列出几个判断要点，帮助你做出选择。"
            )

        # 【平台分叉】朋友圈压成短帖导语；小红书保持种草口吻
        if platform == "朋友圈":
            opening = (
                f"🔥 {product_name}｜现货可体验\n"
                f"适合{target_audience}·{scenario}\n"
                "✅ 配置以官网/门店实机为准"
            )
        elif platform == "小红书":
            opening = (
                f"用了几天{product_name}，按「{target_audience}/{scenario}」真实记录～"
                "只写能核对的点，不写没依据的承诺。"
            )
        return opening

    def generate_body(self,
                     product_name: str,
                     scenario: str,
                     platform: str) -> Tuple[str, List[str]]:
        """
        生成正文主体

        Args:
            product_name: 产品型号
            scenario: 场景
            platform: 平台

        Returns:
            (正文内容, 使用的事实列表)
        """
        facts = self.retriever.get_product_facts(product_name)
        if not facts:
            return "", []

        # 【平台硬分叉】小红书种草体 / 朋友圈短帖，禁止共用软文骨架
        if platform == "朋友圈":
            return self._body_moments(product_name, facts)
        if platform == "小红书":
            return self._body_xhs(product_name, facts)

        facts_used = []
        paragraphs = []

        # 段落1: 基础配置
        os_info = facts.get("os", "")
        processor = facts.get("processor", "")
        memory = facts.get("memory", "")
        storage = facts.get("storage", "")

        para1 = f"**配置方面**\n\n"
        if os_info:
            para1 += f"{product_name}搭载{os_info}操作系统"
            facts_used.append(f"操作系统: {os_info}")
            if "HarmonyOS" in os_info:
                para1 += "，与华为手机、平板可以实现文件互传、屏幕共享等协同功能（需登录同一华为账号）"
            para1 += "。"

        if processor:
            para1 += f"处理器为{processor}，"
            facts_used.append(f"处理器: {processor}")

        if memory and storage:
            para1 += f"配备{memory}内存和{storage}存储。"
            facts_used.append(f"内存: {memory}")
            facts_used.append(f"存储: {storage}")

        para1 += "购买前建议确认你的必用软件对该系统和配置的支持情况。\n\n"
        paragraphs.append(para1)

        # 段落2: 屏幕与便携性
        screen_size = facts.get("screen_size", "")
        screen_type = facts.get("screen_type", "")
        resolution = facts.get("resolution", "")
        weight = facts.get("weight", "")

        para2 = "**屏幕与便携性**\n\n"
        if screen_size:
            para2 += f"屏幕为{screen_size}"
            facts_used.append(f"屏幕尺寸: {screen_size}")

        if screen_type:
            para2 += f"{screen_type}"
            facts_used.append(f"屏幕类型: {screen_type}")

        if resolution:
            para2 += f"，分辨率{resolution}"
            facts_used.append(f"分辨率: {resolution}")

        para2 += "。"

        # 判断屏幕比例
        if "2880" in resolution and "1920" in resolution:
            para2 += "3:2屏幕比例相比常见的16:9，纵向显示内容更多，适合文档编辑和网页浏览。"

        if weight:
            para2 += f"机身重量约{weight}，"
            facts_used.append(f"重量: 约{weight}")
            if "1.3" in weight or "1.2" in weight:
                para2 += "携带较为轻便。"
            else:
                para2 += "需要考虑携带负担。"

        para2 += "\n\n"
        paragraphs.append(para2)

        # 段落3: 使用场景建议
        para3 = "**适用场景**\n\n"

        if "HarmonyOS" in os_info:
            para3 += "适合已经使用华为手机、平板的用户，可以充分发挥生态协同优势。"
            para3 += "如果你的工作或学习依赖Windows专属软件（某些专业软件、企业内部系统），需要提前确认兼容性。"
        else:
            para3 += "Windows系统兼容性好，适合需要运行专业软件或企业办公的用户。"

        if "学生" in scenario or "学习" in scenario:
            para3 += "对于学生群体，建议根据专业要求选择：文科、商科一般无特殊要求；"
            para3 += "理工科、设计类专业需要确认专业软件的支持情况。"

        para3 += "\n\n"
        paragraphs.append(para3)

        # 段落4: 购买建议
        para4 = "**购买建议**\n\n"
        para4 += "建议到官方渠道或授权门店实际体验，确认以下几点：\n"
        para4 += "1. 键盘手感和屏幕显示效果是否符合你的使用习惯\n"
        para4 += "2. 接口类型和数量是否满足你的外设需求\n"
        para4 += "3. 必用软件在该系统上的运行情况\n"
        para4 += "4. 当前销售版本的配置和价格（配置可能因销售批次而异）\n\n"
        paragraphs.append(para4)

        body = "".join(paragraphs)
        return body, facts_used


    def _body_xhs(self, product_name: str, facts: dict):
        """小红书种草小节，非软文报告。"""
        used = []
        parts = [
            f"先说体感：{product_name}更适合日常种草笔记，不是到店推销短帖。",
        ]
        mapping = [
            ("✨ 屏幕｜观感", "screen_size", "screen_type", "resolution"),
            ("🎒 便携｜出门", "weight",),
            ("📱 系统｜协同", "os",),
            ("⚙️ 配置｜性能底子", "processor", "memory", "storage"),
        ]
        for item in mapping:
            title, keys = item[0], item[1:]
            vals = []
            for k in keys:
                v = facts.get(k)
                if v:
                    vals.append(str(v))
                    used.append(f"{k}: {v}")
            if vals:
                parts.append(f"{title}\n" + "，".join(vals) + "。真实上手比参数表直观，版本差异记得回官网核对。")
        parts.append(
            "避雷｜不同销售版本配置可能不同，请以官方规格页及实机为准；不写价格库存补贴。"
        )
        parts.append(
            "💬 同场景你们用什么本？评论区聊聊～\n📌 建议收藏对照官方页\n"
            f"#真实上手 #{product_name.replace(' ', '')} #避雷指南"
        )
        return "\n\n".join(parts), used

    def _body_moments(self, product_name: str, facts: dict):
        """朋友圈销售短帖：短行+✓参数。"""
        used = []
        lines = [f"🔥 {product_name}｜现货可体验", ""]
        for label, key in [
            ("屏幕", "screen_size"),
            ("重量", "weight"),
            ("系统", "os"),
            ("处理器", "processor"),
        ]:
            v = facts.get(key)
            if v:
                lines.append(f"✅ {label}：{v}")
                used.append(f"{key}: {v}")
        lines.extend([
            "",
            "✓ 配置以官网/门店实机为准",
            "✓ 到店可上手体验",
            "✓ 详询可私信预约",
            "",
            "欢迎到店咨询～",
            "不同销售版本配置可能不同，请以官方规格页及实际销售 SKU 为准。",
        ])
        return "\n".join(lines), used


    def generate_cta(self, platform: str, scenario: str) -> str:
        """
        生成行动引导

        Args:
            platform: 平台
            scenario: 场景

        Returns:
            CTA文案
        """
        if platform == "公众号":
            cta = "想了解更多配置信息？可访问华为官网产品页，或到附近华为授权体验店实际上手体验。"
        elif platform == "小红书":
            cta = "💬 你在用什么笔记本？欢迎评论区分享～\n📌 记得收藏，选本时可以对比参考"
        elif platform == "朋友圈":
            cta = "详细配置和价格可到店咨询，欢迎预约体验"
        else:
            cta = "建议根据实际需求选择，到官方渠道确认当前销售版本的配置和价格。"

        return cta

    def generate_images(self,
                       product_name: str,
                       platform: str) -> List[ImagePlan]:
        """
        生成配图方案

        Args:
            product_name: 产品型号
            platform: 平台

        Returns:
            配图方案列表
        """
        images = []

        # 主图：产品正面图
        images.append(ImagePlan(
            filename=f"{product_name.replace(' ', '_').lower()}_front.jpg",
            source=f"ima知识库/P6-营销素材库/04-图片/{product_name}/产品正面图",
            position="标题下方",
            purpose="展示产品整体外观",
            caption=f"{product_name}",
            limitation="需使用ima知识库中的官方图片"
        ))

        # 屏幕展示图
        images.append(ImagePlan(
            filename=f"{product_name.replace(' ', '_').lower()}_screen.jpg",
            source=f"ima知识库/P6-营销素材库/04-图片/{product_name}/屏幕显示",
            position="屏幕与便携性段落",
            purpose="展示屏幕显示效果和比例",
            caption="3:2屏幕比例显示效果",
            limitation=""
        ))

        # 如果是鸿蒙系统，添加协同功能图
        facts = self.retriever.get_product_facts(product_name)
        if facts and "HarmonyOS" in facts.get("os", ""):
            images.append(ImagePlan(
                filename="harmonyos_collaboration.jpg",
                source="ima知识库/P6-营销素材库/05-多屏协同/鸿蒙协同示意图",
                position="配置方面段落",
                purpose="展示多设备协同功能",
                caption="与华为手机、平板协同工作",
                limitation="功能需要登录同一华为账号"
            ))

        return images

    def generate_article(self,
                        product_name: str,
                        scenario: str,
                        platform: str,
                        target_audience: str) -> ArticleContent:
        """
        生成完整软文

        Args:
            product_name: 产品型号
            scenario: 使用场景
            platform: 发布平台
            target_audience: 目标人群

        Returns:
            完整软文内容
        """
        article = ArticleContent(
            platform=platform,
            scenario=scenario,
            target_audience=target_audience,
            product_name=product_name
        )

        # 生成标题
        article.title_options = self.generate_titles(
            product_name, scenario, platform, target_audience
        )
        if article.title_options:
            article.selected_title = article.title_options[0].title

        # 生成开头
        article.opening = self.generate_opening(
            product_name, scenario, target_audience, platform
        )

        # 生成正文
        body, facts_used = self.generate_body(product_name, scenario, platform)
        article.body = body
        article.facts_used = facts_used

        # 生成CTA
        article.cta = self.generate_cta(platform, scenario)

        # 版本提醒
        article.version_note = (
            "本文内容基于华为官网公开信息整理，"
            "产品配置可能因销售版本和地区而异，"
            "具体信息以购买时的实际销售版本为准。"
        )

        # 生成配图方案
        article.images = self.generate_images(product_name, platform)

        # 添加知识来源
        facts = self.retriever.get_product_facts(product_name)
        if facts:
            article.knowledge_sources.append(facts.get("source_file", ""))
            if "official_url" in facts:
                article.knowledge_sources.append(facts["official_url"])

        return article


def main():
    """测试软文生成器"""
    import os

    kb_path = os.path.join(os.path.dirname(__file__),
                           "华为PC知识库(1)",
                           "华为PC全板块深度知识库_v7")

    generator = ArticleGenerator(kb_path)

    print("=" * 60)
    print("软文生成器测试")
    print("=" * 60)

    # 生成软文
    article = generator.generate_article(
        product_name="HUAWEI MateBook 14",
        scenario="学生学习",
        platform="公众号",
        target_audience="大学生"
    )

    # 输出Markdown
    print(article.to_markdown())

    # 保存到文件
    output_file = "generated_article.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(article.to_markdown())

    print(f"\n软文已保存至: {output_file}")


if __name__ == "__main__":
    main()
