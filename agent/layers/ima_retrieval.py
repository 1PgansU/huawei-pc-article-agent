"""
第 3 层 + 第 4 层：ima 检索 + 事实点提取
========================================
清单③ 知识与图片检索：按型号和任务调用 ima OpenAPI；检索产品资料及图片；保留来源记录。

三级检索策略：
  1. ima OpenAPI（配置了 IMA_OPENAPI_CLIENTID / IMA_OPENAPI_APIKEY 时）
  2. 本地知识库索引（离线可演示，来源=知识库文件路径，现场可抽查）
  3. 内置 mock 数据（最终兜底，保证 demo 永远可运行）

接口调用顺序（赛题手册 P7）：
  A. search_knowledge_base → 锁定 kb_id
  C. search_knowledge      → 按型号+任务关键词检索
  D. get_media_info        → 拉取原文与图片

凭证：环境变量，严禁写入源码（赛题 P6 安全要求）。
"""
import os
import re
import subprocess
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOCAL_KB_ROOT = os.path.join(PROJECT_ROOT, "华为PC知识库")
P1_ROOT = os.path.join(LOCAL_KB_ROOT, "华为PC全板块深度知识库_v7", "P1-产品参数库")
IMA_SKILL = os.path.join(PROJECT_ROOT, "ima-skills-1.1.10", "ima-skill", "ima_api.cjs")


@dataclass
class EvidenceMap:
    """事实点 + 图片绑定"""
    facts: List[Dict] = field(default_factory=list)
    # facts[i] = {"key", "value", "source", "url"(可选)}
    images: List[Dict] = field(default_factory=list)
    # images[i] = {"id", "desc", "source", "matched_model", "path"(本地可预览时)}
    retrieval_mode: str = "mock"   # ima_api / local_index / mock


# ─────────────────────────────────────────────
# 模式 2：本地知识库索引（现场可抽查来源）
# ─────────────────────────────────────────────

def _normalize(text: str) -> str:
    """型号匹配用的归一化：去空格/大小写/横线"""
    return re.sub(r"[\s\-—_（）()·]", "", text).lower()


def find_product_dir(product: str) -> Optional[str]:
    """在 P1 目录下按型号模糊匹配产品文件夹"""
    if not os.path.isdir(P1_ROOT):
        return None
    target = _normalize(product)
    best, best_score = None, 0
    for root, subdirs, files in os.walk(P1_ROOT):
        if "产品事实.md" not in files:
            continue
        name = _normalize(os.path.basename(root))
        score = 0
        if name == target:
            score = 100
        elif target and (target in name or name in target):
            score = 60 + len(name)  # 越长越具体优先
        else:
            # 关键词重合度（如 "matebook14" "鸿蒙"）
            tokens = [t for t in re.split(r"[a-z0-9]+|[\u4e00-\u9fff]", "") if t]
            overlap = sum(1 for ch in set(target) if ch in name)
            score = overlap if overlap >= 4 else 0
        if score > best_score:
            best, best_score = root, score
    return best


def _parse_fact_md(path: str, rel_source: str, limit: int = 24) -> List[Dict]:
    """
    解析 产品事实.md / 卖点与限制.md：'## key' 下面的非空行合并为 value。
    每条事实 source = 知识库内相对路径（现场可打开核对）。
    """
    facts = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return facts

    current_key, buf = None, []
    url_hint = ""
    m = re.search(r"产品页：(https?://\S+)", content)
    if m:
        url_hint = m.group(1)

    def flush():
        nonlocal current_key, buf
        if current_key and buf:
            value = "；".join(x.strip() for x in buf if x.strip())[:220]
            if value:
                item = {"key": current_key, "value": value, "source": rel_source}
                if url_hint:
                    item["url"] = url_hint
                facts.append(item)
        buf = []

    for line in content.splitlines():
        if line.startswith("## "):
            flush()
            current_key = line[3:].strip()
        elif line.startswith("#") or line.startswith(">"):
            continue
        elif current_key and line.strip():
            buf.append(line.strip().strip("-* "))
        if len(facts) >= limit:
            break
    flush()
    return facts


