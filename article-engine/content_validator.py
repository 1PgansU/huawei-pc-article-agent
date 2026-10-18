"""
内容验证器 - 整合事实核验和合规检查
"""
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from fact_verification import FactVerifier, VerificationResult
from compliance_checker import ComplianceChecker, ComplianceResult


@dataclass
class ValidationReport:
    """完整的验证报告"""
    overall_status: str  # pass, warning, fail
    fact_verification: VerificationResult
    compliance_check: ComplianceResult
    final_score: float
    can_publish: bool
    summary: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "overall_status": self.overall_status,
            "final_score": self.final_score,
            "can_publish": self.can_publish,
            "summary": self.summary,
            "recommendations": self.recommendations,
            "fact_verification": self.fact_verification.to_dict(),
            "compliance_check": self.compliance_check.to_dict()
        }

    def to_markdown(self) -> str:
        """生成Markdown格式的报告"""
        lines = ["# 内容验证报告\n"]

        # 总体状态
        status_emoji = {
            "pass": "✅",
            "warning": "⚠️",
            "fail": "❌"
        }
        lines.append(f"## 验证结果: {status_emoji[self.overall_status]} {self.overall_status.upper()}\n")
        lines.append(f"**综合得分**: {self.final_score:.1f}/100\n")
        lines.append(f"**是否可发布**: {'是' if self.can_publish else '否'}\n")

        # 摘要
        if self.summary:
            lines.append("\n## 问题摘要\n")
            for item in self.summary:
                lines.append(f"- {item}\n")

        # 事实核验部分
        lines.append("\n## 一、事实核验\n")

        if self.fact_verification.verified_facts:
            lines.append("### ✓ 已核验的事实\n")
            for fact in self.fact_verification.verified_facts:
                lines.append(f"- {fact}\n")

        if self.fact_verification.incorrect_facts:
            lines.append("\n### ✗ 错误的事实\n")
            for error in self.fact_verification.incorrect_facts:
                lines.append(f"- {error}\n")

        if self.fact_verification.unverified_claims:
            lines.append("\n### ? 无法核验的声明\n")
            for claim in self.fact_verification.unverified_claims:
                lines.append(f"- {claim}\n")

        if self.fact_verification.image_issues:
            lines.append("\n### ⚠ 图片问题\n")
            for issue in self.fact_verification.image_issues:
                lines.append(f"- {issue}\n")

        if self.fact_verification.warnings:
            lines.append("\n### ⚠ 警告\n")
            for warning in self.fact_verification.warnings:
                lines.append(f"- {warning}\n")

        # 合规检查部分
        lines.append(f"\n## 二、合规检查\n")
        lines.append(f"**合规分数**: {self.compliance_check.score:.1f}/100\n")

        if self.compliance_check.critical_issues:
            lines.append("\n### ❌ 严重问题（必须修改）\n")
            for issue in self.compliance_check.critical_issues:
                lines.append(f"#### {issue.category}\n")
                lines.append(f"- **问题**: {issue.description}\n")
                lines.append(f"- **位置**: {issue.location}\n")
                lines.append(f"- **建议**: {issue.suggestion}\n\n")

        if self.compliance_check.warnings:
            lines.append("\n### ⚠️ 警告（建议修改）\n")
            for issue in self.compliance_check.warnings:
                lines.append(f"#### {issue.category}\n")
                lines.append(f"- **问题**: {issue.description}\n")
                lines.append(f"- **位置**: {issue.location}\n")
                lines.append(f"- **建议**: {issue.suggestion}\n\n")

        if self.compliance_check.info:
            lines.append("\n### ℹ️ 提示信息\n")
            for issue in self.compliance_check.info:
                lines.append(f"- [{issue.category}] {issue.description}\n")

        # 修改建议
        if self.recommendations:
            lines.append("\n## 三、修改建议\n")
            for i, rec in enumerate(self.recommendations, 1):
                lines.append(f"{i}. {rec}\n")

        return "".join(lines)


