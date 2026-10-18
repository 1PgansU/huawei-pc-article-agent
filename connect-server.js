#!/usr/bin/env node
/**
 * 华为PC营销软文智能体 · 连接探测服务
 * 同时托管 frontend 静态文件 + /api/*
 * 默认端口 8787
 *
 * Plan A: 调用 ima-skill/ima_api.cjs 搜共享库并估条目
 * Plan B: 扫描本地「华为PC知识库」目录
 */
"use strict";

const http = require("http");
const fs = require("fs");
const path = require("path");
const os = require("os");
const { spawn } = require("child_process");
const { URL } = require("url");

const ROOT = __dirname;

/** Load KEY=VALUE from .env into process.env if not already set (no logging of values). */
function loadDotEnv(filePath) {
  try {
    if (!fs.existsSync(filePath)) return false;
    const lines = fs.readFileSync(filePath, "utf8").split(/\r?\n/);
    for (const line of lines) {
      const t = line.trim();
      if (!t || t.startsWith("#")) continue;
      const m = t.match(/^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$/);
      if (!m) continue;
      const key = m[1];
      let val = m[2];
      if (
        (val.startsWith('"') && val.endsWith('"')) ||
        (val.startsWith("'") && val.endsWith("'"))
      ) {
        val = val.slice(1, -1);
      }
      if (process.env[key] === undefined || process.env[key] === "") {
        process.env[key] = val;
      }
    }
    return true;
  } catch {
    return false;
  }
}
loadDotEnv(path.join(ROOT, ".env"));
loadDotEnv(path.join(ROOT, "frontend", ".env"));

const FRONTEND = path.join(ROOT, "frontend");
const IMA_API = path.join(ROOT, "ima-skill", "ima_api.cjs");
const PORT = Number(process.env.HW_CONNECT_PORT || 8787);

const WIN_DEFAULT_KB = path.join(
  process.env.USERPROFILE || "C:\\Users\\phobi",
  "Desktop",
  "华为赛题",
  "华为PC知识库"
);
const BOX_FALLBACK_KB = path.join(
  "/workspace",
  "workbuddy-analyze",
  "华为PC知识库(1)"
);

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".md": "text/markdown; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
  ".woff2": "font/woff2",
  ".txt": "text/plain; charset=utf-8",
};

function sendJson(res, status, obj) {
  const body = JSON.stringify(obj);
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Cache-Control": "no-store",
  });
  res.end(body);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    req.on("data", (c) => {
      size += c.length;
      if (size > 1e6) {
        reject(new Error("body too large"));
        req.destroy();
        return;
      }
      chunks.push(c);
    });
    req.on("end", () => {
      const raw = Buffer.concat(chunks).toString("utf8");
      if (!raw) return resolve({});
      try {
        resolve(JSON.parse(raw));
      } catch {
        reject(new Error("invalid JSON"));
      }
    });
    req.on("error", reject);
  });
}

function hasCredentials(extra = {}) {
  const clientId =
    extra.client_id ||
    process.env.IMA_CLIENT_ID ||
    process.env.IMA_OPENAPI_CLIENTID ||
    readSafe(path.join(os.homedir(), ".config", "ima", "client_id"));
  const apiKey =
    extra.api_key ||
    process.env.IMA_API_KEY ||
    process.env.IMA_OPENAPI_APIKEY ||
    readSafe(path.join(os.homedir(), ".config", "ima", "api_key"));
  return Boolean(clientId && apiKey);
}

function readSafe(p) {
  try {
    return fs.readFileSync(p, "utf8").trim();
  } catch {
    return "";
  }
}

function resolveLocalKbPath(override) {
  if (override && String(override).trim()) {
    return path.resolve(String(override).trim());
  }
  if (process.env.HW_LOCAL_KB) {
    return path.resolve(process.env.HW_LOCAL_KB);
  }
  if (process.platform === "win32" && fs.existsSync(WIN_DEFAULT_KB)) {
    return WIN_DEFAULT_KB;
  }
  if (fs.existsSync(BOX_FALLBACK_KB)) {
    return BOX_FALLBACK_KB;
  }
  if (process.platform === "win32") {
    return WIN_DEFAULT_KB;
  }
  return BOX_FALLBACK_KB;
}

