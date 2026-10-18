/**
 * Evidence / product images: Plan A (ima) then Plan B (local KB).
 * Credentials: process.env only (loaded from project .env by connect-server).
 */
"use strict";

const fs = require("fs");
const path = require("path");
const http = require("http");
const https = require("https");
const crypto = require("crypto");

const IMAGE_EXT = new Set([".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"]);
const MEDIA_TYPE_IMAGE = 9;

function ensureDir(p) {
  fs.mkdirSync(p, { recursive: true });
}

function isImageFilename(name) {
  const ext = path.extname(String(name || "")).toLowerCase();
  return IMAGE_EXT.has(ext);
}

/** Resolve path under root; returns null if escape attempted. */
function resolveUnderRoot(root, relOrAbs) {
  if (!root) return null;
  const rootAbs = path.resolve(root);
  let candidate;
  if (!relOrAbs) return null;
  const raw = String(relOrAbs);
  if (path.isAbsolute(raw) || /^[A-Za-z]:[\\/]/.test(raw)) {
    candidate = path.resolve(raw);
  } else {
    candidate = path.resolve(rootAbs, raw);
  }
  const rootNorm = rootAbs.replace(/[\\/]+$/, "");
  const candNorm = candidate;
  if (
    candNorm !== rootNorm &&
    !candNorm.startsWith(rootNorm + path.sep) &&
    !candNorm.startsWith(rootNorm + "/") &&
    !candNorm.startsWith(rootNorm + "\\")
  ) {
    // Windows case-insensitive compare
    const a = rootNorm.toLowerCase();
    const b = candNorm.toLowerCase();
    if (b !== a && !b.startsWith(a + path.sep.toLowerCase()) && !b.startsWith(a + "\\") && !b.startsWith(a + "/")) {
      return null;
    }
  }
  return candidate;
}

function relativePosix(root, full) {
  return path.relative(root, full).split(path.sep).join("/");
}

function parseCsvLine(line) {
  const out = [];
  let cur = "";
  let inQ = false;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (inQ) {
      if (c === '"' && line[i + 1] === '"') {
        cur += '"';
        i++;
      } else if (c === '"') {
        inQ = false;
      } else {
        cur += c;
      }
    } else if (c === '"') {
      inQ = true;
    } else if (c === ",") {
      out.push(cur);
      cur = "";
    } else {
      cur += c;
    }
  }
  out.push(cur);
  return out;
}

function parseCsv(text) {
  const lines = String(text || "")
    .replace(/^\uFEFF/, "")
    .split(/\r?\n/)
    .filter((l) => l.trim());
  if (!lines.length) return { headers: [], rows: [] };
  const headers = parseCsvLine(lines[0]).map((h) => h.trim());
  const rows = [];
  for (let i = 1; i < lines.length; i++) {
    const cols = parseCsvLine(lines[i]);
    const obj = {};
    headers.forEach((h, idx) => {
      obj[h] = cols[idx] != null ? cols[idx] : "";
    });
    rows.push(obj);
  }
  return { headers, rows };
}

function scoreModelMatch(model, query) {
  const m = String(model || "").toLowerCase();
  const q = String(query || "").toLowerCase().trim();
  if (!q) return 1;
  if (!m) return 0;
  if (m.includes(q) || q.includes(m)) return 3;
  const tokens = q.split(/[\s\/\-_]+/).filter((t) => t.length >= 2);
  let hit = 0;
  for (const t of tokens) {
    if (m.includes(t)) hit += 1;
  }
  if (hit >= 2) return 2;
  if (hit === 1) return 1;
  // common aliases
  if (/x\s*pro/i.test(q) && /x\s*pro/i.test(m)) return 3;
  if (/matebook\s*14/i.test(q) && /matebook\s*14/i.test(m)) return 3;
  if (/matebook\s*pro/i.test(q) && /matebook\s*pro/i.test(m) && !/x\s*pro/i.test(m)) return 2;
  return 0;
}

function findGlobalIndexCsv(kbRoot) {
  if (!kbRoot || !fs.existsSync(kbRoot)) return null;
  const stack = [kbRoot];
  let found = null;
  let walked = 0;
  while (stack.length && walked < 5000) {
    const dir = stack.pop();
    let entries;
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const ent of entries) {
      walked += 1;
      const full = path.join(dir, ent.name);
      if (ent.isDirectory()) {
        if (ent.name === ".git" || ent.name === "node_modules") continue;
        stack.push(full);
      } else if (ent.isFile() && /图片资源汇总|全系图片|图片索引/.test(ent.name) && ent.name.endsWith(".csv")) {
        if (/汇总|全系/.test(ent.name)) return full;
        if (!found) found = full;
      }
    }
  }
  return found;
}

