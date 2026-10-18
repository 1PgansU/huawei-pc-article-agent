# 事实核验与合规检查模块 - 使用说明

## 目录结构

```
zhekesong/
├── fact_verification.py      # 事实核验模块
├── compliance_checker.py     # 合规检查模块
├── content_validator.py      # 内容验证器（整合模块）
├── README_验证模块.md         # 本说明文档
└── 华为PC知识库(1)/          # 知识库目录
```

## 功能概述

### 1. 事实核验模块 (fact_verification.py)

**核心功能**：
- 检查产品型号是否存在于知识库
- 核验产品参数（处理器、内存、存储、屏幕、重量等）
- 检测型号混用
- 验证图片来源和型号匹配
- 识别缺少限定条件的声明

**主要类**：
- `FactVerifier`: 事实核验器
- `VerificationResult`: 核验结果数据类

### 2. 合规检查模块 (compliance_checker.py)

**核心功能**：
- 识别绝对化用语（最好、第一、唯一等）
- 检测虚假宣传风险（虚构对比、销量、奖项等）
- 检查价格相关风险（价格标注、优惠信息等）
- 发现夸大承诺
- 检测竞品贬低
- 平台特定合规检查（公众号、小红书、朋友圈）

**主要类**：
- `ComplianceChecker`: 合规检查器
- `ComplianceResult`: 合规检查结果数据类
- `ComplianceIssue`: 合规问题数据类

### 3. 内容验证器 (content_validator.py)

**核心功能**：
- 整合事实核验和合规检查
- 计算综合得分
- 生成完整验证报告
- 输出Markdown和JSON格式报告

**主要类**：
- `ContentValidator`: 内容验证器
- `ValidationReport`: 验证报告数据类

## 安装依赖

```bash
# 基础依赖
pip install dataclasses  # Python 3.7+ 内置
```

无需额外依赖，使用Python标准库即可运行。

## 快速开始

### 示例1：完整验证流程

```python
from content_validator import ContentValidator

# 初始化验证器
kb_path = r"D:\zhekesong\华为PC知识库(1)\华为PC全板块深度知识库_v7"
validator = ContentValidator(kb_path)

# 准备要验证的内容
content = """
HUAWEI MateBook 14（鸿蒙版）搭载麒麟 X90 处理器，
配备24GB内存和512GB存储，14.2英寸OLED屏幕。
"""

# 准备图片信息
images = [
    {
        "name": "product.jpg",
        "source": "ima",
        "model": "HUAWEI MateBook 14",
        "position": "标题下方",
        "description": "产品图"
    }
]

# 执行验证
report = validator.validate(
    product_name="HUAWEI MateBook 14",
    content=content,
    images=images,
    platform="公众号"
)

# 查看结果
print(f"验证状态: {report.overall_status}")
print(f"综合得分: {report.final_score}/100")
print(f"可否发布: {report.can_publish}")

# 输出详细报告
print(report.to_markdown())
```

### 示例2：仅检查合规性（快速检查）

```python
from content_validator import ContentValidator

validator = ContentValidator(kb_path)

content = "这是市场上最好的笔记本，性能绝对一流！"

result = validator.quick_check(content)

print(f"合规: {result['is_compliant']}")
print(f"分数: {result['score']}")
print(f"严重问题: {result['critical_count']} 个")
print(f"警告: {result['warning_count']} 个")
```

### 示例3：单独使用事实核验

```python
from fact_verification import FactVerifier

verifier = FactVerifier(kb_path)

content = "配备32GB内存和1TB存储，重量约1.5kg"

result = verifier.verify_content(
    product_name="HUAWEI MateBook 14",
    content=content
)

print(f"核验通过: {result.is_valid}")
print(f"已核验事实: {result.verified_facts}")
print(f"警告: {result.warnings}")
```

### 示例4：单独使用合规检查

```python
from compliance_checker import ComplianceChecker

checker = ComplianceChecker()

content = "这是最好的笔记本，比苹果强50%！"

result = checker.check(content, platform="小红书")

print(f"合规: {result.is_compliant}")
print(f"分数: {result.score}/100")

for issue in result.critical_issues:
    print(f"[{issue.category}] {issue.description}")
    print(f"  位置: {issue.location}")
    print(f"  建议: {issue.suggestion}")
```

## 验证报告说明

### 报告结构

```python
ValidationReport(
    overall_status="pass" | "warning" | "fail",
    final_score=85.0,  # 0-100分
    can_publish=True,  # 是否可发布
    summary=[...],     # 问题摘要
    recommendations=[...],  # 修改建议
    fact_verification=VerificationResult(...),
    compliance_check=ComplianceResult(...)
)
```

### 状态说明

- **pass**: 无严重问题，可直接发布
- **warning**: 有警告但可发布，建议优化
- **fail**: 有严重问题，不可发布，必须修改

### 评分规则

**事实核验评分**：
- 基础分：100分（有效）或 60分（无效）
- 每个警告：-5分
- 每个错误事实：-15分
- 每个图片问题：-10分

**合规检查评分**：
- 基础分：100分
- 每个严重问题：-20分
- 每个警告：-5分

**综合得分**：
```
final_score = fact_score * 0.5 + compliance_score * 0.5
```

## 核验规则详解

### 事实核验规则

1. **型号匹配**：检查提及的型号是否与目标产品一致
2. **参数核验**：对比声明的参数与知识库中的事实
3. **限定条件**：检查性能、续航等声明是否有测试条件
4. **图片来源**：确保图片来自ima知识库
5. **图片型号**：确保图片型号与产品匹配

