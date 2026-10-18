# article-engine 接入说明

## 已做的接线
| 位置 | 行为 |
|------|------|
| `article-engine/` | 生成/事实核验/合规引擎源码 + `bridge.py` / `paths.py` |
| `agent/layers/article_generation.py` | `generate_draft` 优先调引擎；失败回退原模板 |
| `agent/layers/verification.py` | `verify` 叠加引擎 FactVerifier+ComplianceChecker；失败忽略 |
| `prompts/system_prompt.md` + `01`–`08_*.md` | 八模块系统提示词 |
| frontend / api 路由 | **未改** |

知识库路径：自动解析 `华为PC知识库/华为PC全板块深度知识库_v7`（与 `ima_retrieval.P1_ROOT` 一致）。可用 `HUAWEI_KB_ROOT` 覆盖。

关闭引擎：`$env:USE_ARTICLE_ENGINE="0"`

## 回退策略
- 引擎目录缺失、导入失败、产品名不在引擎索引、生成无稿 → 打印 `[article-engine] … fallback` 并走原 layers。
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
```
