"""
大模型调用层（OpenAI 兼容协议）
================================
支持的厂商（任意一个填 LLM_API_KEY 即可）：
  - 豆包    ：https://ark.cn-beijing.volces.com/api/v3  (LLM_MODEL=doubao-pro-32k)
  - Kimi    ：https://api.moonshot.cn/v1                 (LLM_MODEL=moonshot-v1-32k)
  - DeepSeek: https://api.deepseek.com/v1                (LLM_MODEL=deepseek-chat)
  - 通义千问：https://dashscope.aliyuncs.com/compatible-mode/v1 (LLM_MODEL=qwen-plus)

设计原则：
  - 不在源码中写任何 key（仅读环境变量）
  - 失败/未配置时返回 None，调用方走 mock 兜底
  - 严格按 system_prompt.md 8 大模块约束生成
  - 小红书 / 朋友圈 / 公众号 生成时合并 article-engine/prompts/templates 对应全文
"""
import os
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import List, Dict, Optional


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _get_config() -> Dict[str, str]:
    return {
        "api_key": os.getenv("LLM_API_KEY", "").strip(),
        "base_url": os.getenv("LLM_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3").rstrip("/"),
        "model": os.getenv("LLM_MODEL", "doubao-pro-32k"),
    }


def check_llm_config() -> Dict:
    """返回 LLM 凭证状态（不打印明文）"""
    cfg = _get_config()
    key = cfg["api_key"]
    head, tail = 4, 4
    masked = (f"{key[:head]}****{key[-tail:]}"
              if key and len(key) > head + tail
              else ("****" if key else "(empty)"))
    return {
        "llm_configured": bool(key),
        "provider": _infer_provider(cfg["base_url"]),
        "model": cfg["model"],
        "api_key_masked": masked,
    }


def _infer_provider(base_url: str) -> str:
    if "volces" in base_url: return "豆包(火山方舟)"
    if "moonshot" in base_url: return "Kimi(月之暗面)"
    if "deepseek" in base_url: return "DeepSeek"
    if "dashscope" in base_url: return "通义千问"
    if "openai" in base_url: return "OpenAI"
    return "自定义"


def load_system_prompt() -> str:
    """读取项目根 prompts/system_prompt.md；缺失则返回空串。"""
    path = _project_root() / "prompts" / "system_prompt.md"
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


# platform id / 中文名 → 模板文件名关键词（目录内按关键词匹配）
_PLATFORM_TEMPLATE_KEYS = {
    "xhs": ("小红书",),
    "xiaohongshu": ("小红书",),
    "小红书": ("小红书",),
    "moments": ("朋友圈",),
    "朋友圈": ("朋友圈",),
    "wechat_mp": ("公众号",),
    "wechat": ("公众号",),
    "公众号": ("公众号",),
}


def resolve_platform_template_path(platform: str) -> Optional[Path]:
    """定位 article-engine/prompts/templates 下对应平台模板；找不到返回 None。"""
    if not platform:
        return None
    keys = _PLATFORM_TEMPLATE_KEYS.get(platform.strip()) or _PLATFORM_TEMPLATE_KEYS.get(platform.strip().lower())
    if not keys:
        keys = (platform.strip(),)
    templates_dir = _project_root() / "article-engine" / "prompts" / "templates"
    if not templates_dir.is_dir():
        return None
    md_files = sorted(templates_dir.glob("*.md"), key=lambda p: p.name)
    for key in keys:
        preferred = [p for p in md_files if key in p.name and "最终" in p.name]
        if preferred:
            return preferred[0]
        matched = [p for p in md_files if key in p.name]
        if matched:
            return matched[0]
    return None


def load_platform_template(platform: str) -> str:
    """读取平台提示词模板全文；缺失返回空串。"""
    path = resolve_platform_template_path(platform)
    if path is None:
        return ""
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def build_system_prompt_for_platform(platform: str, base_system: Optional[str] = None) -> str:
    """八模块 system_prompt + 平台模板全文（小红书/朋友圈/公众号优先）。"""
    base = (base_system if base_system is not None else load_system_prompt()).strip()
    platform_tpl = load_platform_template(platform)
    if not platform_tpl:
        return base
    sep = "\n\n---\n\n# 平台专用提示词模板（必须遵守）\n\n"
    if base:
        return base + sep + platform_tpl
    return "# 平台专用提示词模板（必须遵守）\n\n" + platform_tpl