### 合规检查规则

#### 绝对化用语（警告）
- 最好、最强、最佳、最优
- 第一、NO.1、排名第一
- 唯一、独一无二
- 绝对、必然、一定
- 完全、100%
- 所有人、任何人
- 永久、永远

#### 虚假宣传（严重）
- 未经证实的竞品对比
- 虚构的权威认证
- 无来源的销量声明
- 伪造的用户评价
- 虚构的奖项

#### 价格风险（视情况）
- 无来源的价格标注（严重）
- 有来源的价格标注（警告）
- 优惠活动需注明时间和条件
- 免费承诺需说明具体内容

#### 夸大承诺（严重）
- 无条件退款承诺
- 永久/终身服务
- 无限制使用
- 任意退换

#### 竞品贬低（严重）
- 在提及竞品的同时使用贬低性词汇

#### 平台特定规则

**小红书**：
- 不得伪造个人体验（严重）
- 话题标签建议≤8个（警告）

**公众号**：
- 避免利益诱导分享/关注（警告）

**朋友圈**：
- 建议字数≤200字（提示）

## API参考

### ContentValidator

```python
class ContentValidator:
    def __init__(self, knowledge_base_path: str)
    
    def validate(
        self,
        product_name: str,
        content: str,
        images: Optional[List[Dict]] = None,
        platform: str = "通用",
        knowledge_sources: Optional[List[str]] = None
    ) -> ValidationReport
    
    def quick_check(self, content: str) -> Dict
```

### FactVerifier

```python
class FactVerifier:
    def __init__(self, knowledge_base_path: str)
    
    def verify_content(
        self,
        product_name: str,
        content: str,
        images: List[Dict] = None
    ) -> VerificationResult
    
    def verify_model_consistency(self, content: str) -> List[str]
```

### ComplianceChecker

```python
class ComplianceChecker:
    def __init__(self)
    
    def check(
        self,
        content: str,
        platform: str = "通用"
    ) -> ComplianceResult
    
    def check_image_compliance(
        self,
        images: List[Dict]
    ) -> List[ComplianceIssue]
```

## 图片数据格式

```python
{
    "name": "产品图片文件名",
    "source": "ima",  # 必须是ima
    "model": "HUAWEI MateBook 14",  # 产品型号
    "position": "标题下方",  # 建议插入位置
    "description": "产品正面图"  # 图片说明
}
```

## 集成到Agent系统

### 在生成流程中调用

```python
# 1. Agent生成软文内容
generated_content = agent.generate_article(...)

# 2. 执行验证
validator = ContentValidator(kb_path)
report = validator.validate(
    product_name=product_name,
    content=generated_content,
    images=generated_images,
    platform=target_platform
)

# 3. 根据验证结果决定是否重新生成
if not report.can_publish:
    # 提取问题并重新生成
    issues = report.summary
    regenerated_content = agent.regenerate_with_fixes(
        original=generated_content,
        issues=issues,
        recommendations=report.recommendations
    )
    
    # 再次验证
    report = validator.validate(...)

# 4. 输出最终内容和验证报告
return {
    "content": generated_content,
    "validation_report": report.to_dict(),
    "can_publish": report.can_publish
}
```

### 流程建议

```
用户输入
  ↓
场景理解
  ↓
知识检索
  ↓
内容生成
  ↓
[事实核验] ← 本模块
  ↓
[合规检查] ← 本模块
  ↓
验证不通过？ → 重新生成（最多3次）
  ↓ 通过
输出内容 + 验证报告
```

## 测试

运行各模块的测试：

```bash
# 测试事实核验
python fact_verification.py

# 测试合规检查
python compliance_checker.py

# 测试完整验证
python content_validator.py
```

## 注意事项

1. **知识库路径**：确保知识库路径正确，包含完整的P1-产品参数库
2. **性能优化**：首次加载知识库较慢，建议缓存FactVerifier实例
3. **规则定制**：可以根据实际需求修改compliance_checker.py中的规则
4. **图片核验**：目前仅检查来源和型号，不检查图片实际内容
5. **持续更新**：随着知识库更新，需要重新初始化验证器

## 扩展功能建议

1. **增强事实提取**：使用NLP模型提取更复杂的产品声明
2. **图像识别**：集成图像识别API验证图片内容
3. **知识图谱**：构建产品知识图谱提高核验准确性
4. **学习优化**：收集验证结果，优化规则权重
5. **批量验证**：支持批量验证多篇内容

## 常见问题

**Q: 为什么有些事实无法核验？**
A: 可能是知识库中没有相关数据，或提取模式无法匹配。建议补充知识库或优化提取规则。

**Q: 合规分数如何提高？**
A: 删除绝对化用语，添加限定条件，确保所有声明有来源依据。

**Q: 图片问题如何解决？**
A: 只使用ima知识库中的图片，确保图片型号与产品型号完全匹配。

**Q: 验证速度慢怎么办？**
A: 复用validator实例，避免重复加载知识库。考虑只在关键节点调用完整验证。

## 更新日志

- **v1.0** (2026-10-18)
  - 初始版本
  - 实现事实核验基础功能
  - 实现合规检查基础功能
  - 提供完整的验证报告

## 联系与支持

如有问题或建议，请查看赛题手册或咨询比赛组委会。
