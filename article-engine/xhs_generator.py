"""
小红书种草文案生成器 - 口语化、感性化、视觉化
"""
import os
import shutil
from typing import List, Dict
from knowledge_retriever import KnowledgeRetriever


class XHSArticleGenerator:
    """小红书风格文案生成器"""

    def __init__(self, knowledge_base_path: str):
        self.retriever = KnowledgeRetriever(knowledge_base_path)
        self.kb_path = knowledge_base_path

    def generate(self, product_name: str, scenario: str, target_audience: str) -> Dict:
        """生成小红书风格文案"""

        # 获取产品信息
        facts = self.retriever.get_product_facts(product_name)
        if not facts:
            return {"error": "产品信息未找到"}

        # 根据场景选择风格
        if "颜值" in scenario or "外观" in scenario or "新色" in scenario:
            return self._generate_color_style(product_name, facts, target_audience)
        elif "学生" in scenario or target_audience == "大学生":
            return self._generate_student_style(product_name, facts, target_audience)
        else:
            return self._generate_general_style(product_name, facts, scenario, target_audience)

    def _generate_color_style(self, product_name: str, facts: Dict, audience: str) -> Dict:
        """生成颜值/新色风格文案"""

        # 提取关键信息
        screen = facts.get('screen_size', '14.2 英寸')
        weight = facts.get('weight', '约1.33 kg')
        os_name = facts.get('os', 'HarmonyOS')

        # 标题（夸张+emoji+感叹）
        title = f"救命！{product_name}新色，美到我心巴了😭"

        # 副标题
        subtitle = f"{product_name}｜这波新配色，春日氛围感直接拉满！✨"

        # 开头（情绪化）
        opening = f"姐妹们！{product_name}出新色了！直接把春天装进了笔记本！\n这次的配色真的太懂了，摆在桌上就是颜值天花板，每天打开电脑心情都是甜甜的～"

        # 正文段落
        sections = []

        # 段落1：颜值描述
        sections.append({
            "emoji": "🎨",
            "title": "配色｜氛围感直接拉满",
            "content": f"这次的配色真的绝了！低饱和的莫兰迪调，自带温柔滤镜。\n雾面质感细腻不沾指纹，摆在桌上就是一件艺术品，完全不是普通的笔记本能比的！\n拍照发朋友圈，氛围感直接拉满～"
        })

        # 段落2：屏幕体验
        sections.append({
            "emoji": "🖥️",
            "title": "屏幕｜{screen}高清好屏",
            "content": f"{screen}的OLED屏，色彩通透又细腻。\n超窄边框看起来特别沉浸，不管是追剧还是修图，画面都超治愈。\n长时间对着也不觉得累，护眼又高级～"
        })

        # 段落3：便携性
        sections.append({
            "emoji": "💼",
            "title": "便携｜{weight}轻薄随行",
            "content": f"重量才{weight}，放进包里完全没负担！\n去图书馆、咖啡厅随便带，女生单手也能轻松拿。\n这种轻薄感，一旦用过就回不去了～"
        })

        # 段落4：功能亮点
        if "HarmonyOS" in os_name or "鸿蒙" in os_name:
            sections.append({
                "emoji": "✨",
                "title": "鸿蒙生态｜多屏协同超丝滑",
                "content": "华为手机一碰就连，传文件、拖照片都丝滑到飞起！\n上课拍的PPT直接拖到电脑，写作业找资料超方便。\n完全不是花瓶款，日常使用体验太香了～"
            })

        # CTA
        cta = "💬 你们用的什么笔记本呀？评论区分享～\n📌 记得收藏，换电脑的时候可以对比参考！"

        # 话题标签
        tags = ["#笔记本颜值天花板", "#学生党笔记本", f"#{product_name}"]

        return {
            "title": title,
            "subtitle": subtitle,
            "opening": opening,
            "sections": sections,
            "cta": cta,
            "tags": tags
        }

    def _generate_student_style(self, product_name: str, facts: Dict, audience: str) -> Dict:
        """生成学生场景风格文案"""

        screen = facts.get('screen_size', '14.2 英寸')
        weight = facts.get('weight', '约1.33 kg')
        os_name = facts.get('os', 'HarmonyOS')

        title = f"开学换本｜{product_name}实测，真香预警⚠️"
        subtitle = f"{product_name}｜学生党选本攻略，这几点必看！"

        opening = f"开学季到了，终于换了{product_name}！\n用了一周，真的太适合学生党了，来给大家分享下真实使用感受～"

        sections = []

        sections.append({
            "emoji": "📚",
            "title": "学习体验｜{screen}看文档超舒服",
            "content": f"{screen}的OLED屏，3:2比例看PDF、写论文特别爽！\n一屏能显示更多内容，不用频繁滚动。\n对着屏幕一整天眼睛也不累，护眼效果确实不错～"
        })

        sections.append({
            "emoji": "🎒",
            "title": "便携｜{weight}背去图书馆不累",
            "content": f"重量才{weight}，放书包里完全没负担。\n每天背去图书馆，比带两本教材还轻！\n这种轻薄感，通勤党真的会爱死～"
        })

        if "HarmonyOS" in os_name or "鸿蒙" in os_name:
            sections.append({
                "emoji": "📱",
                "title": "协同｜华为手机党狂喜",
                "content": "如果你用华为手机，这个协同功能真的绝了！\n上课拍的PPT、手机的资料，直接拖过来就能用。\n不用U盘、不用微信传，效率直接起飞～"
            })

        sections.append({
            "emoji": "⚠️",
            "title": "避雷｜软件兼容记得确认",
            "content": f"如果你专业需要用特定软件（CAD、PR之类），记得提前确认下兼容性！\n{os_name}系统常用办公软件都没问题，但专业软件建议到店试试。\n文科、商科专业基本都能满足～"
        })

        cta = "💬 你们专业都用什么笔记本？评论区聊聊～\n📌 建议收藏！选本的时候能少踩坑！"

        tags = ["#学生党笔记本", "#开学季", f"#{product_name}"]

        return {
            "title": title,
            "subtitle": subtitle,
            "opening": opening,
            "sections": sections,
            "cta": cta,
            "tags": tags
        }

    def _generate_general_style(self, product_name: str, facts: Dict, scenario: str, audience: str) -> Dict:
        """生成通用风格文案"""

        title = f"{product_name}真实使用感受，来唠唠～"
        subtitle = f"{product_name}｜{scenario}实测体验"

        opening = f"用了{product_name}一段时间，来分享下真实感受！"

        sections = [
            {
                "emoji": "✨",
                "title": "初印象｜颜值在线",
                "content": "拆箱第一眼就被颜值吸引了，设计很简约高级。"
            }
        ]

        cta = "💬 你们在用什么笔记本？评论区分享～"
        tags = [f"#{product_name}", "#笔记本推荐"]

        return {
            "title": title,
            "subtitle": subtitle,
            "opening": opening,
            "sections": sections,
            "cta": cta,
            "tags": tags
        }

    def find_images(self, product_name: str) -> List[str]:
        """查找产品图片"""
        image_paths = []

        # 搜索路径
        search_path = os.path.join(self.kb_path, "P6-营销素材库/04-图片")

        if not os.path.exists(search_path):
            return []

        # 遍历查找所有图片
        for root, dirs, files in os.walk(search_path):
            for file in files:
                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                    # MateBook系列的图片
                    if "matebook" in file.lower() or "协同" in file or "屏" in file:
                        full_path = os.path.join(root, file)
                        image_paths.append(full_path)

        return image_paths[:5]  # 最多5张

    def generate_html(self, content: Dict, output_path: str, images: List[str] = None):
        """生成带真实图片的HTML"""

        # 复制图片到输出目录
        output_dir = os.path.dirname(output_path)
        image_dir = os.path.join(output_dir, "images")
        os.makedirs(image_dir, exist_ok=True)

        copied_images = []
        if images:
            for i, img_path in enumerate(images[:3]):
                if os.path.exists(img_path):
                    ext = os.path.splitext(img_path)[1]
                    new_name = f"image_{i+1}{ext}"
                    new_path = os.path.join(image_dir, new_name)
                    shutil.copy2(img_path, new_path)
                    copied_images.append(f"images/{new_name}")

        # 生成HTML
        html = self._build_html(content, copied_images)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        return output_path

    def _build_html(self, content: Dict, images: List[str]) -> str:
        """构建HTML内容"""

        html_parts = ['''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>''' + content['title'] + '''</title>
    <style>
        :root { color-scheme: light; }
        body {
            max-width: 680px;
            margin: 20px auto;
            padding: 0 20px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
            line-height: 1.8;
            color: #333;
            background: #f8f8f8;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 16px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        }
        h1 {
            font-size: 22px;
            font-weight: 700;
            margin: 0 0 10px;
            color: #000;
            line-height: 1.4;
        }
        .subtitle {
            font-size: 16px;
            color: #666;
            margin-bottom: 20px;
        }
        .opening {
            background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
            padding: 20px;
            border-radius: 12px;
            margin: 20px 0;
            font-size: 15px;
            line-height: 1.8;
        }
        .image {
            width: 100%;
            border-radius: 12px;
            margin: 20px 0;
        }
        .section {
            margin: 30px 0;
        }
        .section-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 12px;
            color: #000;
        }
        .section-content {
            font-size: 15px;
            line-height: 1.9;
            color: #333;
            white-space: pre-line;
        }
        .cta {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 12px;
            margin: 30px 0;
            font-size: 15px;
            line-height: 1.8;
            white-space: pre-line;
        }
        .tags {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 20px;
        }
        .tag {
            background: #f0f0f0;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 14px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>''' + content['title'] + '''</h1>''']

        if 'subtitle' in content:
            html_parts.append(f'<div class="subtitle">{content["subtitle"]}</div>')

        # 第一张图
        if images and len(images) > 0:
            html_parts.append(f'<img src="{images[0]}" class="image" alt="产品图">')

        html_parts.append(f'<div class="opening">{content["opening"]}</div>')

        # 正文段落
        for i, section in enumerate(content.get('sections', [])):
            html_parts.append(f'''
        <div class="section">
            <div class="section-title">{section['emoji']} {section['title']}</div>
            <div class="section-content">{section['content']}</div>
        </div>''')

            # 在中间插入图片
            if i == 1 and images and len(images) > 1:
                html_parts.append(f'<img src="{images[1]}" class="image" alt="产品细节">')
            elif i == 3 and images and len(images) > 2:
                html_parts.append(f'<img src="{images[2]}" class="image" alt="使用场景">')

        html_parts.append(f'''
        <div class="cta">{content['cta']}</div>
        <div class="tags">''')

        for tag in content.get('tags', []):
            html_parts.append(f'<span class="tag">{tag}</span>')

        html_parts.append('''
        </div>
    </div>
</body>
</html>''')

        return ''.join(html_parts)


