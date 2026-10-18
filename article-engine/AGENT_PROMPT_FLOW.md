# Agent 调用链与 Prompt / 模板逻辑

> 更新说明：本文描述本机「华为赛题」项目从前端到最终文案的真实路径。  
> **平台 md 提示词模板（小红书/朋友圈/公众号）只在 LLM 路径注入**；无 `LLM_API_KEY` 时回退 article-engine / 本地模板，并在 API `generation_meta.used_platform_template=false` 标明原因。

---

## 1) 完整调用链（前端 → 最终文案）

```
浏览器 frontend/
  js/api-client.js  →  AgentApi.generate(payload)  →  POST /api/generate
  js/app.js         →  也可直接 fetch(API_BASE + "/api/generate")
        │
        ▼
api_server.py
  ApiHandler.do_POST
  routes["/api/generate"] → IntegrationService.generate
        │
        ▼
agent/service.py
  IntegrationService.__init__  →  env_config.load_env() 读项目根 .env
  IntegrationService.generate(payload)
    ├─ _get_plan / plan → _task（中文平台名映射为 xhs/moments/…）
    ├─ build_content_plan(task)          # layers/scenario_strategy.py
    ├─ retrieve_evidence(...)            # layers/ima_retrieval.py
    ├─ generate_draft(task, plan, evidence)  # layers/article_generation.py  ★文案核心
    └─ _bundle(...) → verify(...)        # layers/verification.py
        │
        ▼
  返回 JSON：data.article + data.generation_mode + data.generation_meta
```

其它入口（同一 `generate_draft`）：

| 入口 | 文件 | 函数 |
|------|------|------|
| CLI demo | `demo.py` | 直接 `generate_draft` |
| agent CLI | `agent/main.py` | 流水线内 `generate_draft` |
| Gradio | `ui/gradio_app.py` | `generate_draft` |
| 修订重生 | `agent/service.py` `revise` / `layers/revision.py` | 改平台或卖点时再调 `generate_draft` |

旁路（**不是** md 提示词驱动）：

- 平台为小红书时，`article_generation._attach_xhs` → `article-engine/bridge.generate_xhs_html` → `xhs_auto_generator.XHSAutoGenerator`  
  写出 `exports/xhs/*.html`。这是**代码内嵌 HTML 模板**，**不读** `prompts/templates/小红书提示词模板-最终版.md`。

---

## 2) 每一层用了哪些 prompt / 模板

| 层 | 文件 | 读哪些文件 | 何时加载 | 如何合并 |
|----|------|------------|----------|----------|
| 任务理解 | `agent/layers/task_understanding.py` | 无 prompt 文件 | — | 结构化 TaskSpec |
| 场景策略 | `agent/layers/scenario_strategy.py` | `prompts/scenario_platform_strategy.yaml` | `build_content_plan` 每次打开 | 场景 profile ⊕ 平台 profile → ContentPlan（字数/结构/CTA/语气） |
| 检索 | `agent/layers/ima_retrieval.py` | 知识库 / 本地镜像 | generate 时 | 产出 EvidenceMap，**不是**文案 prompt |
| **生成（LLM）** | `agent/llm_client.py` + `article_generation._try_llm_draft` | ① `prompts/system_prompt.md` ② `article-engine/prompts/templates/<平台>.md` | LLM 调用前 | `build_system_prompt_for_platform`：`system_prompt` + 分隔线 + **平台模板全文** → Chat `system`；user 里塞 task/plan/evidence JSON |
| **生成（引擎）** | `article-engine/bridge.generate_article` → `ArticleSystem` | 引擎内部 rules / KB（**不读** platforms md） | LLM 失败或未配置后 | 规则拼装 opening/body/cta |
| **生成（本地）** | `article_generation._gen_title/_gen_lead/_gen_body` | 无 md；硬编码中性句式 | 引擎也失败时 | 按 ContentPlan 拼段落 |
| 小红书 HTML | `xhs_auto_generator._build_html_template` | 代码内 HTML 字符串 | `_attach_xhs` / bridge | 视觉卡；与「最终版 md」是两条线 |
| 核验 | `verification.py` (+ 可选 article-engine compliance) | 规则/引擎校验 | `_bundle` | 不生成文案 |
| 修订 | `revision.py` / `service.revise` | 无独立 prompt | 改平台时再走 `generate_draft` | 同上三分支 |

平台模板物理路径（优先「最终」文件名）：

- 小红书 → `article-engine/prompts/templates/小红书提示词模板-最终版.md`
- 朋友圈 → `article-engine/prompts/templates/朋友圈提示词模板.md`
- 公众号 → `article-engine/prompts/templates/公众号提示词模板.md`

---

## 3) LLM vs article-engine vs 旧模板：分支与回退

`generate_draft` 固定顺序：

