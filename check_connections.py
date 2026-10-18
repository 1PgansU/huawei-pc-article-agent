"""
连接自检 —— 一条命令确认「ima 知识库」和「大模型」是否真的通
============================================================
用法：
    python check_connections.py            # 常规自检
    python check_connections.py --deep     # 追加真实内容抓取 + LLM 实际对话测试

判定标准（不看 "是否配置了"，只看 "是否真的调通"）：
    ima  : search_knowledge_base → search_knowledge → get_media_info → 抓正文
    LLM  : 对 base_url 发 /models 探测；--deep 时再发一次真实 chat
"""
import os
import sys
import json
import argparse
import urllib.request
import urllib.error

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from agent.env_config import load_env  # noqa: E402
load_env()

from agent.layers.kb_connection import (  # noqa: E402
    check_knowledge_base, DEFAULT_KB_NAME, IMA_SKILL,
)
from agent.layers.ima_retrieval import _ima_call  # noqa: E402

OK, BAD, WARN = "✅", "❌", "⚠️ "


def line(tag: str, name: str, ok: bool, detail: str = "") -> bool:
    print(f"{OK if ok else BAD} [{tag}] {name}" + (f" — {detail}" if detail else ""))
    return ok


def check_ima(deep: bool) -> bool:
    print("\n──────── IMA 知识库 ────────")
    cid = os.getenv("IMA_OPENAPI_CLIENTID", "")
    key = os.getenv("IMA_OPENAPI_APIKEY", "")
    ok = True
    ok &= line("凭证", "IMA_OPENAPI_CLIENTID / APIKEY 已加载", bool(cid and key),
               f"client_id={cid[:4]}****" if cid else "未找到（检查 .env 是否被加载）")
    if not (cid and key):
        return False

    ok &= line("环境", "ima skill 可执行", os.path.exists(IMA_SKILL), IMA_SKILL)

    r1 = _ima_call("openapi/wiki/v1/search_knowledge_base",
                   {"query": DEFAULT_KB_NAME, "cursor": "", "limit": 20})
    ok1 = bool(r1 and r1.get("code") == 0)
    detail1 = r1.get("msg", "") if r1 else "无返回"
    kb_id = ""
    if ok1:
        try:
            info = r1["data"]["info_list"][0]
            kb_id = info.get("kb_id", "")
            detail1 = f"{info.get('kb_name')} / 成员{info.get('member_count')} / 内容{info.get('content_count')}条"
        except (KeyError, IndexError):
            ok1 = False
            detail1 = "返回体中没有匹配的 info_list"
    ok &= line("接口", "search_knowledge_base", ok1, detail1)
    if not kb_id:
        return False

    probe = "HUAWEI MateBook 14"
    r2 = _ima_call("openapi/wiki/v1/search_knowledge",
                   {"knowledge_base_id": kb_id, "query": probe, "limit": 5})
    items = (r2 or {}).get("data", {}).get("info_list", []) or []
    ok &= line("接口", "search_knowledge", r2 is not None and r2.get("code") == 0,
               f"命中 {len(items)} 条：{items[0].get('title', '')[:30] if items else '（空）'}")
    media_id = items[0].get("media_id", "") if items else ""

    # 正式状态（与 UI 展示一致）
    st = check_knowledge_base()
    ok &= line("状态", f"UI 展示的连接状态 = {st.connection}", st.connection == "connected",
               st.kb_name)

    if deep and items:
        # 注意：media_type=99 是文件夹(media_id=folder_xxx)，get_media_info 会报 220030，必须过滤
        md_items = [i for i in items if i.get("media_type") in (7, None)]
        img_items = [i for i in items if i.get("media_type") == 9]
        if img_items:
            print(f"{OK} [图片] 知识库返回图片资源 {len(img_items)} 个：{img_items[0].get('title','')[:30]}")
        quota_hit = False
        for it in md_items[:5]:
            mid = it.get("media_id", "")
            title = it.get("title", "")[:36]
            r3 = _ima_call("openapi/wiki/v1/get_media_info", {"media_id": mid})
            code = (r3 or {}).get("code")
            msg = (r3 or {}).get("msg", "")
            if code == 220021:  # 每日原文抓取配额
                print(f"{WARN} [内容] 配额限制：{msg}")
                quota_hit = True
                break
            try:
                ui = r3["data"]["url_info"]
                url, headers = ui["url"], ui.get("headers", {})
            except (TypeError, KeyError):
                print(f"{WARN} [内容] {title} → get_media_info code={code} msg={msg}（跳过）")
                continue
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=30) as resp:
                    body = resp.read().decode("utf-8", errors="replace")
                ok &= line("内容", "get_media_info → 抓正文", True, f"{len(body)} 字符｜来源：{title}")
                print("      正文前 100 字：", body[:100].replace("\n", " "))
                break
            except Exception as e:
                print(f"{WARN} [内容] {title} 下载失败 {type(e).__name__}（换下一条）")
        else:
            if not quota_hit:
                ok &= line("内容", "get_media_info → 抓正文", False, "前 5 条均无法获取，检查知识库权限")
        if quota_hit:
            print("      → 今日原文抓取额度已用完，不影响「检索+生成」链路；"
                  "请把原文缓存到本地，避免每天重复拉取。")
    elif not deep:
        print(f"{WARN} [内容] 抓正文未测试（加 --deep 可验证）")

    return ok