function walkStats(root, maxFiles = 8000) {
  const out = {
    exists: false,
    md: 0,
    files: 0,
    dirs: 0,
    hasP1: false,
    hasReadme: false,
    sample: [],
  };
  if (!root || !fs.existsSync(root)) return out;
  const st = fs.statSync(root);
  if (!st.isDirectory()) return out;
  out.exists = true;

  const stack = [root];
  while (stack.length && out.files < maxFiles) {
    const dir = stack.pop();
    let entries;
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const ent of entries) {
      if (ent.name === ".git" || ent.name === "node_modules" || ent.name === ".DS_Store") continue;
      const full = path.join(dir, ent.name);
      if (ent.isDirectory()) {
        out.dirs += 1;
        if (/P1|产品参数/i.test(ent.name)) out.hasP1 = true;
        stack.push(full);
      } else if (ent.isFile()) {
        out.files += 1;
        const lower = ent.name.toLowerCase();
        if (lower.endsWith(".md")) {
          out.md += 1;
          if (out.sample.length < 6) {
            out.sample.push(path.relative(root, full));
          }
        }
        if (/^readme/i.test(ent.name) || ent.name === "全库导航.md" || ent.name === "导入ima说明.md") {
          out.hasReadme = true;
        }
        if (/P1|产品参数/i.test(ent.name)) out.hasP1 = true;
      }
    }
  }
  return out;
}

function scanLocal(localPath) {
  const stats = walkStats(localPath);
  if (!stats.exists) {
    return {
      mode: "none",
      ok: false,
      title: "未找到本地知识库",
      detail: `目录不存在：${localPath}`,
      local_path: localPath,
      error: "local_kb_missing",
    };
  }
  const bits = [];
  bits.push(`约 ${stats.files} 个文件`);
  if (stats.md) bits.push(`${stats.md} 个 Markdown`);
  if (stats.hasP1) bits.push("含产品参数相关目录/文件");
  if (stats.hasReadme) bits.push("含 README/导航说明");
  const detail = bits.join(" · ") + (stats.sample.length ? ` · 示例：${stats.sample.slice(0, 3).join("、")}` : "");
  const thin = stats.files < 3 && stats.md < 2;
  return {
    mode: "local",
    ok: true,
    title: "已用本地知识库",
    detail: thin
      ? `${detail}（内容偏少，若你有完整压缩包请解压到该路径）`
      : detail,
    local_path: localPath,
    item_hint: stats.files,
    local_stats: stats,
  };
}

function runImaApi(apiPath, body, creds = {}) {
  return new Promise((resolve) => {
    if (!fs.existsSync(IMA_API)) {
      resolve({ ok: false, error: "ima_api_missing", msg: `未找到 ${IMA_API}` });
      return;
    }
    const env = { ...process.env };
    if (creds.client_id) {
      env.IMA_CLIENT_ID = creds.client_id;
      env.IMA_OPENAPI_CLIENTID = creds.client_id;
    }
    if (creds.api_key) {
      env.IMA_API_KEY = creds.api_key;
      env.IMA_OPENAPI_APIKEY = creds.api_key;
    }
    const args = [IMA_API, apiPath, JSON.stringify(body || {})];
    const child = spawn(process.execPath, args, {
      env,
      cwd: path.dirname(IMA_API),
      windowsHide: true,
    });
    let stdout = "";
    let stderr = "";
    const timer = setTimeout(() => {
      try {
        child.kill("SIGTERM");
      } catch (_) {}
      resolve({ ok: false, error: "timeout", msg: "ima API 调用超时" });
    }, 45000);
    child.stdout.on("data", (d) => {
      stdout += d.toString("utf8");
    });
    child.stderr.on("data", (d) => {
      stderr += d.toString("utf8");
    });
    child.on("error", (err) => {
      clearTimeout(timer);
      resolve({ ok: false, error: "spawn_failed", msg: err.message });
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      if (code !== 0) {
        let msg = stderr || stdout || `exit ${code}`;
        try {
          const j = JSON.parse(stderr || "{}");
          if (j.msg) msg = j.msg;
        } catch (_) {}
        resolve({ ok: false, error: "ima_failed", msg: String(msg).slice(0, 500), raw: stdout.slice(0, 300) });
        return;
      }
      // stdout may contain update-check JSON concatenated; take last JSON object
      const parsed = parseLastJson(stdout);
      if (!parsed) {
        resolve({ ok: false, error: "bad_json", msg: "无法解析 ima 返回", raw: stdout.slice(0, 400) });
        return;
      }
      resolve({ ok: true, data: parsed });
    });
  });
}

