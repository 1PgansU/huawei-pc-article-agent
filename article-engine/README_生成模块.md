# 图文软文生成模块 - 使用说明

## 📦 模块概述

本模块提供华为PC营销软文的自动生成功能，包括：

1. **知识检索** - 从知识库提取产品信息、卖点、场景
2. **标题生成** - 生成3种风格的标题选项
3. **正文生成** - 生成开头、主体、CTA
4. **配图方案** - 生成图片使用方案
5. **自动验证** - 整合事实核验和合规检查

---

## 🗂️ 文件结构

```
zhekesong/
├── knowledge_retriever.py    # 知识检索器
├── article_generator.py      # 软文生成器
├── article_system.py          # 整合系统（生成+验证）
├── fact_verification.py       # 事实核验模块
├── compliance_checker.py      # 合规检查模块
├── content_validator.py       # 内容验证器
├── README_生成模块.md         # 本文档
└── 华为PC知识库(1)/           # 知识库目录
```

---

## 🚀 快速开始

### 1. 基础生成

```python
from article_generator import ArticleGenerator

# 初始化生成器
kb_path = "华为PC知识库(1)/华为PC全板块深度知识库_v7"
generator = ArticleGenerator(kb_path)

# 生成软文
article = generator.generate_article(
    product_name="HUAWEI MateBook 14",
    scenario="学生学习",
    platform="公众号",
    target_audience="大学生"
)

# 查看标题选项
for i, option in enumerate(article.title_options, 1):
    print(f"{i}. [{option.style}] {option.title}")
    print(f"   {option.reason}\n")

# 输出Markdown
print(article.to_markdown())
```

### 2. 生成+验证（推荐）

```python
from article_system import ArticleSystem

# 初始化系统
system = ArticleSystem(kb_path)

# 生成并验证
result = system.generate_with_validation(
    product_name="HUAWEI MateBook 14",
    scenario="学生学习",
    platform="公众号",
    target_audience="大学生",
    auto_fix=False  # 是否自动重试修复
)

# 查看结果
print(f"状态: {result['status']}")
print(f"得分: {result['validation_report'].final_score}/100")
print(f"可发布: {result['validation_report'].can_publish}")

# 导出文件
files = system.export_result(result, "output")
# 生成5个文件: article.md, article.json, 
#             validation_report.md, validation_report.json, summary.md
```

---

## 📝 生成流程

```
输入参数
  ↓
知识检索（产品事实、卖点、场景）
  ↓
标题生成（3种风格）
  ↓
开头生成（人物+任务+阻碍）
  ↓
正文生成（配置、屏幕、场景、购买建议）
  ↓
CTA生成（行动引导）
  ↓
配图方案（产品图、场景图）
  ↓
知识来源记录
  ↓
自动验证（事实+合规）
  ↓
导出成稿
```

---

## 🎨 标题生成策略

系统自动生成3种风格的标题：

### 1. 场景式
- 特点：具体人物+任务
- 示例：`HUAWEI MateBook 14：开学季选笔记本，这几点要注意`
- 适用：吸引目标人群

### 2. 利益式
- 特点：解决问题+价值点
- 示例：`华为生态用户换新本：HUAWEI MateBook 14协同体验如何？`
- 适用：筛选精准用户

### 3. 陈述式
- 特点：包含关键参数
- 示例：`HUAWEI MateBook 14：14.2英寸轻薄本选购要点`
- 适用：搜索流量

系统会根据场景和人群自动调整标题内容。

---

## ✍️ 正文结构

### 开头段落（3-4句）
- 点出目标人群
- 说明核心任务
- 引出产品定位

### 主体段落

#### 1. 配置方面
- 操作系统（限定条件）
- 处理器
- 内存和存储
- 软件兼容性提醒

#### 2. 屏幕与便携性
- 屏幕尺寸和类型
- 分辨率和比例
- 重量和厚度

#### 3. 适用场景
- 适合的用户
- 不适合的情况
- 针对人群的特别说明

#### 4. 购买建议
- 到店体验要点
- 需要确认的事项
- 版本差异提醒

### CTA（行动引导）
根据平台调整：
- **公众号**：引导访问官网或到店
- **小红书**：互动评论、收藏
- **朋友圈**：私聊咨询

---

## 🖼️ 配图方案

### 标准配图

每篇软文自动规划3张图：

1. **产品主图**
   - 位置：标题下方
   - 用途：展示产品整体外观
   - 来源：ima知识库/产品正面图

2. **屏幕展示图**
   - 位置：屏幕段落
   - 用途：展示屏幕显示效果
   - 来源：ima知识库/屏幕显示

