# article-engine 接入说明

## 已做的接线
| 位置 | 行为 |
|------|------|
| `article-engine/` | 生成/事实核验/合规引擎源码 + `bridge.py` / `paths.py` |
| `agent/layers/article_generation.py` | `generate_draft`：**LLM+平台模板 → 引擎 → 原模板**；失败逐级回退 |
| `agent/llm_client.py` | 加载 `prompts/system_prompt.md` + `article-engine/prompts/templates` 平台全文并入 system |
| `agent/layers/verification.py` | `verify` 叠加引擎 FactVerifier+ComplianceChecker；失败忽略 |
| `prompts/system_prompt.md` + `01`–`08_*.md` | 八模块系统提示词 |
| frontend / api 路由 | **未改** |

知识库路径：自动解析 `华为PC知识库/华为PC全板块深度知识库_v7`（与 `ima_retrieval.P1_ROOT` 一致）。可用 `HUAWEI_KB_ROOT` 覆盖。

关闭引擎：`$env:USE_ARTICLE_ENGINE="0"`  
关闭 LLM 生成（仍可用引擎/模板）：`$env:USE_LLM_GENERATION="0"`

## 平台提示词模板（重要）

路径：`article-engine/prompts/templates/`

| 平台 | 文件 |
|------|------|
| 小红书 | `小红书提示词模板-最终版.md` |
| 朋友圈 | `朋友圈提示词模板.md` |
| 公众号 | `公众号提示词模板.md` |
| 通用参考 | `AI提示词模板.md` |

**接线：** `llm_client.resolve_platform_template_path` / `load_platform_template` / `build_system_prompt_for_platform`  
在 `generate_article_with_llm` 与 `article_generation._try_llm_draft` 中，按 `plan.platform`（`xhs` / `moments` / `wechat_mp`）把对应模板**全文**合并进 system prompt。未配置 `LLM_API_KEY` 或调用失败 → 回退 article-engine / 原模板，**不改 API**。

## 回退策略
- 引擎目录缺失、导入失败、产品名不在引擎索引、生成无稿 → 打印 `[article-engine] … fallback` 并走原 layers。
- LLM 未配置 / 解析失败 → 打印 `[llm] … fallback`，再试引擎或原模板。
- 配图始终来自 `EvidenceMap`（不采用引擎图片 id），避免破坏图片核验。

## 启动
```powershell
cd "C:\Users\phobi\Desktop\华为赛题"
python -m agent.api_server
# 或以仓库现有启动脚本 / 批处理为准
```

## 冒烟
```powershell
cd "C:\Users\phobi\Desktop\华为赛题\article-engine"
python -c "from paths import resolve_kb_root; print(resolve_kb_root())"
python -c "from bridge import compliance_check_only; print(compliance_check_only('普通描述')['result']['score'])"
cd "C:\Users\phobi\Desktop\华为赛题"
python -c "from agent.llm_client import resolve_platform_template_path; print(resolve_platform_template_path('xhs')); print(resolve_platform_template_path('moments')); print(resolve_platform_template_path('wechat_mp'))"
```

## 小红书自动图文（XHSAutoGenerator）

增量自 `xhs_auto_generator.py`：从知识库抽事实、匹配产品图、输出左图右文 HTML。

| 位置 | 作用 |
|------|------|
| `article-engine/xhs_auto_generator.py` | 核心生成器 |
| `article-engine/prompts/templates/*.md` | 各平台提示词模板（含小红书最终版）——**现已接入 LLM 生成** |
| `article-engine/examples/auto_xhs_*.html` | 样例 HTML（只作参考） |
| `bridge.generate_xhs_html(...)` | 稳定 dict 接口；默认写到 `exports/xhs/` |
| `bridge.generate_article(...)` | platform 含「小红书」时附加 `xhs_html_path` / `extra.xhs`；失败只记 `xhs_error`，主文案仍返回 |
| `agent/layers/article_generation.py` | `DraftArticle.xhs_html_path` / `extra`；平台为 `xhs` 时尝试旁路 |

**前端怎么看到：** 走原有「生成」按钮（平台选小红书）。API 返回的 `article` 里多了：

- `xhs_html_path`：本机 HTML 绝对路径（可用浏览器打开）
- `extra.xhs`：风格、人群、kb_root 等元数据
- `extra.generation=llm` / `extra.platform_template=...`：若本次走了 LLM+模板

同目录会有 `product_image.jpg`（生成器自动拷贝）。**未改** `/api/*` 路由名。

**冒烟：**
```powershell
cd "C:\Users\phobi\Desktop\华为赛题\article-engine"
python -c "from xhs_auto_generator import XHSAutoGenerator; print('ok', XHSAutoGenerator)"
python -c "from bridge import generate_xhs_html; r=generate_xhs_html('HUAWEI MateBook 14', style='颜值种草'); print(r['html_path'])"
```