```
1) _try_llm_draft
     跳过条件（写入 llm_skip_reason）：
       - USE_LLM_GENERATION in {0,false,False}
       - 无法 import llm_client
       - LLM_API_KEY / 等价 key 为空
       - system_prompt 合并结果为空
       - LLM 返回空 / Markdown 解析失败 / 异常
     成功：extra.generation="llm", used_platform_template=是否解析到平台 md

2) _try_article_engine   （USE_ARTICLE_ENGINE 默认 1）
     → bridge.generate_article
     成功后 _stamp_fallback_extra：
       used_platform_template=false
       generation="article-engine"
       附带已解析到的模板路径（仅作对照，**未注入**）

3) 本地 _gen_* 模板
     generation="local-template"
     used_platform_template=false
     若 platform=xhs 仍可能 _attach_xhs 写 HTML
```

API `IntegrationService._bundle`：

- `generation_mode` ← `draft.extra.generation`（不再写死 `"template"`）
- `generation_meta` ← `used_platform_template` / `platform_template*` / `llm_skip_reason` / …

`/api/status` 的 `llm` 字段会标明是否缺 key，以及缺 key 时平台 md **不会**注入。

---

## 4) 平台名 → 模板映射

**前端/表单中文 → 内部 id**（`service.PLATFORMS`）：

| 中文 | id |
|------|-----|
| 小红书 | `xhs` |
| 朋友圈 | `moments` |
| 公众号 | `wechat_mp` |
| 海报 | `poster` |

**id / 中文 → 模板文件关键词**（`llm_client._PLATFORM_TEMPLATE_KEYS`）：

| 输入 | 匹配目录内 `*.md` |
|------|-------------------|
| `xhs` / `xiaohongshu` / `小红书` | 名含「小红书」，优先含「最终」 |
| `moments` / `朋友圈` | 名含「朋友圈」 |
| `wechat_mp` / `wechat` / `公众号` | 名含「公众号」 |

**id → article-engine 中文平台**（`article_generation._PLATFORM_TO_ENGINE`）：

`xhs→小红书`, `moments→朋友圈`, `wechat_mp→公众号`, `poster→海报`

海报无专用 md，不强制 LLM。

---

## 5) 还有哪些 agent 步骤会碰 prompt

| 步骤 | 碰 prompt？ | 说明 |
|------|-------------|------|
| `task_understanding` | 否 | 规则解析 |
| `scenario_strategy` | **是（YAML）** | `prompts/scenario_platform_strategy.yaml`，非 LLM |
| `ima_retrieval` | 否 | 取证 |
| `article_generation` | **是（LLM+md）** | 唯一把平台 md 全文喂给模型的地方 |
| `_attach_xhs` / XHSAutoGenerator | 否（代码 HTML） | 易与「最终版 md」混淆 |
| `verification` | 弱 | 规则/引擎合规，不加载平台 md |
| `revision` | 间接 | 重生时再次 `generate_draft` |
| `service.status` | 否 | 只报告 LLM 是否配置 |

---

## 6) 前端如何一眼确认模板是否生效

生成接口返回（`data` 内）：

1. **`generation_meta.used_platform_template`**  
   - `true`：本次 LLM system prompt 已合并平台 md  
   - `false`：未注入（看 `llm_skip_reason`）
2. **`generation_meta.platform_template_name`**  
   例如 `小红书提示词模板-最终版.md`（即使 false 也会显示「解析到了哪份」）
3. **`generation_meta.llm_skip_reason`**  
   常见：`LLM_API_KEY empty (set in .env to use platform md templates)`
4. **`generation_mode` / `article.extra.generation`**  
   `llm` | `article-engine` | `local-template`
5. **`article.extra.system_prompt_chars`**（仅 llm 成功时）  
   合并后 system 长度，应明显大于裸 `system_prompt.md`

也可看服务端控制台：

- `[llm] skip: LLM_API_KEY empty...`
- `[llm] calling model; platform=xhs; template=小红书提示词模板-最终版.md; system_prompt_chars=...`
- `[gen] fallback=article-engine; used_platform_template=false; ...`

**注意：** `exports/xhs/*.html` 存在 ≠ 平台 md 已注入。HTML 来自 `XHSAutoGenerator`，布局可能「看起来像」最终版，但文案链路不是 LLM+md。

---

## 7) 阻塞条件（本机当前）

`.env` 现有 IMA 密钥，**没有** `LLM_API_KEY`。  
因此选小红书时实际路径是：

`generate_draft` → LLM skip → **article-engine** →（可选）XHS HTML

要真正按「小红书提示词模板-最终版」生成，需在 `.env` 增加例如：

```
LLM_API_KEY=你的密钥
LLM_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
LLM_MODEL=doubao-pro-32k
USE_LLM_GENERATION=1
```

然后重启 `api_server` / 生成服务，再跑一单，确认 `used_platform_template=true`。