3. **功能图**（根据产品特性）
   - 鸿蒙系统：多屏协同示意图
   - 轻薄本：便携使用场景
   - 来源：ima知识库/对应素材

### 配图信息

每张图包含：
```python
{
    "filename": "huawei_matebook_14_front.jpg",
    "source": "ima知识库/P6-营销素材库/04-图片/...",
    "position": "标题下方",
    "purpose": "展示产品整体外观",
    "caption": "HUAWEI MateBook 14",
    "limitation": "需使用ima知识库中的官方图片"
}
```

---

## 🔍 知识检索

### 支持的数据源

- **P1-产品参数库**: 产品规格、配置
- **P2-卖点话术库**: 产品卖点、话术
- **P6-营销素材库**: 图片、模板、案例
- **P8-客户场景库**: 使用场景、人群

### 检索方法

```python
from knowledge_retriever import KnowledgeRetriever

retriever = KnowledgeRetriever(kb_path)

# 获取产品事实
facts = retriever.get_product_facts("HUAWEI MateBook 14")
print(facts['os'])          # HarmonyOS 6
print(facts['screen_size']) # 14.2 英寸
print(facts['weight'])      # 约 1.33 kg

# 获取卖点
selling_points = retriever.get_selling_points(
    "HUAWEI MateBook 14", 
    "学生学习"
)

# 搜索产品
results = retriever.search_product("MateBook 14")
# ['HUAWEI MateBook 14', 'MateBook 14 酷睿 Ultra']
```

---

## 🎯 平台适配

### 公众号
- 标题：60字内，陈述式为主
- 正文：800-1200字，段落清晰
- CTA：引导官网或到店

### 小红书
- 标题：口语化，带emoji
- 正文：600-800字，分段短
- CTA：互动引导（评论、收藏）

### 朋友圈
- 标题：简短有力
- 正文：200-300字
- CTA：私聊咨询

---

## 📊 生成示例

### 输入
```python
product_name = "HUAWEI MateBook 14"
scenario = "学生学习"
platform = "公众号"
target_audience = "大学生"
```

### 输出

#### 标题（3个选项）
1. 【场景式】HUAWEI MateBook 14：开学季选笔记本，这几点要注意
2. 【利益式】华为生态用户换新本：HUAWEI MateBook 14协同体验如何？
3. 【陈述式】HUAWEI MateBook 14：14.2英寸轻薄本选购要点

#### 正文结构
- 开头：3句话点出人群、任务、产品
- 配置段：系统+处理器+内存+兼容性提醒
- 屏幕段：尺寸+类型+比例+重量
- 场景段：适合/不适合+专业建议
- 购买段：体验要点+确认事项

#### 配图方案
- 图1：产品正面图（标题下）
- 图2：屏幕显示图（屏幕段）
- 图3：多屏协同图（配置段）

#### 验证结果
- 事实核验：✓ 通过
- 合规检查：✓ 通过
- 综合得分：85/100
- 可否发布：是

---

## 🛠️ API 参考

### ArticleGenerator

```python
class ArticleGenerator:
    def __init__(self, knowledge_base_path: str)
    
    def generate_titles(
        self,
        product_name: str,
        scenario: str,
        platform: str,
        target_audience: str
    ) -> List[TitleOption]
    
    def generate_opening(
        self,
        product_name: str,
        scenario: str,
        target_audience: str,
        platform: str
    ) -> str
    
    def generate_body(
        self,
        product_name: str,
        scenario: str,
        platform: str
    ) -> Tuple[str, List[str]]
    
    def generate_cta(
        self,
        platform: str,
        scenario: str
    ) -> str
    
    def generate_images(
        self,
        product_name: str,
        platform: str
    ) -> List[ImagePlan]
    
    def generate_article(
        self,
        product_name: str,
        scenario: str,
        platform: str,
        target_audience: str
    ) -> ArticleContent
```

### ArticleSystem

```python
class ArticleSystem:
    def __init__(self, knowledge_base_path: str)
    
    def generate_with_validation(
        self,
        product_name: str,
        scenario: str,
        platform: str,
        target_audience: str,
        auto_fix: bool = True
    ) -> Dict
    
    def export_result(
        self,
        result: Dict,
        output_dir: str = "."
    ) -> Dict[str, str]
```

### KnowledgeRetriever

```python
class KnowledgeRetriever:
    def __init__(self, knowledge_base_path: str)
    
    def get_product_facts(
        self,
        product_name: str
    ) -> Optional[Dict]
    
    def get_selling_points(
        self,
        product_name: str,
        scenario: str = ""
    ) -> List[Dict]
    
    def get_available_products(self) -> List[str]
    
    def search_product(self, query: str) -> List[str]
```

