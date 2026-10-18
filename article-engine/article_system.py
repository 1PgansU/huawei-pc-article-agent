"""
软文生成系统 - 整合生成、验证、优化
"""
import json
from typing import Dict, List, Optional
from article_generator import ArticleGenerator, ArticleContent
from content_validator import ContentValidator, ValidationReport


class ArticleSystem:
    """软文生成与验证系统"""

    def __init__(self, knowledge_base_path: str):
        """
        初始化系统

        Args:
            knowledge_base_path: 知识库根目录
        """
        self.generator = ArticleGenerator(knowledge_base_path)
        self.validator = ContentValidator(knowledge_base_path)
        self.max_retries = 3

    def generate_with_validation(self,
                                product_name: str,
                                scenario: str,
                                platform: str,
                                target_audience: str,
                                auto_fix: bool = True) -> Dict:
        """
        生成并验证软文

        Args:
            product_name: 产品型号
            scenario: 使用场景
            platform: 发布平台
            target_audience: 目标人群
            auto_fix: 是否自动修复问题

        Returns:
            结果字典
        """
        result = {
            "status": "unknown",
            "article": None,
            "validation_report": None,
            "iterations": []
        }

        for attempt in range(self.max_retries):
            # 生成软文
            article = self.generator.generate_article(
                product_name=product_name,
                scenario=scenario,
                platform=platform,
                target_audience=target_audience
            )

            # 准备验证用的内容和图片
            full_content = f"{article.selected_title}\n\n{article.opening}\n\n{article.body}"

            images = [
                {
                    "name": img.filename,
                    "source": "ima" if "ima" in img.source else "unknown",
                    "model": product_name,
                    "position": img.position,
                    "description": img.purpose
                }
                for img in article.images
            ]

            # 验证
            validation_report = self.validator.validate(
                product_name=product_name,
                content=full_content,
                images=images,
                platform=platform,
                knowledge_sources=article.knowledge_sources
            )

            # 记录迭代
            result["iterations"].append({
                "attempt": attempt + 1,
                "score": validation_report.final_score,
                "can_publish": validation_report.can_publish,
                "critical_issues": len(validation_report.compliance_check.critical_issues),
                "warnings": len(validation_report.compliance_check.warnings)
            })

            # 判断是否可以发布
            if validation_report.can_publish:
                result["status"] = "success"
                result["article"] = article
                result["validation_report"] = validation_report
                break

            # 如果不自动修复或已达最大重试次数，停止
            if not auto_fix or attempt == self.max_retries - 1:
                result["status"] = "failed"
                result["article"] = article
                result["validation_report"] = validation_report
                break

            # 否则，根据问题调整生成策略
            # 这里简化处理，实际应根据具体问题调整
            print(f"第{attempt + 1}次生成未通过验证，重新生成...")

        return result

    def export_result(self,
                     result: Dict,
                     output_dir: str = ".") -> Dict[str, str]:
        """
        导出结果文件

        Args:
            result: 生成结果
            output_dir: 输出目录

        Returns:
            生成的文件路径字典
        """
        import os
        from pathlib import Path

        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        files = {}

        article = result.get("article")
        validation_report = result.get("validation_report")

        if article:
            # 导出Markdown软文
            article_file = output_path / "article.md"
            with open(article_file, 'w', encoding='utf-8') as f:
                f.write(article.to_markdown())
            files["article_md"] = str(article_file)

            # 导出JSON
            article_json = output_path / "article.json"
            with open(article_json, 'w', encoding='utf-8') as f:
                json.dump(article.to_dict(), f, ensure_ascii=False, indent=2)
            files["article_json"] = str(article_json)

        if validation_report:
            # 导出验证报告
            report_file = output_path / "validation_report.md"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(validation_report.to_markdown())
            files["validation_md"] = str(report_file)

            # 导出JSON
            report_json = output_path / "validation_report.json"
            with open(report_json, 'w', encoding='utf-8') as f:
                json.dump(validation_report.to_dict(), f, ensure_ascii=False, indent=2)
            files["validation_json"] = str(report_json)

        # 导出汇总
        summary_file = output_path / "summary.md"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(self._generate_summary(result))
        files["summary"] = str(summary_file)

        return files

    def _generate_summary(self, result: Dict) -> str:
        """生成汇总报告"""
        lines = []

        lines.append("# 软文生成汇总报告\n\n")

        # 生成状态
        status_emoji = {
            "success": "✅",
            "failed": "❌",
            "unknown": "⚠️"
        }
        status = result.get("status", "unknown")
        lines.append(f"## 生成状态: {status_emoji[status]} {status.upper()}\n\n")

        # 迭代信息
        iterations = result.get("iterations", [])
        if iterations:
            lines.append("## 生成迭代\n\n")
            for it in iterations:
                lines.append(f"### 第{it['attempt']}次尝试\n")
                lines.append(f"- 得分: {it['score']:.1f}/100\n")
                lines.append(f"- 可发布: {'是' if it['can_publish'] else '否'}\n")
                lines.append(f"- 严重问题: {it['critical_issues']} 个\n")
                lines.append(f"- 警告: {it['warnings']} 个\n\n")

        # 最终结果
        article = result.get("article")
        validation_report = result.get("validation_report")

        if article:
            lines.append("## 文章信息\n\n")
            lines.append(f"- **产品**: {article.product_name}\n")
            lines.append(f"- **平台**: {article.platform}\n")
            lines.append(f"- **场景**: {article.scenario}\n")
            lines.append(f"- **人群**: {article.target_audience}\n")
            lines.append(f"- **标题**: {article.selected_title}\n")
            lines.append(f"- **字数**: {len(article.opening) + len(article.body)} 字\n")
            lines.append(f"- **配图**: {len(article.images)} 张\n\n")

        if validation_report:
            lines.append("## 验证结果\n\n")
            lines.append(f"- **综合得分**: {validation_report.final_score:.1f}/100\n")
            lines.append(f"- **可否发布**: {'是' if validation_report.can_publish else '否'}\n")
            lines.append(f"- **事实核验**: {'✓ 通过' if validation_report.fact_verification.is_valid else '✗ 未通过'}\n")
            lines.append(f"- **合规检查**: {'✓ 通过' if validation_report.compliance_check.is_compliant else '✗ 未通过'}\n\n")

            if validation_report.summary:
                lines.append("### 问题摘要\n\n")
                for item in validation_report.summary:
                    lines.append(f"- {item}\n")
                lines.append("\n")

            if validation_report.recommendations:
                lines.append("### 修改建议\n\n")
                for i, rec in enumerate(validation_report.recommendations, 1):
                    lines.append(f"{i}. {rec}\n")
                lines.append("\n")

        # 文件清单
        lines.append("## 生成文件\n\n")
        lines.append("- `article.md` - Markdown格式软文\n")
        lines.append("- `article.json` - JSON格式软文数据\n")
        lines.append("- `validation_report.md` - Markdown格式验证报告\n")
        lines.append("- `validation_report.json` - JSON格式验证报告\n")
        lines.append("- `summary.md` - 本汇总文件\n\n")

        return "".join(lines)


def main():
    """测试软文生成系统"""
    import os

    kb_path = os.path.join(os.path.dirname(__file__),
                           "华为PC知识库(1)",
                           "华为PC全板块深度知识库_v7")

    system = ArticleSystem(kb_path)

    print("=" * 60)
    print("软文生成系统测试")
    print("=" * 60)

    # 生成并验证
    result = system.generate_with_validation(
        product_name="HUAWEI MateBook 14",
        scenario="学生学习",
        platform="公众号",
        target_audience="大学生",
        auto_fix=False
    )

    print(f"\n生成状态: {result['status']}")
    print(f"迭代次数: {len(result['iterations'])}")

    if result['validation_report']:
        report = result['validation_report']
        print(f"综合得分: {report.final_score:.1f}/100")
        print(f"可否发布: {'是' if report.can_publish else '否'}")

    # 导出文件
    output_dir = "output_article"
    files = system.export_result(result, output_dir)

    print(f"\n文件已导出到: {output_dir}/")
    for key, path in files.items():
        print(f"  - {key}: {path}")

    # 显示汇总
    print("\n" + "=" * 60)
    print("汇总报告")
    print("=" * 60)
    print(system._generate_summary(result))


if __name__ == "__main__":
    main()