def chat(messages: List[Dict[str, str]],
         temperature: float = 0.7,
         max_tokens: int = 2048,
         timeout: int = 60) -> Optional[str]:
    """
    调用大模型（OpenAI Chat Completions 兼容协议）
    返回：模型回复文本；失败返回 None
    """
    cfg = _get_config()
    if not cfg["api_key"]:
        return None

    url = f"{cfg['base_url']}/chat/completions"
    payload = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg['api_key']}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        print(f"[LLM] HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:300]}")
        return None
    except Exception as e:
        print(f"[LLM] 调用失败: {type(e).__name__}: {e}")
        return None


def generate_article_with_llm(task_dict: Dict, plan_dict: Dict,
                              evidence_map: Dict, system_prompt: str = "") -> Optional[str]:
    """
    用大模型生成软文正文
    task_dict    : TaskSpec.to_dict()
    plan_dict    : ContentPlan.to_dict()
    evidence_map : EvidenceMap.to_dict()
    system_prompt: 可选；为空则自动加载 prompts/system_prompt.md
                   并按 platform 合并 article-engine 平台模板全文
    """
    platform = (
        (plan_dict or {}).get("platform")
        or (task_dict or {}).get("platform")
        or ""
    )
    if not (system_prompt or "").strip():
        system_prompt = build_system_prompt_for_platform(str(platform))
    else:
        tpl = load_platform_template(str(platform))
        if tpl and tpl not in system_prompt:
            system_prompt = (
                system_prompt.rstrip()
                + "\n\n---\n\n# 平台专用提示词模板（必须遵守）\n\n"
                + tpl
            )

    tpl_path = resolve_platform_template_path(str(platform))
    tpl_note = str(tpl_path) if tpl_path else "(无匹配平台模板，仅用通用 system_prompt)"

    user_msg = f"""请基于以下结构化输入生成软文。
请严格遵守 system 中的八模块约束，以及【平台专用提示词模板】中的结构/文风/版式要求。
本平台模板来源：{tpl_note}

【任务】
{json.dumps(task_dict, ensure_ascii=False, indent=2)}

【内容策略】
{json.dumps(plan_dict, ensure_ascii=False, indent=2)}

【事实证据（仅可使用以下事实，禁止编造）】
{json.dumps(evidence_map, ensure_ascii=False, indent=2)}

【输出格式（Markdown）】
# 标题
> 导语（1-2句）

## 正文
（按 plan.structure 与平台模板展开，每段以事实点为依据）

## 行动引导
（按 plan.cta 与平台模板 CTA 规范输出）

【硬性约束】
- 所有参数/功能/卖点必须能在【事实证据】中找到
- 末尾必须包含免责句："不同销售版本配置可能不同，请以官方规格页及实际销售 SKU 为准。"
- 不要编造价格、库存、补贴、赠品
- 不要出现"最/第一/绝对/100%"等绝对化用语
- 小红书/朋友圈必须遵循对应平台模板的结构与语气；事实仍只来自证据
"""
    messages = [
        {"role": "system", "content": system_prompt or "你是华为 PC 营销图文助手，禁止编造参数。"},
        {"role": "user", "content": user_msg},
    ]
    return chat(messages, temperature=0.7, max_tokens=1800)


# ============ 自检 ============
if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from env_config import load_env
    load_env()

    print("=== LLM 凭证状态 ===")
    for k, v in check_llm_config().items():
        print(f"  {k}: {v}")

    print("\n=== 平台模板定位 ===")
    for plat in ("xhs", "moments", "wechat_mp", "小红书", "朋友圈", "公众号"):
        path = resolve_platform_template_path(plat)
        print(f"  {plat}: {path.name if path else 'MISSING'}")

    print("\n=== 连通性测试 ===")
    reply = chat([
        {"role": "user", "content": "用一句话回答：华为 MateBook 的核心卖点是什么？"}
    ])
    if reply:
        print(f"✅ 调用成功：{reply[:100]}")
    else:
        print("❌ 调用失败或未配置 LLM_API_KEY（继续走 mock 即可）")