def main():
    """测试生成"""
    import os

    kb_path = os.path.join(os.path.dirname(__file__),
                           "华为PC知识库(1)",
                           "华为PC全板块深度知识库_v7")

    generator = XHSArticleGenerator(kb_path)

    # 场景1：颜值/新色
    print("=" * 60)
    print("场景1: 颜值种草风格")
    print("=" * 60)

    content = generator.generate(
        product_name="HUAWEI MateBook 14",
        scenario="新色外观",
        target_audience="学生党"
    )

    # 查找图片
    images = generator.find_images("HUAWEI MateBook 14")
    print(f"\n找到 {len(images)} 张图片")
    for img in images[:3]:
        print(f"  - {os.path.basename(img)}")

    # 生成HTML
    output_path = "xhs_color_style.html"
    generator.generate_html(content, output_path, images)
    print(f"\n✅ 已生成: {output_path}")

    # 场景2：学生场景
    print("\n" + "=" * 60)
    print("场景2: 学生实用风格")
    print("=" * 60)

    content2 = generator.generate(
        product_name="HUAWEI MateBook 14",
        scenario="学生学习",
        target_audience="大学生"
    )

    output_path2 = "xhs_student_style.html"
    generator.generate_html(content2, output_path2, images)
    print(f"\n✅ 已生成: {output_path2}")


if __name__ == "__main__":
    main()
