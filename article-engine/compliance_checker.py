"""
合规检查模块
识别虚假宣传、价格误导、绝对化用语等营销合规风险
"""
import re
from typing import List, Dict, Tuple
from dataclasses import dataclass, field


@dataclass
class ComplianceIssue:
    """合规问题"""
    category: str  # 问题类别
    severity: str  # 严重程度: critical, warning, info
    description: str  # 问题描述
    location: str  # 问题位置/上下文
    suggestion: str = ""  # 修改建议


@dataclass
class ComplianceResult:
    """合规检查结果"""
    is_compliant: bool
    critical_issues: List[ComplianceIssue] = field(default_factory=list)  # 严重问题
    warnings: List[ComplianceIssue] = field(default_factory=list)  # 警告
    info: List[ComplianceIssue] = field(default_factory=list)  # 提示信息
    score: float = 100.0  # 合规分数

    def to_dict(self) -> Dict:
        return {
            "is_compliant": self.is_compliant,
            "score": self.score,
            "critical_issues": [
                {
                    "category": issue.category,
                    "severity": issue.severity,
                    "description": issue.description,
                    "location": issue.location,
                    "suggestion": issue.suggestion
                }
                for issue in self.critical_issues
            ],
            "warnings": [
                {
                    "category": issue.category,
                    "severity": issue.severity,
                    "description": issue.description,
                    "location": issue.location,
                    "suggestion": issue.suggestion
                }
                for issue in self.warnings
            ],
            "info": [
                {
                    "category": issue.category,
                    "severity": issue.severity,
                    "description": issue.description,
                    "location": issue.location
                }
                for issue in self.info
            ]
        }