function parseLastJson(text) {
  const t = String(text || "").trim();
  if (!t) return null;
  try {
    return JSON.parse(t);
  } catch (_) {}
  // try last {...} block
  const idx = t.lastIndexOf("{");
  if (idx >= 0) {
    try {
      return JSON.parse(t.slice(idx));
    } catch (_) {}
  }
  return null;
}

function unwrapData(resp) {
  if (!resp || typeof resp !== "object") return {};
  if (resp.data && typeof resp.data === "object") return resp.data;
  return resp;
}

function apiOk(resp) {
  if (!resp || typeof resp !== "object") return false;
  const code = resp.retcode ?? resp.code ?? resp.errcode;
  if (code === undefined || code === null) {
    // some wrappers only return data
    return Boolean(resp.data || resp.info_list || resp.knowledge_list);
  }
  return Number(code) === 0;
}

function pickKb(list) {
  if (!Array.isArray(list) || !list.length) return null;
  const prefer = (name) => {
    const n = String(name || "");
    if (/任德耀.*华为PC|华为PC知识库|华为PC营销|华为.?PC/i.test(n)) return 2;
    if (/华为|MateBook|PC/i.test(n)) return 1;
    return 0;
  };
  const scored = list
    .map((item) => ({
      id: item.kb_id || item.id || item.knowledge_base_id || "",
      name: item.kb_name || item.name || item.title || "",
      content_count: Number(item.content_count || item.item_count || item.knowledge_count || 0) || 0,
      member_count: Number(item.member_count || 0) || 0,
      score: prefer(item.kb_name || item.name || item.title),
      raw: item,
    }))
    .filter((x) => x.id);
  scored.sort((a, b) => b.score - a.score);
  return scored[0] || null;
}

async function tryIma(creds) {
  if (!hasCredentials(creds)) {
    return {
      mode: "none",
      ok: false,
      title: "未配置凭证",
      detail: "未找到 IMA_CLIENT_ID / IMA_API_KEY（或 ~/.config/ima/）。将尝试本地库。",
      error: "no_credentials",
    };
  }

  const queries = ["任德耀新建华为PC知识库", "华为PC知识库", "华为PC"];
  let kb = null;
  let lastErr = null;

  for (const q of queries) {
    const r = await runImaApi(
      "openapi/wiki/v1/search_knowledge_base",
      { query: q, cursor: "", limit: 20 },
      creds
    );
    if (!r.ok) {
      lastErr = r.msg || r.error;
      continue;
    }
    if (!apiOk(r.data)) {
      lastErr = (r.data && (r.data.msg || r.data.message)) || "search 返回非 0";
      continue;
    }
    const data = unwrapData(r.data);
    const list = data.info_list || data.list || data.knowledge_bases || [];
    kb = pickKb(list);
    if (kb) break;
  }

  if (!kb) {
    return {
      mode: "none",
      ok: false,
      title: "未找到华为 PC 知识库",
      detail: lastErr
        ? `搜索失败或无匹配：${lastErr}`
        : "已搜索「任德耀新建华为PC知识库 / 华为PC」，未匹配到可用库。",
      error: "kb_not_found",
    };
  }

  // Prefer content_count from search result (authoritative); optionally smoke list root
  let total = kb.content_count || 0;
  let listSmoke = null;
  const r = await runImaApi(
    "openapi/wiki/v1/get_knowledge_list",
    { knowledge_base_id: kb.id, cursor: "", limit: 20 },
    creds
  );
  if (r.ok && apiOk(r.data)) {
    const data = unwrapData(r.data);
    const kn = data.knowledge_list || data.info_list || data.list || [];
    listSmoke = Array.isArray(kn) ? kn.length : 0;
  }
  if (!total && listSmoke) total = listSmoke;

  const hint = total
    ? `约 ${total} 项`
    : listSmoke != null
      ? `根目录可见 ${listSmoke} 项`
      : "已连接，条目数暂不可估";

  return {
    mode: "ima",
    ok: true,
    title: "已连 ima 云端",
    detail: `知识库「${kb.name}」· ${hint}`,
    kb_id: kb.id,
    kb_name: kb.name,
    item_hint: total || listSmoke || undefined,
    member_count: kb.member_count || undefined,
  };
}