function findFileByNameUnder(kbRoot, fileName, preferRelDir) {
  if (!fileName) return null;
  if (preferRelDir) {
    const direct = resolveUnderRoot(kbRoot, path.join(preferRelDir, "images", fileName));
    if (direct && fs.existsSync(direct)) return direct;
    const direct2 = resolveUnderRoot(kbRoot, path.join(preferRelDir, fileName));
    if (direct2 && fs.existsSync(direct2)) return direct2;
  }
  // shallow search by basename (cap)
  const stack = [kbRoot];
  let walked = 0;
  while (stack.length && walked < 8000) {
    const dir = stack.pop();
    let entries;
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const ent of entries) {
      walked += 1;
      const full = path.join(dir, ent.name);
      if (ent.isDirectory()) {
        if (ent.name === ".git" || ent.name === "node_modules") continue;
        stack.push(full);
      } else if (ent.isFile() && ent.name === fileName) {
        return full;
      }
    }
  }
  return null;
}

function scanLocalImages(kbRoot, query, limit) {
  const lim = Math.max(1, Math.min(Number(limit) || 6, 20));
  const images = [];
  if (!kbRoot || !fs.existsSync(kbRoot)) {
    return { ok: false, error: "local_kb_missing", images: [], detail: `目录不存在：${kbRoot}` };
  }

  const indexPath = findGlobalIndexCsv(kbRoot);
  if (indexPath) {
    try {
      const text = fs.readFileSync(indexPath, "utf8");
      const { rows } = parseCsv(text);
      const scored = [];
      for (const row of rows) {
        const fileName =
          row["文件名"] || row["filename"] || row["file"] || row["图片文件"] || Object.values(row)[0] || "";
        const model = row["产品型号"] || row["型号"] || row["model"] || "";
        const caption =
          row["中文说明"] ||
          row["说明"] ||
          row["中文图片说明"] ||
          row["caption"] ||
          row["描述"] ||
          fileName;
        const relDir = row["相对目录"] || row["目录"] || row["path"] || "";
        const sc = scoreModelMatch(model + " " + fileName + " " + caption, query);
        if (query && sc <= 0) continue;
        scored.push({ fileName, model, caption, relDir, score: sc || 1 });
      }
      scored.sort((a, b) => b.score - a.score);
      for (const item of scored) {
        if (images.length >= lim) break;
        if (!item.fileName || !isImageFilename(item.fileName)) continue;
        const full = findFileByNameUnder(kbRoot, item.fileName, item.relDir);
        if (!full) continue;
        const rel = relativePosix(kbRoot, full);
        images.push({
          id: `local_${crypto.createHash("sha1").update(rel).digest("hex").slice(0, 10)}`,
          caption: item.caption || item.fileName,
          matched_model: item.model || query || "",
          source: `local:${rel}`,
          url: `/api/local-file?path=${encodeURIComponent(rel)}`,
          media_id: null,
          mode: "local",
        });
      }
    } catch (err) {
      // fall through to walk
    }
  }

  if (!images.length && indexPath) /* 未匹配时回退任意图 */ {
    try {
      const text = fs.readFileSync(indexPath, "utf8");
      const { rows } = parseCsv(text);
      for (const row of rows) {
        if (images.length >= lim) break;
        const fileName = row["文件名"] || Object.values(row)[0] || "";
        const model = row["产品型号"] || "";
        const caption = row["中文说明"] || row["说明"] || row["中文图片说明"] || fileName;
        const relDir = row["相对目录"] || "";
        if (!fileName || !isImageFilename(fileName)) continue;
        const full = findFileByNameUnder(kbRoot, fileName, relDir);
        if (!full) continue;
        const rel = relativePosix(kbRoot, full);
        images.push({
          id: `local_${crypto.createHash("sha1").update(rel).digest("hex").slice(0, 10)}`,
          caption: caption || fileName,
          matched_model: model || query || "",
          source: `local:${rel}`,
          url: `/api/local-file?path=${encodeURIComponent(rel)}`,
          media_id: null,
          mode: "local",
        });
      }
    } catch (_) {}
  }

  if (images.length < lim) {
    // walk images/ dirs matching query
    const stack = [kbRoot];
    let walked = 0;
    const candidates = [];
    while (stack.length && walked < 10000 && candidates.length < 200) {
      const dir = stack.pop();
      let entries;
      try {
        entries = fs.readdirSync(dir, { withFileTypes: true });
      } catch {
        continue;
      }
      for (const ent of entries) {
        walked += 1;
        const full = path.join(dir, ent.name);
        if (ent.isDirectory()) {
          if (ent.name === ".git" || ent.name === "node_modules") continue;
          stack.push(full);
        } else if (ent.isFile() && isImageFilename(ent.name)) {
          const rel = relativePosix(kbRoot, full);
          const sc = scoreModelMatch(rel, query);
          if (query && sc <= 0 && !/images|图片/i.test(dir)) continue;
          if (query && sc <= 0) continue;
          candidates.push({ full, rel, score: sc || 1, name: ent.name });
        }
      }
    }
    candidates.sort((a, b) => b.score - a.score);
    const seen = new Set(images.map((i) => i.source));
    for (const c of candidates) {
      if (images.length >= lim) break;
      const src = `local:${c.rel}`;
      if (seen.has(src)) continue;
      seen.add(src);
      images.push({
        id: `local_${crypto.createHash("sha1").update(c.rel).digest("hex").slice(0, 10)}`,
        caption: c.name,
        matched_model: query || "",
        source: src,
        url: `/api/local-file?path=${encodeURIComponent(c.rel)}`,
        media_id: null,
        mode: "local",
      });
    }
  }

  return {
    ok: images.length > 0,
    mode: "local",
    images,
    detail: images.length
      ? `本地库匹配 ${images.length} 张图`
      : `本地库未找到与「${query || ""}」匹配的图片`,
    local_path: kbRoot,
  };
}