_IMG_DESC_RE = re.compile(r"^(?:hwpc|vmall)_[^_]*_(.+?)_\d+\.(png|jpe?g|webp)$", re.I)


def _collect_images(product_dir: str, product: str, max_images: int = 10) -> List[Dict]:
    """收集产品目录下的图片，desc 从文件名解析，source=相对路径，path=本地可预览路径"""
    images = []
    for sub in ("images", "商城款式图片"):
        d = os.path.join(product_dir, sub)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not re.search(r"\.(png|jpe?g|webp)$", fn, re.I):
                continue
            full = os.path.join(d, fn)
            rel = os.path.relpath(full, LOCAL_KB_ROOT)
            m = _IMG_DESC_RE.match(fn)
            desc = m.group(1) if m else os.path.splitext(fn)[0]
            images.append({
                "id": fn,
                "desc": desc,
                "source": f"华为PC知识库/{rel}",
                "matched_model": product,
                "path": full,
            })
            if len(images) >= max_images:
                return images
    return images


def _local_retrieve(product: str, scenario: str) -> Optional[EvidenceMap]:
    """本地知识库检索：返回 None 表示没找到产品目录"""
    pdir = find_product_dir(product)
    if not pdir:
        return None

    facts: List[Dict] = []
    for fn in ("产品事实.md", "卖点与限制.md"):
        fp = os.path.join(pdir, fn)
        if os.path.exists(fp):
            rel = os.path.relpath(fp, LOCAL_KB_ROOT)
            facts.extend(_parse_fact_md(fp, f"华为PC知识库/{rel}"))

    images = _collect_images(pdir, product)
    if not facts and not images:
        return None
    return EvidenceMap(facts=facts, images=images, retrieval_mode="local_index")


# ─────────────────────────────────────────────
# 模式 1：ima OpenAPI（真实调用）
# ─────────────────────────────────────────────

def _ima_call(endpoint: str, payload: dict) -> Optional[dict]:
    if not os.path.exists(IMA_SKILL):
        return None
    try:
        r = subprocess.run(
            ["node", IMA_SKILL, endpoint, json.dumps(payload, ensure_ascii=False)],
            capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace",
        )
        return json.loads(r.stdout)
    except Exception:
        return None


def _ima_retrieve(kb_name: str, product: str, scenario: str) -> Optional[EvidenceMap]:
    """真实 ima OpenAPI 调用（A → C → D）。失败返回 None 回退本地索引。"""
    resp = _ima_call("openapi/wiki/v1/search_knowledge_base",
                     {"query": kb_name, "cursor": "", "limit": 20})
    if not resp:
        return None
    try:
        kb_id = resp["data"]["info_list"][0]["kb_id"]
    except (KeyError, IndexError):
        return None

    resp = _ima_call("openapi/wiki/v1/search_knowledge",
                     {"knowledge_base_id": kb_id, "query": product, "limit": 10})
    if not resp:
        return None

    facts, images = [], []
    items = resp.get("data", {}).get("info_list", []) or []
    for it in items:
        title = it.get("title", "")
        snippet = it.get("snippet") or it.get("summary") or ""
        if snippet:
            facts.append({
                "key": title[:20] or "知识条目",
                "value": snippet[:220],
                "source": f"ima kb://{kb_id}/{it.get('media_id', title)}",
            })
    return EvidenceMap(facts=facts, images=images, retrieval_mode="ima_api")


# ─────────────────────────────────────────────
# 模式 3：mock 兜底
# ─────────────────────────────────────────────