class ComplianceChecker:
    """合规检查器"""

    def __init__(self):
        # 绝对化用语黑名单
        self.absolute_terms = {
            "最": ["最好", "最强", "最佳", "最优", "最快", "最高", "最低", "最大", "最小", "最新"],
            "第一": ["第一", "第一名", "NO.1", "No.1", "排名第一"],
            "唯一": ["唯一", "独一无二", "绝无仅有"],
            "绝对": ["绝对", "必然", "一定", "肯定"],
            "完全": ["完全", "彻底", "100%", "百分百", "百分之百"],
            "所有": ["所有人", "任何人", "每个人", "全部"],
            "永久": ["永久", "永远", "终身"]
        }

        # 虚假宣传模式
        self.false_claim_patterns = [
            # 虚构对比
            (r'(?:比|超过|战胜).*?(?:苹果|MacBook|联想|戴尔|惠普|ThinkPad).*?(?:[0-9]+%|倍|性能)',
             "竞品对比", "与竞品的性能对比需要有权威测试依据"),

            # 虚构权威
            (r'(?:权威|专家|机构|评测|排行榜).*?(?:认证|评选|推荐|第一)',
             "权威背书", "需要注明具体机构名称和评选时间"),

            # 虚构销量
            (r'(?:销量|销售|热销|畅销|爆款).*?(?:第一|冠军|领先|突破.*?万)',
             "销量声明", "销量数据需要有官方来源"),

            # 虚构用户
            (r'(?:用户|消费者|客户).*?都.*?(?:说|认为|评价|满意)',
             "用户评价", "用户评价需要真实且可溯源"),

            # 虚构奖项
            (r'(?:获得|荣获|斩获).*?(?:奖|大奖|金奖)',
             "奖项声明", "奖项需要注明颁发机构和时间"),
        ]

        # 价格相关风险模式
        self.price_risk_patterns = [
            (r'[¥￥]\s*\d+', "价格标注", "价格信息需要有官方来源依据"),
            (r'(?:优惠|折扣|降价|立减|直降)\s*[¥￥]?\d+', "优惠信息", "优惠活动需要注明时间和条件"),
            (r'(?:免费|赠送|白送)', "免费承诺", "需要说明免费的具体内容和条件"),
            (r'(?:限时|仅限|今日|本周).*?(?:优惠|特价|活动)', "限时活动", "需要注明具体截止时间"),
            (r'原价.*?现价', "价格对比", "原价需要有真实交易依据"),
        ]

        # 夸大承诺模式
        self.exaggeration_patterns = [
            (r'(?:包|保证|承诺).*?(?:满意|不满意退款|无效退款)', "退款承诺", "退款政策需要说明具体条件"),
            (r'(?:永不|永久|终身).*?(?:保修|免费|服务)', "永久承诺", "需要明确服务的实际期限和条件"),
            (r'(?:无限|不限).*?(?:流量|次数|时间)', "无限承诺", "需要说明具体限制条件"),
            (r'(?:随时|任意|任何时候).*?(?:退货|换货|取消)', "任意承诺", "需要说明具体的退换货政策"),
        ]

    def check(self, content: str, platform: str = "通用") -> ComplianceResult:
        """
        执行合规检查

        Args:
            content: 待检查的内容
            platform: 发布平台（公众号、小红书、朋友圈等）

        Returns:
            合规检查结果
        """
        result = ComplianceResult(is_compliant=True)

        # 1. 检查绝对化用语
        self._check_absolute_terms(content, result)

        # 2. 检查虚假宣传
        self._check_false_claims(content, result)

        # 3. 检查价格风险
        self._check_price_risks(content, result)

        # 4. 检查夸大承诺
        self._check_exaggerations(content, result)

        # 5. 检查竞品贬低
        self._check_competitor_disparagement(content, result)

        # 6. 平台特定检查
        self._check_platform_specific(content, platform, result)

        # 7. 计算合规分数
        score = 100.0
        score -= len(result.critical_issues) * 20  # 严重问题每个扣20分
        score -= len(result.warnings) * 5  # 警告每个扣5分
        result.score = max(0, score)

        # 8. 判断是否合规
        if result.critical_issues:
            result.is_compliant = False

        return result

    def _check_absolute_terms(self, content: str, result: ComplianceResult):
        """检查绝对化用语"""
        for category, terms in self.absolute_terms.items():
            for term in terms:
                # 使用正则避免部分匹配（如"最"匹配到"最近"）
                if category == "最":
                    # 对"最"字需要特殊处理，必须后面跟着形容词
                    pattern = r'(?<![近多])' + re.escape(term) + r'(?![近多])'
                else:
                    pattern = re.escape(term)

                matches = list(re.finditer(pattern, content, re.IGNORECASE))
                for match in matches:
                    # 获取上下文
                    start = max(0, match.start() - 15)
                    end = min(len(content), match.end() + 15)
                    context = content[start:end]

                    issue = ComplianceIssue(
                        category="绝对化用语",
                        severity="warning",
                        description=f"使用了绝对化表述 '{term}'",
                        location=context,
                        suggestion=f"建议修改为相对表述，如'表现优秀'、'性能出色'等，或添加限定条件"
                    )
                    result.warnings.append(issue)

    def _check_false_claims(self, content: str, result: ComplianceResult):
        """检查虚假宣传风险"""
        for pattern, claim_type, suggestion in self.false_claim_patterns:
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            for match in matches:
                context = match.group(0)

                # 检查是否有来源标注
                has_source = any(keyword in content[max(0, match.start()-50):min(len(content), match.end()+50)]
                               for keyword in ["来源", "数据来源", "根据", "依据", "官方", "测试"])

                severity = "warning" if has_source else "critical"

                issue = ComplianceIssue(
                    category=claim_type,
                    severity=severity,
                    description=f"发现{claim_type}相关声明，可能存在虚假宣传风险",
                    location=context,
                    suggestion=suggestion
                )

                if severity == "critical":
                    result.critical_issues.append(issue)
                else:
                    result.warnings.append(issue)

    def _check_price_risks(self, content: str, result: ComplianceResult):
        """检查价格相关风险"""
        for pattern, risk_type, suggestion in self.price_risk_patterns:
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            for match in matches:
                context = match.group(0)

                # 检查是否有价格来源说明
                has_source = any(keyword in content[max(0, match.start()-50):min(len(content), match.end()+50)]
                               for keyword in ["官网", "官方", "商城", "截至", "日期", "来源"])

                severity = "warning" if has_source else "critical"

                issue = ComplianceIssue(
                    category=risk_type,
                    severity=severity,
                    description=f"发现{risk_type}，需要核验来源",
                    location=context,
                    suggestion=suggestion
                )

                if severity == "critical":
                    result.critical_issues.append(issue)
                else:
                    result.warnings.append(issue)

    def _check_exaggerations(self, content: str, result: ComplianceResult):
        """检查夸大承诺"""
        for pattern, promise_type, suggestion in self.exaggeration_patterns:
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            for match in matches:
                context = match.group(0)

                issue = ComplianceIssue(
                    category="夸大承诺",
                    severity="critical",
                    description=f"发现{promise_type}，可能构成虚假承诺",
                    location=context,
                    suggestion=suggestion
                )
                result.critical_issues.append(issue)

    def _check_competitor_disparagement(self, content: str, result: ComplianceResult):
        """检查竞品贬低"""
        # 竞品品牌列表
        competitors = ["苹果", "MacBook", "联想", "ThinkPad", "戴尔", "Dell",
                      "惠普", "HP", "华硕", "ASUS", "宏碁", "Acer", "小米", "荣耀"]

        # 贬低性词汇
        negative_terms = ["差", "烂", "垃圾", "不行", "失败", "落后", "过时",
                         "淘汰", "低端", "劣质", "糟糕"]

        for competitor in competitors:
            for term in negative_terms:
                # 检查是否在同一句话中出现竞品和贬低词
                pattern = f'[^。！？\n]{{0,50}}{re.escape(competitor)}[^。！？\n]{{0,50}}{re.escape(term)}'
                matches = list(re.finditer(pattern, content))

                if not matches:
                    # 反向检查
                    pattern = f'[^。！？\n]{{0,50}}{re.escape(term)}[^。！？\n]{{0,50}}{re.escape(competitor)}'
                    matches = list(re.finditer(pattern, content))

                for match in matches:
                    context = match.group(0)

                    issue = ComplianceIssue(
                        category="竞品贬低",
                        severity="critical",
                        description=f"可能存在对竞品 '{competitor}' 的贬低性表述",
                        location=context,
                        suggestion="应客观对比产品特性，避免主观贬低竞品"
                    )
                    result.critical_issues.append(issue)

    def _check_platform_specific(self, content: str, platform: str,
                                result: ComplianceResult):
        """平台特定检查"""
        if platform == "小红书":
            # 检查是否伪造个人体验
            personal_patterns = [
                r'我[用使试]了',
                r'亲测',
                r'真实体验',
                r'用了.*?[天周月]'
            ]
            for pattern in personal_patterns:
                matches = list(re.finditer(pattern, content))
                for match in matches:
                    context = match.group(0)

                    issue = ComplianceIssue(
                        category="伪造体验",
                        severity="critical",
                        description="小红书内容不得伪造个人使用体验",
                        location=context,
                        suggestion="如果是真实体验，需要提供实际使用凭证；如果是代写，应使用客观描述"
                    )
                    result.critical_issues.append(issue)

            # 检查话题标签数量
            hashtag_count = len(re.findall(r'#[^#\s]+', content))
            if hashtag_count > 10:
                issue = ComplianceIssue(
                    category="话题标签",
                    severity="warning",
                    description=f"话题标签过多（{hashtag_count}个），建议控制在8个以内",
                    location="",
                    suggestion="过多标签可能影响内容质量和用户体验"
                )
                result.warnings.append(issue)

        elif platform == "公众号":
            # 检查是否有诱导分享/关注
            inducement_patterns = [
                r'(?:点赞|转发|分享).*?(?:抽奖|送|赠)',
                r'(?:关注|订阅).*?(?:领取|免费|赠送)',
                r'(?:集赞|拉人|邀请).*?(?:返现|优惠|奖励)'
            ]
            for pattern in inducement_patterns:
                matches = list(re.finditer(pattern, content))
                for match in matches:
                    context = match.group(0)

                    issue = ComplianceIssue(
                        category="诱导互动",
                        severity="warning",
                        description="可能存在诱导分享、关注的表述",
                        location=context,
                        suggestion="公众号应避免明显的利益诱导，建议使用更自然的行动引导"
                    )
                    result.warnings.append(issue)

        elif platform == "门店朋友圈":
            # 朋友圈应简洁，检查字数
            if len(content) > 300:
                issue = ComplianceIssue(
                    category="内容长度",
                    severity="info",
                    description=f"朋友圈文案较长（{len(content)}字），可能被折叠",
                    location="",
                    suggestion="建议控制在200字以内，确保核心信息在折叠前可见"
                )
                result.info.append(issue)

    def check_image_compliance(self, images: List[Dict]) -> List[ComplianceIssue]:
        """
        检查图片合规性

        Args:
            images: 图片列表 [{"name": "xxx.jpg", "source": "ima", "description": "..."}]

        Returns:
            合规问题列表
        """
        issues = []

        for img in images:
            img_name = img.get("name", "")
            img_source = img.get("source", "")
            img_desc = img.get("description", "")

            # 检查图片来源
            if img_source != "ima":
                issue = ComplianceIssue(
                    category="图片来源",
                    severity="critical",
                    description=f"图片 '{img_name}' 不是来自ima知识库",
                    location=img_name,
                    suggestion="必须使用ima知识库中的官方图片素材"
                )
                issues.append(issue)

            # 检查是否有水印或第三方标识
            watermark_keywords = ["测评", "评测", "体验", "开箱", "UP主", "博主"]
            if any(keyword in img_desc for keyword in watermark_keywords):
                issue = ComplianceIssue(
                    category="图片水印",
                    severity="warning",
                    description=f"图片 '{img_name}' 可能包含第三方水印或标识",
                    location=img_name,
                    suggestion="避免使用带有第三方标识的图片"
                )
                issues.append(issue)

        return issues