---

## ⚙️ 配置选项

### 场景类型
- `学生学习` - 大学生、开学季
- `移动办公` - 职场人士、出差
- `内容创作` - 创作者、剪辑
- `商务管理` - 企业管理
- `企业IT` - 企业采购

### 平台类型
- `公众号` - 微信公众号
- `小红书` - 小红书笔记
- `知乎` - 知乎问答
- `朋友圈` - 微信朋友圈
- `门店` - 门店海报

### 目标人群
- `大学生` - 在校大学生
- `职场人士` - 上班族
- `创作者` - 内容创作者
- `企业用户` - 企业采购
- `换机用户` - 老用户换新

---

## 🎯 使用技巧

### 1. 选择合适的场景
根据产品特性和目标人群选择场景：
- HarmonyOS产品 → 强调生态协同
- 轻薄本 → 强调便携和续航
- 高性能本 → 强调创作和性能

### 2. 平台风格适配
不同平台有不同的阅读习惯：
- 公众号：深度、完整
- 小红书：轻松、互动
- 朋友圈：简洁、直接

### 3. 人群定位精准
明确目标人群，避免泛泛而谈：
- ✅ 好：文科专业大学生
- ❌ 差：所有人

### 4. 保留限定条件
所有声明都要有限定：
- ✅ 续航约12小时（典型办公场景）
- ❌ 续航12小时

### 5. 使用官方图片
只使用ima知识库中的图片：
- ✅ ima知识库/P6-营销素材库/...
- ❌ 网络随意搜索的图片

---

## 🧪 测试命令

```bash
# 测试知识检索
python knowledge_retriever.py

# 测试软文生成
python article_generator.py

# 测试完整系统
python article_system.py
```

---

## 📋 输出文件

### 生成5个文件

1. **article.md** - Markdown格式软文
   - 包含：场景判断、知识依据、标题方案、正文、配图方案

2. **article.json** - JSON格式数据
   - 结构化数据，方便程序处理

3. **validation_report.md** - 验证报告
   - 事实核验结果
   - 合规检查结果
   - 修改建议

4. **validation_report.json** - 验证数据
   - JSON格式验证结果

5. **summary.md** - 汇总报告
   - 生成状态
   - 迭代信息
   - 文件清单

---

## 🔧 进阶使用

### 批量生成

```python
from article_system import ArticleSystem

system = ArticleSystem(kb_path)

# 定义任务列表
tasks = [
    {"product": "HUAWEI MateBook 14", "scenario": "学生学习", "platform": "公众号"},
    {"product": "HUAWEI MateBook Pro", "scenario": "内容创作", "platform": "小红书"},
    {"product": "MateBook 14 酷睿 Ultra", "scenario": "商务办公", "platform": "知乎"},
]

# 批量生成
for i, task in enumerate(tasks, 1):
    result = system.generate_with_validation(
        product_name=task["product"],
        scenario=task["scenario"],
        platform=task["platform"],
        target_audience="目标用户"
    )
    
    output_dir = f"output_{i}"
    system.export_result(result, output_dir)
    print(f"任务{i}完成，输出到 {output_dir}/")
```

### 自定义标题

```python
# 生成文章
article = generator.generate_article(...)

# 查看标题选项
for option in article.title_options:
    print(f"[{option.style}] {option.title}")

# 手动选择标题
article.selected_title = article.title_options[1].title

# 导出
with open("article.md", 'w', encoding='utf-8') as f:
    f.write(article.to_markdown())
```

---

## 📚 相关文档

- **README_验证模块.md** - 事实核验和合规检查详解
- **交付说明.md** - 整体功能交付说明
- **图文软文输出规范.md** - 知识库中的输出规范

---

## ⚠️ 注意事项

1. **知识库路径**：确保知识库路径正确
2. **产品型号**：必须是知识库中存在的型号
3. **图片使用**：只使用ima知识库中的官方图片
4. **限定条件**：保留所有限定条件和测试说明
5. **人工审核**：生成后仍需人工最终审核

---

## 🎉 总结

已完成功能：

✅ **知识检索** - 自动提取产品事实  
✅ **标题生成** - 3种风格自适应  
✅ **正文生成** - 结构化内容生成  
✅ **配图方案** - 智能图片规划  
✅ **自动验证** - 事实+合规双重检查  
✅ **多格式导出** - Markdown+JSON  

**下一步建议**：
1. 集成到你的完整工作流
2. 根据实际效果调整生成模板
3. 补充更多产品的卖点库
4. 优化不同平台的文案风格

有问题随时问我！