def check_llm(deep: bool) -> bool:
    print("\n──────── 大模型 LLM ────────")
    cfg = {
        "api_key": os.getenv("LLM_API_KEY", "").strip(),
        "base_url": os.getenv("LLM_BASE_URL", "").strip().rstrip("/"),
        "model": os.getenv("LLM_MODEL", "").strip(),
    }
    ok = True
    ok &= line("凭证", "LLM_API_KEY 已加载", bool(cfg["api_key"]),
               f"{cfg['api_key'][:4]}****{cfg['api_key'][-4:]}" if cfg["api_key"] else "未配置")
    if not cfg["api_key"]:
        print("      → 系统会自动走 mock 模板生成，功能可演示但不算真实调用。")
        return False
    print(f"      base_url = {cfg['base_url']}\n      model    = {cfg['model']}")

    # 1) 网络可达性（无论是否 --deep 都测，失败通常是代理/墙导致）
    probe_url = f"{cfg['base_url']}/models"
    try:
        req = urllib.request.Request(probe_url, headers={"Authorization": f"Bearer {cfg['api_key']}"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            code = resp.status
            body = resp.read().decode("utf-8", errors="replace")[:120]
    except urllib.error.HTTPError as e:
        code, body = e.code, e.read().decode("utf-8", errors="replace")[:120]
    except Exception as e:
        code, body = 0, f"{type(e).__name__}: {e}"
    reachable = code != 0
    ok &= line("网络", f"{cfg['base_url']} 可达", reachable, f"HTTP {code} {body[:80]}")
    if not reachable:
        print("      → 常见原因：OpenAI 官方域名在当前网络不可达。建议换国内厂商：")
        print("        LLM_BASE_URL=https://api.deepseek.com/v1   LLM_MODEL=deepseek-chat")
        print("        LLM_BASE_URL=https://api.moonshot.cn/v1    LLM_MODEL=moonshot-v1-32k")
        print("        LLM_BASE_URL=https://ark.cn-beijing.volces.com/api/v3  LLM_MODEL=doubao-pro-32k")

    # 2) 真实对话
    if deep and reachable:
        from agent.llm_client import chat
        reply = chat([{"role": "user", "content": "回复两个字：可用"}], max_tokens=32)
        ok &= line("调用", "chat/completions 实调", bool(reply), (reply or "无返回")[:80])
    elif reachable:
        print(f"{WARN} [调用] 对话实调未测试（加 --deep 可验证）")

    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deep", action="store_true", help="追加上下文抓取与真实对话测试")
    args = ap.parse_args()

    print("=" * 60)
    print(f"项目根目录: {PROJECT_ROOT}")
    print(f".env 已加载: {os.path.exists(os.path.join(PROJECT_ROOT, '.env'))}")
    print("=" * 60)

    ima_ok = check_ima(args.deep)
    llm_ok = check_llm(args.deep)

    print("\n" + "=" * 60)
    print(f"ima 知识库 : {'通过' if ima_ok else '不通过'}")
    print(f"LLM 大模型 : {'通过' if llm_ok else '不通过（当前走 mock 兜底）'}")
    print("=" * 60)
    return 0 if (ima_ok and llm_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
