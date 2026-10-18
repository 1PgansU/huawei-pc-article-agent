"""
事实核验模块
负责检查生成的软文中的产品事实是否准确，包括型号、参数、功能等
"""
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class VerificationResult:
    """核验结果"""
    is_valid: bool
    verified_facts: List[str] = field(default_factory=list)  # 已核验的事实
    unverified_claims: List[str] = field(default_factory=list)  # 无法核验的声明
    incorrect_facts: List[str] = field(default_factory=list)  # 错误的事实
    missing_sources: List[str] = field(default_factory=list)  # 缺少来源的声明
    image_issues: List[str] = field(default_factory=list)  # 图片问题
    warnings: List[str] = field(default_factory=list)  # 警告信息

    def to_dict(self) -> Dict:
        return {
            "is_valid": self.is_valid,
            "verified_facts": self.verified_facts,
            "unverified_claims": self.unverified_claims,
            "incorrect_facts": self.incorrect_facts,
            "missing_sources": self.missing_sources,
            "image_issues": self.image_issues,
            "warnings": self.warnings
        }


class FactVerifier:
    """事实核验器"""

    def __init__(self, knowledge_base_path: str):
        """
        初始化事实核验器

        Args:
            knowledge_base_path: 知识库根目录路径
        """
        self.kb_path = Path(knowledge_base_path)
        self.product_db = {}  # 产品数据库缓存
        self.price_db = {}  # 价格数据库缓存

        # 加载产品型号索引
        self._load_product_index()

    def _load_product_index(self):
        """加载产品型号索引"""
        product_param_path = self.kb_path / "P1-产品参数库"

        # 扫描鸿蒙电脑
        harmonyos_path = product_param_path / "01-鸿蒙电脑"
        if harmonyos_path.exists():
            for product_dir in harmonyos_path.iterdir():
                if product_dir.is_dir():
                    product_name = product_dir.name
                    self.product_db[product_name] = {
                        "type": "鸿蒙电脑",
                        "path": product_dir
                    }

        # 扫描Windows电脑
        windows_path = product_param_path / "02-MateBook-Windows"
        if windows_path.exists():
            for product_dir in windows_path.iterdir():
                if product_dir.is_dir():
                    product_name = product_dir.name
                    self.product_db[product_name] = {
                        "type": "Windows电脑",
                        "path": product_dir
                    }

        # 扫描商用产品
        business_path = product_param_path / "03-华为擎云商用"
        if business_path.exists():
            for product_dir in business_path.iterdir():
                if product_dir.is_dir():
                    product_name = product_dir.name
                    self.product_db[product_name] = {
                        "type": "商用电脑",
                        "path": product_dir
                    }

    def _load_product_facts(self, product_name: str) -> Optional[Dict]:
        """加载产品事实数据"""
        if product_name not in self.product_db:
            return None

        product_info = self.product_db[product_name]
        facts_file = product_info["path"] / "产品事实.md"

        if not facts_file.exists():
            return None

        with open(facts_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 解析产品事实（简化版，提取关键规格）
        facts = {
            "product_name": product_name,
            "type": product_info["type"],
            "raw_content": content
        }

        # 提取操作系统
        os_match = re.search(r'(?:操作系统|OS)[：:\s]*\n*(HarmonyOS \d+|Windows \d+[^\\n]*)', content)
        if os_match:
            facts["os"] = os_match.group(1).strip()

        # 提取处理器
        cpu_patterns = [
            r'处理器[：:\s]*\n*([^\n]+)',
            r'CPU[：:\s]*\n*([^\n]+)',
            r'(?:搭载|采用)[^\n]*?([酷睿Ultra|麒麟|英特尔|Intel][^\n，。]+)'
        ]
        for pattern in cpu_patterns:
            cpu_match = re.search(pattern, content)
            if cpu_match:
                facts["processor"] = cpu_match.group(1).strip()
                break

        # 提取内存规格
        memory_match = re.search(r'(?:内存|RAM)[：:\s]*\n*([^\n]+)', content)
        if memory_match:
            facts["memory"] = memory_match.group(1).strip()

        # 提取存储规格
        storage_match = re.search(r'(?:存储|硬盘|SSD)[：:\s]*\n*([^\n]+)', content)
        if storage_match:
            facts["storage"] = storage_match.group(1).strip()

        # 提取屏幕规格
        screen_match = re.search(r'尺寸[：:\s]*\n*([0-9.]+\s*英寸)', content)
        if screen_match:
            facts["screen_size"] = screen_match.group(1).strip()

        resolution_match = re.search(r'分辨率[：:\s]*\n*([0-9]+\s*[×x]\s*[0-9]+)', content)
        if resolution_match:
            facts["resolution"] = resolution_match.group(1).strip()

        # 提取重量
        weight_match = re.search(r'(?:重量|约)[：:\s]*\n*约?\s*([0-9.]+\s*kg)', content)
        if weight_match:
            facts["weight"] = weight_match.group(1).strip()

        return facts

    def _extract_product_claims(self, content: str) -> List[Dict]:
        """
        从生成的软文中提取产品声明

        Args:
            content: 软文内容

        Returns:
            产品声明列表
        """
        claims = []

        # 提取型号声明
        model_patterns = [
            r'(HUAWEI MateBook [^\s，。]+)',
            r'(MateBook [^\s，。]+)',
            r'(华为擎云[^\s，。]+)'
        ]
        for pattern in model_patterns:
            for match in re.finditer(pattern, content):
                claims.append({
                    "type": "产品型号",
                    "claim": match.group(1),
                    "context": content[max(0, match.start()-20):min(len(content), match.end()+20)]
                })

        # 提取处理器声明
        cpu_patterns = [
            r'(搭载|采用|配备)[^\n]*?([酷睿Ultra|麒麟X?\d+|英特尔.*?[0-9]+代|Intel Core [^\s，。]+)[^\n]*?处理器',
            r'处理器[^\n]*?([酷睿Ultra|麒麟X?\d+|英特尔.*?[0-9]+代|Intel Core [^\s，。]+)',
            r'(麒麟X?\d+|酷睿Ultra|Intel Core [^\s，。]+)[^\n]*?性能'
        ]
        for pattern in cpu_patterns:
            for match in re.finditer(pattern, content):
                claims.append({
                    "type": "处理器",
                    "claim": match.group(0),
                    "context": match.group(0)
                })

        # 提取内存和存储声明
        memory_patterns = [
            r'(\d+\s*GB)[^\n]*?(?:内存|RAM)',
            r'内存[^\n]*?(\d+\s*GB)'
        ]
        for pattern in memory_patterns:
            for match in re.finditer(pattern, content):
                claims.append({
                    "type": "内存",
                    "claim": match.group(0),
                    "context": match.group(0)
                })

        storage_patterns = [
            r'(\d+\s*(?:GB|TB))[^\n]*?(?:存储|硬盘|SSD)',
            r'(?:存储|硬盘)[^\n]*?(\d+\s*(?:GB|TB))'
        ]
        for pattern in storage_patterns:
            for match in re.finditer(pattern, content):
                claims.append({
                    "type": "存储",
                    "claim": match.group(0),
                    "context": match.group(0)
                })

        # 提取屏幕声明
        screen_patterns = [
            r'(\d+(?:\.\d+)?)[^\n]*?英寸[^\n]*?屏',
            r'屏幕[^\n]*?(\d+(?:\.\d+)?)[^\n]*?英寸',
            r'(\d+\s*[×x]\s*\d+)[^\n]*?分辨率',
            r'分辨率[^\n]*?(\d+\s*[×x]\s*\d+)',
            r'(OLED|LCD|IPS)[^\n]*?屏',
            r'(\d+Hz)[^\n]*?刷新率'
        ]
        for pattern in screen_patterns:
            for match in re.finditer(pattern, content):
                claims.append({
                    "type": "屏幕",
                    "claim": match.group(0),
                    "context": match.group(0)
                })

        # 提取重量和尺寸声明
        weight_patterns = [
            r'重量[^\n]*?(\d+(?:\.\d+)?)[^\n]*?kg',
            r'约\s*(\d+(?:\.\d+)?)\s*kg',
            r'仅重\s*(\d+(?:\.\d+)?)\s*kg'
        ]
        for pattern in weight_patterns:
            for match in re.finditer(pattern, content):
                claims.append({
                    "type": "重量",
                    "claim": match.group(0),
                    "context": match.group(0)
                })

        # 提取续航声明
        battery_patterns = [
            r'续航[^\n]*?(\d+)[^\n]*?小时',
            r'(\d+)[^\n]*?小时[^\n]*?续航',
            r'电池[^\n]*?(\d+\s*(?:Wh|mAh))'
        ]
        for pattern in battery_patterns:
            for match in re.finditer(pattern, content):
                claims.append({
                    "type": "续航",
                    "claim": match.group(0),
                    "context": match.group(0)
                })

        # 提取价格声明
        price_patterns = [
            r'价格[^\n]*?([¥￥]\s*\d+)',
            r'([¥￥]\s*\d+)[^\n]*?起',
            r'售价[^\n]*?(\d+\s*元)',
            r'(\d+\s*元)[^\n]*?起'
        ]
        for pattern in price_patterns:
            for match in re.finditer(pattern, content):
                claims.append({
                    "type": "价格",
                    "claim": match.group(0),
                    "context": match.group(0)
                })

        return claims

    def verify_content(self, product_name: str, content: str,
                      images: List[Dict] = None) -> VerificationResult:
        """
        核验软文内容

        Args:
            product_name: 产品型号
            content: 软文内容
            images: 图片列表 [{"name": "xxx.jpg", "source": "ima", "model": "MateBook 14"}]

        Returns:
            核验结果
        """
        result = VerificationResult(is_valid=True)

        # 1. 检查产品型号是否存在
        if product_name not in self.product_db:
            result.is_valid = False
            result.incorrect_facts.append(f"产品型号 '{product_name}' 在知识库中不存在")
            return result

        # 2. 加载产品事实数据
        facts = self._load_product_facts(product_name)
        if not facts:
            result.is_valid = False
            result.incorrect_facts.append(f"无法加载产品 '{product_name}' 的事实数据")
            return result

        # 3. 提取软文中的产品声明
        claims = self._extract_product_claims(content)

        # 4. 逐项核验
        for claim in claims:
            claim_type = claim["type"]
            claim_text = claim["claim"]

            if claim_type == "产品型号":
                # 检查型号是否准确
                if claim_text != product_name and claim_text not in product_name:
                    result.warnings.append(
                        f"提及的型号 '{claim_text}' 可能与目标产品 '{product_name}' 不一致"
                    )

            elif claim_type == "处理器":
                # 检查处理器信息
                if "processor" in facts:
                    fact_cpu = facts["processor"].lower()
                    claim_cpu = claim_text.lower()

                    # 简单模糊匹配
                    if not any(keyword in claim_cpu for keyword in fact_cpu.split()):
                        result.warnings.append(
                            f"处理器声明 '{claim_text}' 可能与事实 '{facts['processor']}' 不符"
                        )
                    else:
                        result.verified_facts.append(f"处理器: {claim_text}")
                else:
                    result.unverified_claims.append(f"处理器声明: {claim_text} (知识库无对应事实)")

            elif claim_type == "内存":
                # 提取内存容量数字
                claimed_mem = re.search(r'(\d+)\s*GB', claim_text)
                if claimed_mem and "memory" in facts:
                    claimed_value = claimed_mem.group(1)
                    if claimed_value not in facts["memory"]:
                        result.warnings.append(
                            f"内存声明 '{claim_text}' 可能与事实 '{facts['memory']}' 不符"
                        )
                    else:
                        result.verified_facts.append(f"内存: {claim_text}")

            elif claim_type == "存储":
                # 提取存储容量
                claimed_storage = re.search(r'(\d+\s*(?:GB|TB))', claim_text)
                if claimed_storage and "storage" in facts:
                    claimed_value = claimed_storage.group(1)
                    if claimed_value not in facts["storage"]:
                        result.warnings.append(
                            f"存储声明 '{claim_text}' 可能与事实 '{facts['storage']}' 不符"
                        )
                    else:
                        result.verified_facts.append(f"存储: {claim_text}")

            elif claim_type == "屏幕":
                # 检查屏幕声明
                screen_size_match = re.search(r'(\d+(?:\.\d+)?)\s*英寸', claim_text)
                if screen_size_match and "screen_size" in facts:
                    claimed_size = screen_size_match.group(1)
                    fact_size = re.search(r'(\d+(?:\.\d+)?)', facts["screen_size"])
                    if fact_size and claimed_size != fact_size.group(1):
                        result.warnings.append(
                            f"屏幕尺寸声明 '{claim_text}' 可能与事实 '{facts['screen_size']}' 不符"
                        )
                    else:
                        result.verified_facts.append(f"屏幕: {claim_text}")

            elif claim_type == "重量":
                # 检查重量声明
                weight_match = re.search(r'(\d+(?:\.\d+)?)', claim_text)
                if weight_match and "weight" in facts:
                    claimed_weight = weight_match.group(1)
                    fact_weight = re.search(r'(\d+(?:\.\d+)?)', facts["weight"])
                    if fact_weight and claimed_weight != fact_weight.group(1):
                        result.warnings.append(
                            f"重量声明 '{claim_text}' 可能与事实 '{facts['weight']}' 不符"
                        )
                    else:
                        result.verified_facts.append(f"重量: {claim_text}")

            elif claim_type == "续航":
                # 续航通常需要标注测试条件，检查是否有限定语
                if "典型" not in claim_text and "测试" not in claim_text and "约" not in claim_text:
                    result.warnings.append(
                        f"续航声明 '{claim_text}' 缺少限定条件（如'典型使用'、'测试条件'等）"
                    )
                else:
                    result.verified_facts.append(f"续航: {claim_text}")

            elif claim_type == "价格":
                # 价格声明需要特别注意
                result.warnings.append(
                    f"发现价格声明 '{claim_text}'，需要核验是否有官方来源依据"
                )

        # 5. 检查绝对化声明（无依据的夸张）
        absolute_patterns = [
            r'最[好好棒强快]',
            r'第一',
            r'最佳',
            r'无敌',
            r'完美',
            r'100%',
            r'绝对',
            r'一定',
            r'所有.*都',
            r'任何.*都',
            r'永远'
        ]
        for pattern in absolute_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                result.warnings.append(
                    f"发现可能的绝对化表述: '{match.group()}' (位置: {match.start()})"
                )

        # 6. 核验图片
        if images:
            for img in images:
                img_name = img.get("name", "")
                img_source = img.get("source", "")
                img_model = img.get("model", "")

                # 检查图片来源
                if img_source != "ima":
                    result.image_issues.append(
                        f"图片 '{img_name}' 的来源不是ima知识库"
                    )

                # 检查图片型号是否匹配
                if img_model and img_model != product_name:
                    result.image_issues.append(
                        f"图片 '{img_name}' 的型号 '{img_model}' 与目标产品 '{product_name}' 不一致"
                    )

                # 检查是否标注了插入位置
                if "position" not in img or not img["position"]:
                    result.image_issues.append(
                        f"图片 '{img_name}' 未标注建议插入位置"
                    )

        # 7. 检查是否缺少必要的限定条件
        risky_claims = [
            (r'支持.*协同', '协同功能'),
            (r'AI.*检测', 'AI功能'),
            (r'兼容.*设备', '设备兼容性'),
            (r'运行.*软件', '软件兼容性')
        ]
        for pattern, feature_name in risky_claims:
            if re.search(pattern, content):
                if not re.search(r'需要|必须|支持|限于|仅限|部分|当前', content):
                    result.warnings.append(
                        f"提及{feature_name}但可能缺少使用条件或限制说明"
                    )

        # 8. 最终判断
        if result.incorrect_facts or result.image_issues:
            result.is_valid = False

        return result

    def verify_model_consistency(self, content: str) -> List[str]:
        """
        检查内容中是否混用了不同型号

        Args:
            content: 软文内容

        Returns:
            发现的型号列表
        """
        models_found = []
        model_patterns = [
            r'HUAWEI MateBook [^\s，。\n]+',
            r'MateBook [^\s，。\n]+',
            r'华为擎云[^\s，。\n]+'
        ]

        for pattern in model_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                model = match.group(0)
                if model not in models_found:
                    models_found.append(model)

        return models_found


def main():
    """测试函数"""
    # 示例用法
    import os
    kb_path = os.path.join(os.path.dirname(__file__), "华为PC知识库(1)", "华为PC全板块深度知识库_v7")

    # 检查路径是否存在
    if not os.path.exists(kb_path):
        print(f"错误：知识库路径不存在: {kb_path}")
        print(f"当前目录: {os.getcwd()}")
        print(f"脚本目录: {os.path.dirname(__file__)}")
        return

    print(f"知识库路径: {kb_path}")
    verifier = FactVerifier(kb_path)
    print(f"已加载产品数量: {len(verifier.product_db)}")
    if verifier.product_db:
        print(f"产品列表: {list(verifier.product_db.keys())[:5]}...")

    # 测试软文
    test_content = """
    HUAWEI MateBook 14（鸿蒙版）是一款搭载麒麟 X90 处理器的14.2英寸轻薄本，
    配备24GB内存和512GB存储，重量约1.33kg。它采用OLED屏幕，分辨率2880×1920，
    续航可达12小时。这是市场上最好的笔记本，性能绝对一流。
    """

    test_images = [
        {"name": "matebook14_front.jpg", "source": "ima",
         "model": "HUAWEI MateBook 14", "position": "标题下方"},
        {"name": "matebook14_side.jpg", "source": "internet",
         "model": "HUAWEI MateBook 14", "position": ""}
    ]

    result = verifier.verify_content("HUAWEI MateBook 14", test_content, test_images)

    print("=" * 60)
    print("事实核验结果")
    print("=" * 60)
    print(f"\n整体是否通过: {result.is_valid}\n")

    if result.verified_facts:
        print("✓ 已核验的事实:")
        for fact in result.verified_facts:
            print(f"  - {fact}")

    if result.warnings:
        print("\n⚠ 警告:")
        for warning in result.warnings:
            print(f"  - {warning}")

    if result.incorrect_facts:
        print("\n✗ 错误的事实:")
        for error in result.incorrect_facts:
            print(f"  - {error}")

    if result.unverified_claims:
        print("\n? 无法核验的声明:")
        for claim in result.unverified_claims:
            print(f"  - {claim}")

    if result.image_issues:
        print("\n✗ 图片问题:")
        for issue in result.image_issues:
            print(f"  - {issue}")


if __name__ == "__main__":
    main()