async function connect(body) {
  const prefer = (body && body.prefer) || "auto"; // auto | ima | local
  const creds = {
    client_id: body && body.client_id,
    api_key: body && body.api_key,
  };
  const localPath = resolveLocalKbPath(body && body.local_path);

  if (prefer === "local") {
    return scanLocal(localPath);
  }

  if (prefer === "ima") {
    const a = await tryIma(creds);
    if (a.ok) return a;
    return { ...a, fallback_local: scanLocal(localPath) };
  }

  // auto: A then B
  const a = await tryIma(creds);
  if (a.ok) return a;
  const b = scanLocal(localPath);
  if (b.ok) {
    return {
      ...b,
      title: "已用本地知识库（云端未通）",
      detail: `${b.detail}；云端原因：${a.detail || a.error || "未知"}`,
      ima_error: a.error,
      ima_detail: a.detail,
    };
  }
  return {
    mode: "none",
    ok: false,
    title: "未能连接",
    detail: `云端：${a.detail || a.error}；本地：${b.detail || b.error}`,
    error: "both_failed",
    ima_error: a.error,
    local_path: localPath,
  };
}

function serveStatic(req, res, urlPath) {
  let rel = decodeURIComponent(urlPath.split("?")[0]);
  if (rel === "/" || rel === "") rel = "/index.html";
  if (rel.includes("..")) {
    res.writeHead(400);
    res.end("bad path");
    return;
  }
  const filePath = path.join(FRONTEND, rel.replace(/^\//, ""));
  if (!filePath.startsWith(FRONTEND)) {
    res.writeHead(403);
    res.end("forbidden");
    return;
  }
  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
      res.end("Not found: " + rel);
      return;
    }
    const ext = path.extname(filePath).toLowerCase();
    res.writeHead(200, { "Content-Type": MIME[ext] || "application/octet-stream" });
    res.end(data);
  });
}

const server = http.createServer(async (req, res) => {
  const u = new URL(req.url || "/", `http://${req.headers.host || "127.0.0.1"}`);
  const p = u.pathname;

  if (req.method === "OPTIONS") {
    res.writeHead(204, {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    });
    res.end();
    return;
  }

  try {
    if (p === "/api/health" && req.method === "GET") {
      sendJson(res, 200, {
        ok: true,
        service: "huawei-connect",
        port: PORT,
        has_credentials: hasCredentials(),
        ima_api: fs.existsSync(IMA_API),
        default_local_kb: resolveLocalKbPath(),
        time: new Date().toISOString(),
      });
      return;
    }

    if (p === "/api/connect" && req.method === "POST") {
      const body = await readBody(req);
      const result = await connect(body || {});
      sendJson(res, 200, result);
      return;
    }

    if (p.startsWith("/api/")) {
      sendJson(res, 404, { ok: false, error: "not_found" });
      return;
    }

    if (req.method === "GET" || req.method === "HEAD") {
      serveStatic(req, res, p);
      return;
    }

    res.writeHead(405);
    res.end("Method Not Allowed");
  } catch (err) {
    sendJson(res, 500, { ok: false, error: "server_error", detail: String(err && err.message) });
  }
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`[huawei-connect] http://127.0.0.1:${PORT}/`);
  console.log(`[huawei-connect] frontend: ${FRONTEND}`);
  console.log(`[huawei-connect] ima_api: ${fs.existsSync(IMA_API) ? IMA_API : "MISSING"}`);
  console.log(`[huawei-connect] credentials: ${hasCredentials() ? "yes" : "no"}`);
  console.log(`[huawei-connect] local_kb: ${resolveLocalKbPath()}`);
});
