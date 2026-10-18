"""
小红书图文自动生成器
支持多种风格，自动提取知识库内容，自动匹配图片
"""
import os
import builtins
import shutil
from typing import Dict, List, Optional
from knowledge_retriever import KnowledgeRetriever

def _safe_print(*args, **kwargs):
    try:
        builtins.print(*args, **kwargs)
    except Exception:
        text = " ".join(str(a) for a in args)
        builtins.print(text.encode("ascii", "replace").decode("ascii"))



class XHSAutoGenerator:
    """小红书图文自动生成器"""

    def __init__(self, knowledge_base_path: str):
        self.retriever = KnowledgeRetriever(knowledge_base_path)
        self.kb_path = knowledge_base_path

    def generate(
        self,
        product_name: str,
        style: str = "颜值种草",
        target_audience: str = "学生党",
        output_path: str = None
    ) -> str:
        """
        自动生成小红书图文

        Args:
            product_name: 产品名称，如 "HUAWEI MateBook 14"
            style: 文案风格 - "颜值种草", "性能实测", "学生党", "职场办公"
            target_audience: 目标人群 - "学生党", "职场人士", "创作者", "女性用户"
            output_path: 输出HTML路径，不指定则自动生成

        Returns:
            生成的HTML文件路径
        """

        _safe_print(f"🎨 开始生成小红书图文...")
        _safe_print(f"   产品: {product_name}")
        _safe_print(f"   风格: {style}")
        _safe_print(f"   人群: {target_audience}")

        # 1. 提取产品信息
        _safe_print("\n📚 提取产品信息...")
        facts = self.retriever.get_product_facts(product_name)
        if not facts:
            raise ValueError(f"未找到产品信息: {product_name}")

        # 2. 查找产品图片
        _safe_print("🖼️  查找产品图片...")
        image_path = self._find_best_image(product_name)
        if not image_path:
            _safe_print("   ⚠️  未找到产品图片，将使用占位符")

        # 3. 生成文案
        _safe_print("✍️  生成文案内容...")
        content = self._generate_content(product_name, facts, style, target_audience)

        # 4. 生成HTML
        _safe_print("🎯 生成HTML页面...")
        if not output_path:
            safe_name = product_name.replace(" ", "_").replace("/", "_")
            output_path = f"xhs_{safe_name}_{style}.html"

        html_path = self._generate_html(content, image_path, output_path)

        _safe_print(f"\n✅ 生成完成: {html_path}")
        return html_path

    def _find_best_image(self, product_name: str) -> Optional[str]:
        """查找最佳产品图片"""

        # 搜索路径
        product_dir = None
        for root, dirs, files in os.walk(os.path.join(self.kb_path, "P1-产品参数库")):
            for d in dirs:
                if product_name in d:
                    product_dir = os.path.join(root, d)
                    break
            if product_dir:
                break

        if not product_dir:
            return None

        # 优先顺序：商城款式图片 > images > 其他
        search_paths = [
            os.path.join(product_dir, "商城款式图片"),
            os.path.join(product_dir, "images"),
            product_dir
        ]

        for search_path in search_paths:
            if not os.path.exists(search_path):
                continue

            for root, dirs, files in os.walk(search_path):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                        # 优先选择配色、外观相关图片
                        if any(keyword in file for keyword in ['配色', '外观', '正面', '展示', '樱粉金', '原野绿']):
                            return os.path.join(root, file)

            # 如果没找到优先图片，返回第一张
            for root, dirs, files in os.walk(search_path):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                        return os.path.join(root, file)

        return None

    def _generate_content(
        self,
        product_name: str,
        facts: Dict,
        style: str,
        audience: str
    ) -> Dict:
        """根据风格生成内容"""

        if style == "颜值种草":
            return self._generate_beauty_content(product_name, facts, audience)
        elif style == "性能实测":
            return self._generate_performance_content(product_name, facts, audience)
        elif style == "学生党":
            return self._generate_student_content(product_name, facts, audience)
        elif style == "职场办公":
            return self._generate_workplace_content(product_name, facts, audience)
        else:
            return self._generate_general_content(product_name, facts, audience)

    def _generate_beauty_content(self, product_name: str, facts: Dict, audience: str) -> Dict:
        """颜值种草风格"""

        screen = facts.get('screen_size', '14英寸')
        weight = facts.get('weight', '轻薄')
        os_name = facts.get('os', 'HarmonyOS')

        return {
            "author": "李闪闪",
            "title": f"{product_name}新色，美到我心巴了😭",
            "sections": [
                {
                    "emoji": "🎨",
                    "title": "配色｜氛围感直接拉满",
                    "content": f"这次的配色真的绝了！低饱和的莫兰迪调，自带温柔滤镜。\n雾面质感细腻不沾指纹，摆在桌上就是一件艺术品，完全不是普通的笔记本能比的！\n拍照发朋友圈，氛围感直接拉满～"
                },
                {
                    "emoji": "🖥️",
                    "title": f"屏幕｜{screen}高清好屏",
                    "content": f"{screen}的OLED屏，色彩通透又细腻。\n超窄边框看起来特别沉浸，不管是追剧还是修图，画面都超治愈。\n长时间对着也不觉得累，护眼又高级～"
                },
                {
                    "emoji": "💼",
                    "title": f"便携｜{weight}轻薄随行",
                    "content": f"重量才{weight}，放进包里完全没负担！\n去图书馆、咖啡厅随便带，女生单手也能轻松拿。\n这种轻薄感，一旦用过就回不去了～"
                },
                {
                    "emoji": "✨",
                    "title": "鸿蒙生态｜多屏协同超丝滑",
                    "content": "华为手机一碰就连，传文件、拖照片都丝滑到飞起！\n上课拍的PPT直接拖到电脑，写作业找资料超方便。\n完全不是花瓶款，日常使用体验太香了～"
                }
            ],
            "cta": "💬 你们用的什么笔记本呀？评论区分享～\n📌 记得收藏，换电脑的时候可以对比参考！",
            "tags": ["#笔记本颜值天花板", f"#{audience}", f"#{product_name.replace(' ', '')}"]
        }

    def _generate_performance_content(self, product_name: str, facts: Dict, audience: str) -> Dict:
        """性能实测风格"""

        processor = facts.get('processor', '高性能处理器')
        screen = facts.get('screen_size', '14英寸')
        weight = facts.get('weight', '轻薄')
        resolution = facts.get('resolution', '高分辨率')

        return {
            "author": "数码博主Leo",
            "title": f"{product_name}实测｜性能真香预警⚠️",
            "sections": [
                {
                    "emoji": "⚡",
                    "title": f"{processor}｜性能直接拉满",
                    "content": f"搭载{processor}，实测性能真的能打！\nPR剪4K视频、PS修大图、多任务并行，完全不卡顿。风扇声音也很轻，图书馆用也不尴尬～\n日常使用真的丝滑，响应速度快到飞起！"
                },
                {
                    "emoji": "🖥️",
                    "title": f"{screen}高素质屏｜护眼又专业",
                    "content": f"{screen}屏幕，{resolution}分辨率，显示效果真的绝了！\n色彩准确，对比度高，修图、看视频都很爽。\n3:2黄金比例，看文档、写代码显示内容更多，效率直接翻倍！"
                },
                {
                    "emoji": "💼",
                    "title": f"{weight}机身｜真的轻到没负担",
                    "content": f"{weight}的机身，这才是真正的轻薄本！\n每天背着上班，放包里完全无感。\n商务出差、移动办公真的很合适！"
                },
                {
                    "emoji": "✨",
                    "title": "鸿蒙生态｜跨设备协同太爽了",
                    "content": "手机一碰电脑，文件秒传。手机来电话，电脑能接听。\n手机APP直接在电脑上用，无缝切换不要太丝滑！\n如果你用华为全家桶，这个生态体验真的回不去了～"
                }
            ],
            "cta": "💬 总结：性能、屏幕、便携、生态，四个维度都很能打！\n如果你是华为生态用户，这台真的可以闭眼入～",
            "tags": [f"#{product_name.replace(' ', '')}", "#轻薄本推荐", "#生产力工具", "#鸿蒙笔记本"]
        }

    def _generate_student_content(self, product_name: str, facts: Dict, audience: str) -> Dict:
        """学生党风格"""

        screen = facts.get('screen_size', '14英寸')
        weight = facts.get('weight', '轻薄')

        return {
            "author": "大学生阿星",
            "title": f"开学换本｜{product_name}学生党必看！",
            "sections": [
                {
                    "emoji": "📚",
                    "title": f"学习体验｜{screen}看文档超舒服",
                    "content": f"{screen}的OLED屏，3:2比例看PDF、写论文特别爽！\n一屏能显示更多内容，不用频繁滚动。\n对着屏幕一整天眼睛也不累，护眼效果确实不错～"
                },
                {
                    "emoji": "🎒",
                    "title": f"便携｜{weight}背去图书馆不累",
                    "content": f"重量才{weight}，放书包里完全没负担。\n每天背去图书馆，比带两本教材还轻！\n这种轻薄感，通勤党真的会爱死～"
                },
                {
                    "emoji": "📱",
                    "title": "协同｜华为手机党狂喜",
                    "content": "如果你用华为手机，这个协同功能真的绝了！\n上课拍的PPT、手机的资料，直接拖过来就能用。\n不用U盘、不用微信传，效率直接起飞～"
                },
                {
                    "emoji": "⚠️",
                    "title": "避雷｜软件兼容记得确认",
                    "content": "如果你专业需要用特定软件（CAD、PR之类），记得提前确认下兼容性！\n常用办公软件都没问题，但专业软件建议到店试试。\n文科、商科专业基本都能满足～"
                }
            ],
            "cta": "💬 你们专业都用什么笔记本？评论区聊聊～\n📌 建议收藏！选本的时候能少踩坑！",
            "tags": ["#学生党笔记本", "#开学季", f"#{product_name.replace(' ', '')}"]
        }

    def _generate_workplace_content(self, product_name: str, facts: Dict, audience: str) -> Dict:
        """职场办公风格"""

        processor = facts.get('processor', '高性能处理器')
        weight = facts.get('weight', '轻薄')

        return {
            "author": "职场人张总",
            "title": f"{product_name}｜职场办公实测，真香！",
            "sections": [
                {
                    "emoji": "💼",
                    "title": f"{weight}机身｜通勤无负担",
                    "content": f"{weight}的重量，每天通勤带着完全不累。\n放进公文包轻轻松松，商务出差也很合适。\n外观简约大气，会议室拿出来很有面子～"
                },
                {
                    "emoji": "⚡",
                    "title": f"{processor}｜办公性能够用",
                    "content": f"搭载{processor}，日常办公完全够用。\nExcel、PPT、视频会议同时开，不卡顿。\n响应速度快，工作效率直接提升！"
                },
                {
                    "emoji": "✨",
                    "title": "多屏协同｜效率神器",
                    "content": "手机电脑无缝协同，文件互传超方便。\n手机来电脑能接，开会不用频繁切换设备。\n这个功能真的是办公利器！"
                }
            ],
            "cta": "💬 职场人必备！效率翻倍不是梦～",
            "tags": ["#职场办公", "#商务笔记本", f"#{product_name.replace(' ', '')}"]
        }

    def _generate_general_content(self, product_name: str, facts: Dict, audience: str) -> Dict:
        """通用风格"""
        return {
            "author": "数码爱好者",
            "title": f"{product_name}真实体验分享",
            "sections": [
                {"emoji": "✨", "title": "初印象", "content": "整体使用体验不错！"}
            ],
            "cta": "💬 你们怎么看？",
            "tags": [f"#{product_name.replace(' ', '')}"]
        }

    def _generate_html(self, content: Dict, image_path: Optional[str], output_path: str) -> str:
        """生成HTML文件"""

        # 复制图片到输出目录
        output_dir = os.path.dirname(os.path.abspath(output_path)) if os.path.dirname(output_path) else "."
        image_filename = "product_image.jpg"

        if image_path and os.path.exists(image_path):
            dest_path = os.path.join(output_dir, image_filename)
            shutil.copy2(image_path, dest_path)
            _safe_print(f"   📸 图片已复制: {os.path.basename(image_path)}")
        else:
            image_filename = "placeholder"

        # 生成HTML内容
        html = self._build_html_template(content, image_filename)

        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        return os.path.abspath(output_path)

    def _build_html_template(self, content: Dict, image_filename: str) -> str:
        """构建HTML模板"""

        sections_html = ""
        for section in content.get("sections", []):
            sections_html += f'''
        <div class="section">
            <div class="section-title">{section["emoji"]} {section["title"]}</div>
            <div class="section-content">{section["content"]}</div>
        </div>'''

        tags_html = ""
        for tag in content.get("tags", []):
            tags_html += f'<span class="tag">{tag}</span>\n                '

        return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{content["title"]} - 小红书</title>
    <style>
        :root {{ color-scheme: light; }}
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
            background: #f8f8f8;
            color: #333;
        }}
        .xhs-container {{
            max-width: 1200px;
            margin: 40px auto;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 16px rgba(0,0,0,0.1);
            display: flex;
        }}
        .image-section {{
            width: 60%;
            background: #000;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .main-image {{
            width: 100%;
            height: 100%;
            object-fit: cover;
        }}
        .content-section {{
            width: 40%;
            padding: 30px;
            display: flex;
            flex-direction: column;
            overflow-y: auto;
            max-height: 90vh;
        }}
        .author-info {{
            display: flex;
            align-items: center;
            margin-bottom: 20px;
        }}
        .avatar {{
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 18px;
            margin-right: 10px;
        }}
        .author-name {{
            font-size: 16px;
            font-weight: 600;
            color: #333;
        }}
        .follow-btn {{
            margin-left: auto;
            padding: 6px 20px;
            border: 1px solid #ff2442;
            color: #ff2442;
            background: white;
            border-radius: 20px;
            font-size: 14px;
            cursor: pointer;
            font-weight: 500;
        }}
        .title {{
            font-size: 22px;
            font-weight: 700;
            line-height: 1.4;
            margin-bottom: 20px;
            color: #000;
        }}
        .article-content {{
            font-size: 15px;
            line-height: 1.9;
            color: #333;
        }}
        .section {{
            margin: 25px 0;
        }}
        .section-title {{
            font-weight: 600;
            font-size: 16px;
            margin-bottom: 10px;
            color: #000;
        }}
        .section-content {{
            font-size: 15px;
            line-height: 1.9;
            color: #333;
            white-space: pre-line;
        }}
        .cta {{
            background: linear-gradient(135deg, #f0f7ff 0%, #e8f4ff 100%);
            padding: 18px;
            border-radius: 10px;
            margin: 25px 0;
            font-size: 14px;
            line-height: 1.8;
            white-space: pre-line;
            color: #333;
        }}
        .tags {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin: 20px 0;
        }}
        .tag {{
            background: #f5f5f5;
            padding: 5px 12px;
            border-radius: 4px;
            font-size: 13px;
            color: #0084ff;
            cursor: pointer;
        }}
        .tag:hover {{
            background: #e8f4ff;
        }}
        .interaction {{
            margin-top: auto;
            padding-top: 20px;
            border-top: 1px solid #f0f0f0;
            display: flex;
            align-items: center;
            gap: 20px;
            font-size: 14px;
            color: #999;
        }}
        .interaction-item {{
            display: flex;
            align-items: center;
            gap: 5px;
        }}
        .interaction-item svg {{
            width: 20px;
            height: 20px;
        }}
        @media (max-width: 768px) {{
            .xhs-container {{
                flex-direction: column;
            }}
            .image-section, .content-section {{
                width: 100%;
            }}
            .image-section {{
                height: 400px;
            }}
        }}
    </style>