class ContentValidator:
    """内容验证器 - 整合事实核验和合规检查"""

    def __init__(self, knowledge_base_path: str):
        """
        初始化内容验证器

        Args:
            knowledge_base_path: 知识库根目录路径
        """
        self.fact_verifier = FactVerifier(knowledge_base_path)
        self.compliance_checker = ComplianceChecker()

    def validate(self,
                product_name: str,
                content: str,
                images: Optional[List[Dict]] = None,
                platform: str = "通用",
                knowledge_sources: Optional[List[str]] = None) -> ValidationReport:
        """
        执行完整的内容验证

        Args:
            product_name: 产品型号
            content: 软文内容
            images: 图片列表 [{"name": "xxx.jpg", "source": "ima", "model": "...", "position": "..."}]
            platform: 发布平台
            knowledge_sources: 知识库来源列表（用于记录）

        Returns:
            验证报告
        """
        # 1. 事实核验
        fact_result = self.fact_verifier.verify_content(product_name, content, images)

        # 2. 合规检查
        compliance_result = self.compliance_checker.check(content, platform)

        # 3. 图片合规检查
        if images:
            image_compliance = self.compliance_checker.check_image_compliance(images)
            for issue in image_compliance:
                if issue.severity == "critical":
                    compliance_result.critical_issues.append(issue)
                elif issue.severity == "warning":
                    compliance_result.warnings.append(issue)

        # 4. 计算综合得分
        fact_score = 100.0 if fact_result.is_valid else 60.0
        fact_score -= len(fact_result.warnings) * 5
        fact_score -= len(fact_result.incorrect_facts) * 15
        fact_score -= len(fact_result.image_issues) * 10
        fact_score = max(0, fact_score)

        final_score = (fact_score * 0.5 + compliance_result.score * 0.5)

        # 5. 生成摘要
        summary = []
        if not fact_result.is_valid:
            summary.append(f"事实核验未通过：发现 {len(fact_result.incorrect_facts)} 个错误事实")
        if fact_result.image_issues:
            summary.append(f"图片问题：{len(fact_result.image_issues)} 个")
        if not compliance_result.is_compliant:
            summary.append(f"合规检查未通过：发现 {len(compliance_result.critical_issues)} 个严重问题")
        if compliance_result.warnings:
            summary.append(f"合规警告：{len(compliance_result.warnings)} 个")

        # 6. 判断整体状态
        if not fact_result.is_valid or not compliance_result.is_compliant:
            overall_status = "fail"
            can_publish = False
        elif fact_result.warnings or compliance_result.warnings:
            overall_status = "warning"
            can_publish = True  # 有警告但可以发布
        else:
            overall_status = "pass"
            can_publish = True

        # 7. 生成修改建议
        recommendations = []

        # 事实问题的建议
        if fact_result.incorrect_facts:
            recommendations.append("核对产品型号、参数等事实信息，确保与知识库一致")
        if fact_result.unverified_claims:
            recommendations.append("删除或修改无法核验的声明，或补充来源依据")
        if fact_result.image_issues:
            recommendations.append("更换为ima知识库中的官方图片，确保型号匹配")

        # 合规问题的建议
        if compliance_result.critical_issues:
            critical_types = set(issue.category for issue in compliance_result.critical_issues)
            for ct in critical_types:
                if ct == "绝对化用语":
                    recommendations.append("删除或修改绝对化表述，使用相对描述或添加限定条件")
                elif ct in ["竞品对比", "竞品贬低"]:
                    recommendations.append("删除未经证实的竞品对比，或提供权威测试依据")
                elif ct == "价格标注":
                    recommendations.append("核验价格信息来源，标注官方渠道和日期")
                elif ct == "夸大承诺":
                    recommendations.append("删除或限定夸大性承诺，说明具体条件")
                elif ct == "伪造体验":
                    recommendations.append("使用客观描述替代个人体验，或提供真实使用凭证")

        if compliance_result.warnings:
            recommendations.append("检查警告项，考虑优化表述以提高内容质量")

        # 知识来源建议
        if not knowledge_sources:
            recommendations.append("补充知识库来源记录，确保所有事实可追溯")

        # 创建报告
        report = ValidationReport(
            overall_status=overall_status,
            fact_verification=fact_result,
            compliance_check=compliance_result,
            final_score=final_score,
            can_publish=can_publish,
            summary=summary,
            recommendations=recommendations
        )

        return report

    def quick_check(self, content: str) -> Dict:
        """
        快速检查（仅合规，不核验事实）

        Args:
            content: 待检查内容

        Returns:
            简化的检查结果
        """
        result = self.compliance_checker.check(content)

        return {
            "is_compliant": result.is_compliant,
            "score": result.score,
            "critical_count": len(result.critical_issues),
            "warning_count": len(result.warnings),
            "issues": [
                {
                    "severity": issue.severity,
                    "category": issue.category,
                    "description": issue.description,
                    "location": issue.location
                }
                for issue in (result.critical_issues + result.warnings)
            ]
        }


def main():
    """测试完整的验证流程"""
    import os

    # 知识库路径
    kb_path = os.path.join(os.path.dirname(__file__), "华为PC知识库(1)", "华为PC全板块深度知识库_v7")

    if not os.path.exists(kb_path):
        print(f"错误：知识库路径不存在: {kb_path}")
        return

    # 创建验证器
    validator = ContentValidator(kb_path)

    # 测试内容
    test_content = """
    HUAWEI MateBook 14（鸿蒙版）：开学季最佳选择

    新学期开始，选择一台适合学习的笔记本电脑至关重要。华为MateBook 14（鸿蒙版）
    搭载麒麟 X90 处理器，配备24GB内存和512GB存储，14.2英寸OLED屏幕，分辨率
    2880×1920，重量约1.33kg，续航约12小时（典型办公场景测试）。

    这款笔记本采用HarmonyOS 6操作系统，支持与华为手机、平板的无缝协同（需登录
    同一华为账号）。3:2屏幕比例更适合文档编辑和网页浏览，HDMI接口和两个USB-A
    接口方便连接投影仪和U盘。

    适合需要移动办公、重视鸿蒙生态协同的大学生。购买前建议确认必用软件对
    HarmonyOS的支持情况。

    【图片】
    - matebook14_front.jpg（来源：ima知识库，产品正面图，建议插入标题下方）
    - matebook14_screen.jpg（来源：ima知识库，屏幕显示效果，建议插入屏幕介绍段落）
    """

    test_images = [
        {
            "name": "matebook14_front.jpg",
            "source": "ima",
            "model": "HUAWEI MateBook 14",
            "position": "标题下方",
            "description": "产品正面图"
        },
        {
            "name": "matebook14_screen.jpg",
            "source": "ima",
            "model": "HUAWEI MateBook 14",
            "position": "屏幕介绍段落",
            "description": "屏幕显示效果"
        }
    ]

    # 执行验证
    print("正在执行内容验证...\n")
    report = validator.validate(
        product_name="HUAWEI MateBook 14",
        content=test_content,
        images=test_images,
        platform="公众号",
        knowledge_sources=["P1-产品参数库/01-鸿蒙电脑/HUAWEI MateBook 14"]
    )

    # 输出Markdown报告
    print(report.to_markdown())

    # 保存JSON报告
    output_file = "validation_report.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
    print(f"\n详细报告已保存至: {output_file}")

    # 保存Markdown报告
    md_file = "validation_report.md"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(report.to_markdown())
    print(f"Markdown报告已保存至: {md_file}")


if __name__ == "__main__":
    main()