def main():
    """测试函数"""
    checker = ComplianceChecker()

    # 测试用例1：绝对化用语
    test_content_1 = """
    华为MateBook 14是市场上最好的笔记本电脑，性能绝对一流！
    它比苹果MacBook Pro性能强50%，是学生党的最佳选择。
    现在购买立减1000元，仅限今天！所有用户都说好用。
    """

    print("=" * 60)
    print("测试用例1：多种合规问题")
    print("=" * 60)
    result = checker.check(test_content_1, platform="通用")
    print(f"\n合规检查结果: {'✓ 通过' if result.is_compliant else '✗ 不通过'}")
    print(f"合规分数: {result.score}/100\n")

    if result.critical_issues:
        print("严重问题:")
        for issue in result.critical_issues:
            print(f"  [{issue.category}] {issue.description}")
            print(f"    位置: {issue.location}")
            print(f"    建议: {issue.suggestion}\n")

    if result.warnings:
        print("警告:")
        for issue in result.warnings:
            print(f"  [{issue.category}] {issue.description}")
            print(f"    位置: {issue.location}")
            print(f"    建议: {issue.suggestion}\n")

    # 测试用例2：小红书平台特定检查
    test_content_2 = """
    我用了华为MateBook 14一个月，真实体验超级棒！
    亲测续航12小时，办公学习完全够用。
    #华为笔记本 #MateBook #轻薄本 #学生党 #办公利器
    """

    print("=" * 60)
    print("测试用例2：小红书平台检查")
    print("=" * 60)
    result = checker.check(test_content_2, platform="小红书")
    print(f"\n合规检查结果: {'✓ 通过' if result.is_compliant else '✗ 不通过'}")
    print(f"合规分数: {result.score}/100\n")

    if result.critical_issues:
        print("严重问题:")
        for issue in result.critical_issues:
            print(f"  [{issue.category}] {issue.description}")
            print(f"    位置: {issue.location}")
            print(f"    建议: {issue.suggestion}\n")

    # 测试用例3：图片合规检查
    test_images = [
        {"name": "product.jpg", "source": "ima", "description": "产品正面图"},
        {"name": "review.jpg", "source": "internet", "description": "某UP主开箱评测截图"}
    ]

    print("=" * 60)
    print("测试用例3：图片合规检查")
    print("=" * 60)
    image_issues = checker.check_image_compliance(test_images)
    if image_issues:
        print("图片合规问题:")
        for issue in image_issues:
            print(f"  [{issue.category}] {issue.description}")
            print(f"    图片: {issue.location}")
            print(f"    建议: {issue.suggestion}\n")
    else:
        print("✓ 图片检查通过\n")


if __name__ == "__main__":
    main()