</head>
<body>
    <div class="xhs-container">
        <div class="image-section">
            <img src="{image_filename}" alt="产品图" class="main-image">
        </div>

        <div class="content-section">
            <div class="author-info">
                <div class="avatar">{content["author"][0]}</div>
                <div class="author-name">{content["author"]}</div>
                <button class="follow-btn">关注</button>
            </div>

            <div class="title">{content["title"]}</div>

            <div class="article-content">{sections_html}
            </div>

            <div class="cta">{content["cta"]}</div>

            <div class="tags">
                {tags_html}
            </div>

            <div class="interaction">
                <div class="interaction-item">
                    <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>
                    <span>6150</span>
                </div>
                <div class="interaction-item">
                    <svg viewBox="0 0 24 24" fill="currentColor"><path d="M17.5 1.917a6.4 6.4 0 0 0-5.5 3.3a6.4 6.4 0 0 0-5.5-3.3A6.8 6.8 0 0 0 0 8.967c0 4.547 4.786 9.513 8.8 12.88a4.974 4.974 0 0 0 6.4 0C19.214 18.48 24 13.514 24 8.967A6.8 6.8 0 0 0 17.5 1.917z"/></svg>
                    <span>612</span>
                </div>
                <div class="interaction-item">
                    <svg viewBox="0 0 24 24" fill="currentColor"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/></svg>
                    <span>41</span>
                </div>
                <div class="interaction-item" style="margin-left: auto;">
                    <svg viewBox="0 0 24 24" fill="currentColor"><path d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.81 2.04.81 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.5-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92s2.92-1.31 2.92-2.92-1.31-2.92-2.92-2.92z"/></svg>
                </div>
            </div>
        </div>
    </div>
