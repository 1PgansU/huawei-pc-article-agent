# AI+华为PC营销软文智能体

华为·产业进阶赛道赛题工程整理副本：基于 IMA 知识库与大模型，生成华为 PC 营销软文的智能体与前端演示。

## 目录说明

| 路径 | 说明 |
|------|------|
| `agent/` | 智能体相关逻辑 |
| `article-engine/` | 软文生成引擎 |
| `frontend/` / `ui/` | 前端与界面 |
| `prompts/` | 提示词 |
| `ima-skill/` | IMA OpenAPI skill（`connect-server.js` 引用此目录） |
| `docs/` | 文档；赛题手册在 `docs/赛题手册/` |
| `handoff-extracted/` / `exports/` | 交接与导出材料 |
| `archives/` | 体积较小的交付 zip（可选） |
| `ARCHITECTURE.md` | 架构说明 |

## 快速开始

1. 复制环境变量模板并填写密钥（**不要**把真实 `.env` 提交到 git）：
   ```bat
   copy .env.example .env
   ```
2. 参考 `.env.example` 配置 `IMA_OPENAPI_*` 与可选的 `LLM_*`（未配置 LLM 时为 mock 模式）。
3. 安装依赖并启动：
   - Python：见 `requirements.txt`，可运行 `api_server.py` / `demo.py`
   - 连接服务：`start_server.bat` 或 `启动连接服务.bat`
4. 架构细节见 [ARCHITECTURE.md](./ARCHITECTURE.md)。

## 刻意未纳入本仓库的内容

- **真实密钥**：原目录中的 `.env`（含 API Key）未复制。
- **大体积知识库**：`华为PC知识库/`、`华为PC知识库.zip`（约 25MB+）、`事实检验与合规检查.zip`（约 30MB）未纳入，请本地另行保管。
- **重复/乱码启动脚本**：原目录中因编码损坏的 bat 副本未复制，仅保留正确的 `启动连接服务.bat`。
- **`ima-skills-1.1.10/`**：与 `ima-skill` 内容重叠；代码引用的是 `ima-skill`，故只保留后者（zip 备份在 `archives/`）。

## 许可与赛题材料

赛题手册 PDF 仅供参赛使用，请遵守华为赛题相关规定。