_MOCK_FACTS_HARMONY = [
    {"key": "操作系统", "value": "HarmonyOS 6", "source": "P1-产品参数库/01-鸿蒙电脑/HUAWEI MateBook 14/产品事实.md"},
    {"key": "处理器", "value": "麒麟 X90", "source": "P1-产品参数库/01-鸿蒙电脑/HUAWEI MateBook 14/产品事实.md"},
    {"key": "屏幕", "value": "14.2 英寸 3:2 OLED 抗反射触控屏，2880×1920，60/120 Hz", "source": "P1-产品参数库/01-鸿蒙电脑/HUAWEI MateBook 14/产品事实.md"},
    {"key": "重量", "value": "约 1.32-1.33 kg（按方键盘/圆键盘版本区分），厚度 14.5 mm", "source": "P1-产品参数库/01-鸿蒙电脑/HUAWEI MateBook 14/产品事实.md"},
    {"key": "内存", "value": "24 GB / 32 GB", "source": "P1-产品参数库/01-鸿蒙电脑/HUAWEI MateBook 14/产品事实.md"},
    {"key": "接口", "value": "HDMI 2.1 ×1、USB-C ×1、USB-A ×2、3.5 mm ×1", "source": "P1-产品参数库/01-鸿蒙电脑/HUAWEI MateBook 14/产品事实.md"},
]

_MOCK_IMAGES_HARMONY = [
    {"id": "hwpc_matebook-14-harmonyos_原野绿多彩配色_04.png", "desc": "原野绿外观主视觉",
     "source": "P1-产品参数库/01-鸿蒙电脑/HUAWEI MateBook 14/images/", "matched_model": "HUAWEI MateBook 14 鸿蒙版"},
    {"id": "hwpc_matebook-14-harmonyos_深空灰沉稳配色_05.png", "desc": "深空灰沉稳配色",
     "source": "P1-产品参数库/01-鸿蒙电脑/HUAWEI MateBook 14/images/", "matched_model": "HUAWEI MateBook 14 鸿蒙版"},
    {"id": "hwpc_matebook-14-harmonyos_手写笔创作场景_07.jpg", "desc": "手写笔学习/创作场景",
     "source": "P1-产品参数库/01-鸿蒙电脑/HUAWEI MateBook 14/images/", "matched_model": "HUAWEI MateBook 14 鸿蒙版"},
    {"id": "vmall_matebook-14-harmonyos_丰富接口轻薄侧面_13.png", "desc": "接口丰富、轻薄侧面",
     "source": "P1-产品参数库/01-鸿蒙电脑/HUAWEI MateBook 14/商城款式图片/", "matched_model": "HUAWEI MateBook 14 鸿蒙版"},
    {"id": "vmall_matebook-14-harmonyos_长续航影音场景_17.jpg", "desc": "长续航影音场景",
     "source": "P1-产品参数库/01-鸿蒙电脑/HUAWEI MateBook 14/商城款式图片/", "matched_model": "HUAWEI MateBook 14 鸿蒙版"},
    {"id": "vmall_matebook-14-harmonyos_手机协同桌面展示_15.png", "desc": "手机协同桌面展示",
     "source": "P1-产品参数库/01-鸿蒙电脑/HUAWEI MateBook 14/商城款式图片/", "matched_model": "HUAWEI MateBook 14 鸿蒙版"},
]


def _mock_retrieve(product: str) -> EvidenceMap:
    if "MateBook 14" in product or "鸿蒙" in product:
        return EvidenceMap(facts=list(_MOCK_FACTS_HARMONY),
                           images=list(_MOCK_IMAGES_HARMONY), retrieval_mode="mock")
    return EvidenceMap(facts=[], images=[], retrieval_mode="mock")


# ─────────────────────────────────────────────
# 统一入口
# ─────────────────────────────────────────────

def retrieve_evidence(kb_name: str, product: str, scenario: str) -> EvidenceMap:
    """
    检索入口（三级回退）：
      ima OpenAPI（有凭证）→ 本地知识库索引 → mock
    """
    has_creds = bool(os.getenv("IMA_OPENAPI_CLIENTID") and os.getenv("IMA_OPENAPI_APIKEY"))
    if has_creds:
        result = _ima_retrieve(kb_name, product, scenario)
        if result and (result.facts or result.images):
            return result

    result = _local_retrieve(product, scenario)
    if result is not None:
        return result

    return _mock_retrieve(product)


# 兼容旧调用
def list_products() -> List[str]:
    """列出本地知识库中所有可检索的产品名（UI 下拉用）"""
    from .kb_connection import list_local_product_dirs
    return [os.path.basename(d) for d in list_local_product_dirs()]
