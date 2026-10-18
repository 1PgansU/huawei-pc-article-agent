# 华为PC营销软文智能体 · 前端

> 赛题：AI+华为PC营销软文智能体（产业进阶赛道）  
> 技术：静态 HTML / CSS / JS + 可选 Node 连接探测服务（Plan A ima / Plan B 本地库）

## 推荐启动方式（一键）

在项目根目录（与 `connect-server.js`、`启动连接服务.bat`、`frontend/`、`ima-skill/` 同级）：

1. **Windows**：双击 `启动连接服务.bat`  
2. 浏览器会打开 **http://127.0.0.1:8787/**（同一端口托管页面 + `/api`）  
3. 在连接页点 **「连接知识库」**

也可手动：

```bash
node connect-server.js
# 访问 http://127.0.0.1:8787/
```

端口可用环境变量 `HW_CONNECT_PORT` 覆盖。

## 连接逻辑（Plan A → Plan B）

| 模式 | 条件 | 行为 |
|---|---|---|
| **Plan A · ima** | 本机有凭证且网络通 | 调用 `ima-skill/ima_api.cjs` 搜索「任德耀新建华为PC知识库 / 华为PC」，取匹配库，再 `get_knowledge_list` 估条目数 |
| **Plan B · 本地** | 云端失败或点「仅用本地库」 | 扫描本机 `华为PC知识库`（可用 `HW_LOCAL_KB` 覆盖） |

成功（A 或 B）后才解锁「下一步：填写任务」。

### 凭证配置（不要写进仓库）

任选其一（服务启动时会自动读取项目根目录 `.env`，不把密钥写进前端源码）：

- 项目根 `.env`：`IMA_OPENAPI_CLIENTID` + `IMA_OPENAPI_APIKEY`（推荐，你本机已有）
- 环境变量：`IMA_CLIENT_ID` + `IMA_API_KEY`（或同上 OPENAPI 名）
- 文件：`%USERPROFILE%\.config\ima\client_id` 与 `api_key`（各一行明文）
- 页面「高级」：仅写入浏览器 **sessionStorage**，刷新可清，不落盘到项目

### 本地知识库路径

默认（Windows）：`C:\Users\<你>\Desktop\华为赛题\华为PC知识库`  
可用环境变量 `HW_LOCAL_KB` 指向其他目录。

## 页面地图

| 路由 Hash | 页面 | 职责 |
|---|---|---|
| `#connect` | 连接页 | 真连 ima 或本地库；成功后解锁任务 |
| `#task` | 任务页 | TaskSpec 表单；缺项追问 |
| `#strategy` | 策略页 | ContentPlan |
| `#draft` | 成稿页 | 取证 · 稿纸 · 合规签章（后续页仍为演示规则） |
| `#revise` | 修订页 | 重跑 5→6 + 导出 |

## 目录结构（项目根）

```
华为赛题/
  启动连接服务.bat
  connect-server.js      # 静态托管 + /api/health + /api/connect
  ima-skill/             # 官方 ima_api.cjs（勿提交密钥）
  frontend/
    index.html
    css/styles.css
    js/app.js
    js/mock-data.js      # 任务/策略/成稿演示数据；连接态默认未连接
    README.md
  华为PC知识库/          # Plan B 兜底目录
```

## API（本机探测服务）

- `GET /api/health` — 服务是否起来、是否检测到凭证  
- `POST /api/connect` — body 可选 `{ "prefer": "auto"|"ima"|"local", "client_id", "api_key", "local_path" }`  
  返回 `{ mode, ok, title, detail, kb_id?, kb_name?, item_hint?, local_path?, error? }`

## 限制（诚实清单）

1. 连接页已接真探测；**成稿内容仍多为前端规则演示**，生产需继续接检索/生成后端。  
2. 静态 `file://` 打开时无法调本机 API，请用 bat / `node connect-server.js`。  
3. 不要把 API Key 写进源码或提交到 Git。  
4. 配图仍为 CSS 占位。  
5. 桌面优先（约 1280px）。
