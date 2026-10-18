"""
知识检索器 - 从知识库中检索产品信息、卖点、场景等
"""
import os
import re
from typing import Dict, List, Optional, Tuple
from pathlib import Path


class KnowledgeRetriever:
    """知识库检索器"""

    def __init__(self, knowledge_base_path: str):
        """
        初始化知识检索器

        Args:
            knowledge_base_path: 知识库根目录路径
        """
        self.kb_path = Path(knowledge_base_path)
        self.p1_path = self.kb_path / "P1-产品参数库"
        self.p2_path = self.kb_path / "P2-卖点话术库"
        self.p6_path = self.kb_path / "P6-营销素材库"
        self.p8_path = self.kb_path / "P8-客户场景库"

        # 产品索引
        self.product_index = self._build_product_index()

    def _build_product_index(self) -> Dict[str, Dict]:
        """构建产品索引"""
        index = {}

        # 扫描P1-产品参数库
        for category in ["01-鸿蒙电脑", "02-MateBook-Windows", "03-华为擎云商用"]:
            category_path = self.p1_path / category
            if not category_path.exists():
                continue

            for product_dir in category_path.iterdir():
                if not product_dir.is_dir():
                    continue

                product_name = product_dir.name
                index[product_name] = {
                    "name": product_name,
                    "category": category,
                    "path": product_dir,
                    "facts_file": product_dir / "产品事实.md"
                }

        return index

    def get_product_facts(self, product_name: str) -> Optional[Dict]:
        """
        获取产品事实

        Args:
            product_name: 产品型号

        Returns:
            产品事实字典
        """
        if product_name not in self.product_index:
            return None

        product_info = self.product_index[product_name]
        facts_file = product_info["facts_file"]

        if not facts_file.exists():
            return None

        with open(facts_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 解析产品事实
        facts = {
            "product_name": product_name,
            "category": product_info["category"],
            "raw_content": content,
            "source_file": str(facts_file)
        }

        # 提取官方来源
        source_match = re.search(r'产品页：(https?://[^\n]+)', content)
        if source_match:
            facts["official_url"] = source_match.group(1).strip()

        # 提取操作系统
        os_match = re.search(r'## 操作系统\s*\n+([^\n#]+)', content)
        if os_match:
            facts["os"] = os_match.group(1).strip()

        # 提取屏幕信息
        screen_match = re.search(r'## 屏幕.*?尺寸\s*\n+([0-9.]+\s*英寸)', content, re.DOTALL)
        if screen_match:
            facts["screen_size"] = screen_match.group(1).strip()

        screen_type = re.search(r'类型\s*\n+([^\n]+)', content)
        if screen_type:
            facts["screen_type"] = screen_type.group(1).strip()

        resolution = re.search(r'分辨率\s*\n+([0-9]+\s*[×x]\s*[0-9]+)', content)
        if resolution:
            facts["resolution"] = resolution.group(1).strip()

        # 提取处理器
        cpu_match = re.search(r'## 处理器.*?\n+([^\n#]+)', content, re.DOTALL)
        if cpu_match:
            facts["processor"] = cpu_match.group(1).strip()

        # 提取内存
        memory_match = re.search(r'## 内存.*?容量.*?\n+([^\n#]+)', content, re.DOTALL)
        if memory_match:
            facts["memory"] = memory_match.group(1).strip()

        # 提取存储
        storage_match = re.search(r'## 存储.*?容量.*?\n+([^\n#]+)', content, re.DOTALL)
        if storage_match:
            facts["storage"] = storage_match.group(1).strip()

        # 提取重量
        weight_match = re.search(r'重量\s*\n+约\s*([0-9.]+\s*kg)', content)
        if weight_match:
            facts["weight"] = weight_match.group(1).strip()

        # 提取厚度
        thickness_match = re.search(r'厚度\s*\n+([0-9.]+\s*mm)', content)
        if thickness_match:
            facts["thickness"] = thickness_match.group(1).strip()

        return facts

    def get_selling_points(self, product_name: str, scenario: str = "") -> List[Dict]:
        """
        获取产品卖点话术

        Args:
            product_name: 产品型号
            scenario: 使用场景（可选）

        Returns:
            卖点列表
        """
        selling_points = []

        # 从P2-卖点话术库查找
        # 这里简化处理，实际应该扫描目录
        product_category = self._get_product_category(product_name)

        if "鸿蒙" in product_category or "HarmonyOS" in product_name:
            selling_points.append({
                "point": "HarmonyOS生态协同",
                "description": "与华为手机、平板无缝协同，支持文件互传、屏幕共享",
                "limitation": "需登录同一华为账号"
            })

        if "14" in product_name:
            selling_points.append({
                "point": "3:2黄金比例屏幕",
                "description": "相比16:9屏幕，纵向显示内容增加约18%",
                "limitation": "适合文档编辑和网页浏览"
            })

        # 根据场景添加卖点
        if "学生" in scenario or "学习" in scenario:
            selling_points.append({
                "point": "轻薄便携",
                "description": "适合携带上课和自习",
                "limitation": ""
            })

        if "办公" in scenario:
            selling_points.append({
                "point": "移动办公",
                "description": "续航长，接口丰富",
                "limitation": ""
            })

        return selling_points

    def _get_product_category(self, product_name: str) -> str:
        """获取产品类别"""
        if product_name in self.product_index:
            return self.product_index[product_name]["category"]
        return ""

    def get_scenario_info(self, scenario: str) -> Optional[Dict]:
        """
        获取场景信息

        Args:
            scenario: 场景名称（如：学生学习、移动办公）

        Returns:
            场景信息字典
        """
        scenario_map = {
            "学生": "07-学生学习",
            "学习": "07-学生学习",
            "办公": "06-移动办公",
            "移动办公": "06-移动办公",
            "内容创作": "05-内容创作",
            "创作": "05-内容创作",
            "商务": "09-商务管理",
            "企业": "11-企业IT",
            "教育": "02-教育"
        }

        for key, folder in scenario_map.items():
            if key in scenario:
                scenario_path = self.p8_path / folder
                if scenario_path.exists():
                    return {
                        "name": folder,
                        "path": scenario_path,
                        "keywords": [key]
                    }

        return None

    def get_available_products(self) -> List[str]:
        """获取所有可用产品列表"""
        return list(self.product_index.keys())

    def search_product(self, query: str) -> List[str]:
        """
        搜索产品

        Args:
            query: 搜索关键词

        Returns:
            匹配的产品列表
        """
        query_lower = query.lower()
        results = []

        for product_name in self.product_index.keys():
            if query_lower in product_name.lower():
                results.append(product_name)

        return results


def main():
    """测试知识检索器"""
    import os

    kb_path = os.path.join(os.path.dirname(__file__),
                           "华为PC知识库(1)",
                           "华为PC全板块深度知识库_v7")

    retriever = KnowledgeRetriever(kb_path)

    print("=" * 60)
    print("知识检索器测试")
    print("=" * 60)

    # 测试产品索引
    products = retriever.get_available_products()
    print(f"\n可用产品数量: {len(products)}")
    print(f"产品列表: {products[:5]}...")

    # 测试产品搜索
    search_results = retriever.search_product("MateBook 14")
    print(f"\n搜索'MateBook 14'结果: {search_results}")

    # 测试获取产品事实
    if search_results:
        product = search_results[0]
        facts = retriever.get_product_facts(product)

        if facts:
            print(f"\n{product} 产品事实:")
            print(f"  操作系统: {facts.get('os', '未知')}")
            print(f"  屏幕: {facts.get('screen_size', '未知')} {facts.get('screen_type', '')}")
            print(f"  处理器: {facts.get('processor', '未知')}")
            print(f"  内存: {facts.get('memory', '未知')}")
            print(f"  存储: {facts.get('storage', '未知')}")
            print(f"  重量: {facts.get('weight', '未知')}")
            print(f"  官方链接: {facts.get('official_url', '未知')}")

    # 测试卖点获取
    selling_points = retriever.get_selling_points("HUAWEI MateBook 14", "学生学习")
    print(f"\n卖点数量: {len(selling_points)}")
    for sp in selling_points:
        print(f"  - {sp['point']}: {sp['description']}")
        if sp['limitation']:
            print(f"    限制: {sp['limitation']}")


if __name__ == "__main__":
    main()