function downloadToFile(url, headers, destPath, timeoutMs = 30000) {
  return new Promise((resolve, reject) => {
    const lib = url.startsWith("https") ? https : http;
    const req = lib.get(
      url,
      { headers: headers || {}, timeout: timeoutMs },
      (res) => {
        if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
          res.resume();
          downloadToFile(res.headers.location, headers, destPath, timeoutMs).then(resolve, reject);
          return;
        }
        if (res.statusCode !== 200) {
          res.resume();
          reject(new Error(`HTTP ${res.statusCode}`));
          return;
        }
        ensureDir(path.dirname(destPath));
        const ws = fs.createWriteStream(destPath);
        res.pipe(ws);
        ws.on("finish", () => resolve(destPath));
        ws.on("error", reject);
      }
    );
    req.on("error", reject);
    req.on("timeout", () => {
      req.destroy();
      reject(new Error("download timeout"));
    });
  });
}

function guessExtFromUrlOrType(url, contentType) {
  try {
    const u = new URL(url);
    const ext = path.extname(u.pathname).toLowerCase();
    if (IMAGE_EXT.has(ext)) return ext;
  } catch (_) {}
  const ct = String(contentType || "").toLowerCase();
  if (ct.includes("png")) return ".png";
  if (ct.includes("webp")) return ".webp";
  if (ct.includes("gif")) return ".gif";
  if (ct.includes("jpeg") || ct.includes("jpg")) return ".jpg";
  return ".jpg";
}

/**
 * @param {object} deps
 * @param {function} deps.runImaApi
 * @param {function} deps.apiOk
 * @param {function} deps.unwrapData
 * @param {string} deps.cacheDir
 * @param {function} deps.hasCredentials
 */
