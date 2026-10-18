# 如何安装与使用 frontend-design skill

## 这是什么

Anthropic 官方 **frontend-design** skill：指导 Agent 做出有辨识度的生产级 UI，避开常见「AI 味」模板（紫渐变、Inter 默认脸、千篇一律卡片等）。

本目录已附：

- `frontend-design.SKILL.md` — skill 正文  
- `frontend-design.LICENSE.txt` — 许可证（转交必带）

## 方式 A：Cursor 插件市场（推荐）

1. 在 Cursor / Grok Bot 插件目录搜索 **frontend-design**  
2. 安装插件（插件稳定 id：`39586195`）  
3. 新开对话后，做网页/组件/仪表盘时 Agent 会按 skill 描述自动选用  

Grok Bot 也可让助手执行安装（用户确认后装插件即可）。

## 方式 B：手动放入项目 skills

把 skill 放到项目可被 Agent 发现的目录（二选一，文件夹名须为 `frontend-design`）：

```text
.agents/skills/frontend-design/SKILL.md
# 或
.cursor/skills/frontend-design/SKILL.md
```

操作：

```bash
mkdir -p .agents/skills/frontend-design
cp frontend-design.SKILL.md .agents/skills/frontend-design/SKILL.md
# 可选：保留许可证
cp frontend-design.LICENSE.txt .agents/skills/frontend-design/LICENSE.txt
```

用户级全局（本机所有项目）：

```text
~/.agents/skills/frontend-design/SKILL.md
~/.cursor/skills/frontend-design/SKILL.md
```

## 使用方式

在对话里直接说，例如：

- 「按 frontend-design skill，做连接页高保真」  
- 「用我们方案包里的视觉规范 + frontend-design，画成稿页三栏」  

Agent 应先读 `SKILL.md`，再结合《完整前端与产品方案.md》里的色板与 5 页结构实现。

## 与本项目的关系

- **产品/交互**：以《完整前端与产品方案.md》为准  
- **视觉执行质量**：以 `frontend-design` skill 为准  
- 二者冲突时：**赛题红线与方案包信息架构优先**；skill 管「怎么做得不像模板」

## 来源

- 官方 skill 仓库：https://github.com/anthropics/skills（skills/frontend-design）  
- Claude Code 插件镜像：https://github.com/anthropics/claude-code（plugins/frontend-design）  