</body>
</html>'''


def main():
    """测试自动生成"""
    import os

    kb_path = os.path.join(
        os.path.dirname(__file__),
        "华为PC知识库(1)",
        "华为PC全板块深度知识库_v7"
    )

    generator = XHSAutoGenerator(kb_path)

    # 测试1: 颜值种草风格
    _safe_print("=" * 60)
    _safe_print("测试1: MateBook 14 - 颜值种草风格")
    _safe_print("=" * 60)
    generator.generate(
        product_name="HUAWEI MateBook 14",
        style="颜值种草",
        target_audience="学生党",
        output_path="auto_xhs_matebook14_颜值.html"
    )

    # 测试2: 性能实测风格
    _safe_print("\n" + "=" * 60)
    _safe_print("测试2: MateBook Pro - 性能实测风格")
    _safe_print("=" * 60)
    generator.generate(
        product_name="HUAWEI MateBook Pro",
        style="性能实测",
        target_audience="创作者",
        output_path="auto_xhs_matebook_pro_性能.html"
    )

    # 测试3: 学生党风格
    _safe_print("\n" + "=" * 60)
    _safe_print("测试3: MateBook 14 - 学生党风格")
    _safe_print("=" * 60)
    generator.generate(
        product_name="HUAWEI MateBook 14",
        style="学生党",
        target_audience="大学生",
        output_path="auto_xhs_matebook14_学生.html"
    )

    _safe_print("\n" + "=" * 60)
    _safe_print("✅ 全部测试完成！")
    _safe_print("=" * 60)


if __name__ == "__main__":
    main()