function createEvidenceHandlers(deps) {
  const { runImaApi, apiOk, unwrapData, cacheDir, hasCredentials } = deps;
  ensureDir(cacheDir);

  async function cacheMedia(mediaId, creds) {
    const safeId = String(mediaId).replace(/[^a-zA-Z0-9_-]/g, "_").slice(0, 120);
    const metaPath = path.join(cacheDir, safeId + ".json");
    if (fs.existsSync(metaPath)) {
      try {
        const meta = JSON.parse(fs.readFileSync(metaPath, "utf8"));
        if (meta.file && fs.existsSync(path.join(cacheDir, meta.file))) {
          return { ok: true, cache_file: meta.file, media_id: mediaId, from_cache: true };
        }
      } catch (_) {}
    }

    const r = await runImaApi("openapi/wiki/v1/get_media_info", { media_id: mediaId }, creds);
    if (!r.ok || !apiOk(r.data)) {
      return { ok: false, error: "get_media_info_failed", detail: (r.data && r.data.msg) || r.msg };
    }
    const data = unwrapData(r.data);
    const mediaType = Number(data.media_type);
    const urlInfo = data.url_info || {};
    const url = urlInfo.url;
    if (!url) {
      return { ok: false, error: "no_url", media_type: mediaType };
    }
    // Prefer images; still allow if filename looks like image
    const ext = guessExtFromUrlOrType(url, "");
    const fileName = safeId + ext;
    const dest = path.join(cacheDir, fileName);
    try {
      await downloadToFile(url, urlInfo.headers || {}, dest);
    } catch (err) {
      return { ok: false, error: "download_failed", detail: String(err.message || err) };
    }
    fs.writeFileSync(
      metaPath,
      JSON.stringify({ media_id: mediaId, file: fileName, media_type: mediaType, cached_at: new Date().toISOString() }),
      "utf8"
    );
    return { ok: true, cache_file: fileName, media_id: mediaId, media_type: mediaType };
  }

  async function tryImaImages(opts) {
    const { kb_id, query, limit, creds } = opts;
    const lim = Math.max(1, Math.min(Number(limit) || 6, 12));
    if (!hasCredentials(creds || {})) {
      return { ok: false, error: "no_credentials", images: [], detail: "未配置 IMA 凭证（环境变量 / 项目 .env）" };
    }
    if (!kb_id) {
      return { ok: false, error: "no_kb_id", images: [], detail: "缺少 knowledge_base_id" };
    }

    const queries = [];
    const q = String(query || "").trim();
    if (q) {
      queries.push(q);
      queries.push(q + " 图片");
      queries.push(q.replace(/2024|2025|2026/g, "").trim());
    }
    queries.push("MateBook 产品图");
    queries.push("产品外观");

    const seen = new Set();
    const candidates = [];

    for (const sq of queries) {
      if (!sq) continue;
      const r = await runImaApi(
        "openapi/wiki/v1/search_knowledge",
        { query: sq, knowledge_base_id: kb_id, cursor: "" },
        creds
      );
      if (!r.ok || !apiOk(r.data)) continue;
      const data = unwrapData(r.data);
      const list = data.info_list || data.list || [];
      for (const item of list) {
        const mid = item.media_id || item.id || "";
        const title = item.title || item.name || "";
        if (!mid || seen.has(mid)) continue;
        seen.add(mid);
        const looksImg = isImageFilename(title) || /图|外观|配色|产品图|images?/i.test(title);
        candidates.push({
          media_id: mid,
          title,
          score: looksImg ? 2 : 1,
        });
      }
      if (candidates.filter((c) => c.score >= 2).length >= lim) break;
    }

    candidates.sort((a, b) => b.score - a.score);

    const images = [];
    for (const c of candidates) {
      if (images.length >= lim) break;
      const cached = await cacheMedia(c.media_id, creds);
      if (!cached.ok) continue;
      // If media_type known and not image and not image ext, skip unless we have few
      if (
        cached.media_type != null &&
        cached.media_type !== MEDIA_TYPE_IMAGE &&
        !isImageFilename(cached.cache_file) &&
        images.length > 0
      ) {
        continue;
      }
      if (!isImageFilename(cached.cache_file) && cached.media_type !== MEDIA_TYPE_IMAGE) {
        // skip non-image binaries (pdf etc.)
        try {
          fs.unlinkSync(path.join(cacheDir, cached.cache_file));
        } catch (_) {}
        continue;
      }
      images.push({
        id: c.media_id,
        caption: c.title || "ima 配图",
        matched_model: q || "",
        source: `ima:${c.media_id}`,
        url: `/api/cache/${encodeURIComponent(cached.cache_file)}`,
        media_id: c.media_id,
        mode: "ima",
      });
    }

    return {
      ok: images.length > 0,
      mode: "ima",
      images,
      detail: images.length ? `ima 取到 ${images.length} 张图` : "ima 搜索未返回可用图片",
      kb_id,
    };
  }

  async function fetchEvidence(body, resolveLocalKbPath) {
    const prefer = (body && body.prefer) || "auto"; // auto | ima | local
    const query = (body && (body.query || body.model || body.product_hint)) || "";
    const limit = (body && body.limit) || 6;
    const kb_id = body && body.knowledge_base_id;
    const creds = {
      client_id: body && body.client_id,
      api_key: body && body.api_key,
    };
    const localPath = resolveLocalKbPath(body && body.local_path);

    if (prefer === "local") {
      const b = scanLocalImages(localPath, query, limit);
      return { ...b, prefer };
    }

    if (prefer === "ima") {
      const a = await tryImaImages({ kb_id, query, limit, creds });
      if (a.ok) return a;
      return { ...a, fallback_local: scanLocalImages(localPath, query, limit) };
    }

    // auto: A then B
    let a = { ok: false, images: [], detail: "skip_ima" };
    if (kb_id && hasCredentials(creds)) {
      a = await tryImaImages({ kb_id, query, limit, creds });
      if (a.ok) return a;
    } else if (!hasCredentials(creds)) {
      a = { ok: false, error: "no_credentials", images: [], detail: "未配置凭证，改用本地库" };
    } else if (!kb_id) {
      a = { ok: false, error: "no_kb_id", images: [], detail: "无 kb_id，改用本地库" };
    }

    const b = scanLocalImages(localPath, query, limit);
    if (b.ok) {
      return {
        ...b,
        title: "本地知识库配图",
        detail: `${b.detail}（云端：${a.detail || a.error || "无图"}）`,
        ima_error: a.error,
        ima_detail: a.detail,
      };
    }
    return {
      ok: false,
      mode: "none",
      images: [],
      detail: `云端：${a.detail || a.error}；本地：${b.detail || b.error}`,
      error: "both_failed",
    };
  }

  function serveLocalFile(req, res, u, resolveLocalKbPath) {
    const rel = u.searchParams.get("path") || "";
    const rootOverride = u.searchParams.get("root") || "";
    const kbRoot = resolveLocalKbPath(rootOverride || undefined);
    const full = resolveUnderRoot(kbRoot, decodeURIComponent(rel));
    if (!full || !fs.existsSync(full) || !fs.statSync(full).isFile()) {
      res.writeHead(404, { "Content-Type": "application/json; charset=utf-8" });
      res.end(JSON.stringify({ ok: false, error: "not_found" }));
      return;
    }
    if (!isImageFilename(full)) {
      res.writeHead(403, { "Content-Type": "application/json; charset=utf-8" });
      res.end(JSON.stringify({ ok: false, error: "not_image" }));
      return;
    }
    const ext = path.extname(full).toLowerCase();
    const mime =
      { ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif" }[
        ext
      ] || "application/octet-stream";
    res.writeHead(200, {
      "Content-Type": mime,
      "Cache-Control": "public, max-age=3600",
      "Access-Control-Allow-Origin": "*",
    });
    fs.createReadStream(full).pipe(res);
  }

  function serveCache(req, res, fileParam) {
    const name = path.basename(decodeURIComponent(fileParam || ""));
    if (!name || name.includes("..")) {
      res.writeHead(400);
      res.end("bad name");
      return;
    }
    const full = path.join(cacheDir, name);
    if (!full.startsWith(cacheDir) || !fs.existsSync(full)) {
      res.writeHead(404);
      res.end("not found");
      return;
    }
    const ext = path.extname(full).toLowerCase();
    const mime =
      { ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif" }[
        ext
      ] || "application/octet-stream";
    res.writeHead(200, {
      "Content-Type": mime,
      "Cache-Control": "public, max-age=86400",
      "Access-Control-Allow-Origin": "*",
    });
    fs.createReadStream(full).pipe(res);
  }

  async function serveMediaProxy(req, res, u, getCredsFromQuery) {
    const mediaId = u.searchParams.get("media_id");
    if (!mediaId) {
      res.writeHead(400, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ ok: false, error: "media_id required" }));
      return;
    }
    const creds = getCredsFromQuery ? getCredsFromQuery() : {};
    const cached = await cacheMedia(mediaId, creds);
    if (!cached.ok) {
      res.writeHead(502, { "Content-Type": "application/json" });
      res.end(JSON.stringify(cached));
      return;
    }
    serveCache(req, res, cached.cache_file);
  }

  return {
    fetchEvidence,
    serveLocalFile,
    serveCache,
    serveMediaProxy,
    scanLocalImages,
    cacheMedia,
  };
}

module.exports = {
  createEvidenceHandlers,
  resolveUnderRoot,
  scanLocalImages,
  isImageFilename,
};
