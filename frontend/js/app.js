/**
 * 华为PC营销软文智能体 · SPA 应用逻辑
 */
(function () {
  "use strict";

  const M = window.HWMock;
  const PAGES = ["connect", "task", "strategy", "draft", "revise"];
  const PAGE_LABELS = {
    connect: "连接",
    task: "任务",
    strategy: "策略",
    draft: "成稿",
    revise: "修订",
  };

  const state = {
    page: "connect",
    kbConnected: false,
    connectMode: "none", // ima | local | none
    connectInfo: null,
    connecting: false,
    unlocked: { connect: true, task: false, strategy: false, draft: false, revise: false },
    task: M.defaultTaskSpec(),
    plan: null,
    evidence: null,
    article: null,
    report: null,
    segments: null,
    prevArticle: null,
    pipelineRunning: false,
  };

  function $(sel, root) {
    return (root || document).querySelector(sel);
  }
  function $all(sel, root) {
    return Array.from((root || document).querySelectorAll(sel));
  }

  function formatTime(d) {
    const pad = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}（Asia/Shanghai）`;
  }

  function toast(msg) {
    const el = $("#toast");
    el.textContent = msg;
    el.classList.add("show");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => el.classList.remove("show"), 2200);
  }

  function setHash(page) {
    if (location.hash.replace(/^#/, "") !== page) {
      location.hash = page;
    }
  }

  function canEnter(page) {
    if (page === "connect") return true;
    if (page === "task") return state.unlocked.task;
    if (page === "strategy") return state.unlocked.strategy;
    if (page === "draft") return state.unlocked.draft;
    if (page === "revise") {
      return state.unlocked.revise && state.report && state.report.overall !== "FAIL";
    }
    return false;
  }

  function go(page, opts) {
    if (!PAGES.includes(page)) return;
    if (!canEnter(page)) {
      toast("请先完成前面的步骤");
      return;
    }
    state.page = page;
    $all(".page").forEach((p) => {
      p.classList.toggle("active", p.dataset.page === page);
    });
    updateStepNav();
    updateTopbar();
    if (!opts || !opts.skipHash) setHash(page);
    if (page === "task") renderTaskForm();
    if (page === "strategy") renderStrategy();
    if (page === "draft") renderDraft();
    if (page === "revise") renderRevise();
    if (page === "connect") renderConnect();
  }

  function updateStepNav() {
    $all(".step-nav-item").forEach((btn) => {
      const p = btn.dataset.page;
      btn.classList.remove("active", "done", "locked");
      const idx = PAGES.indexOf(p);
      const cur = PAGES.indexOf(state.page);
      if (p === state.page) btn.classList.add("active");
      else if (idx < cur && state.unlocked[p]) btn.classList.add("done");
      if (!canEnter(p)) btn.classList.add("locked");
      btn.setAttribute("aria-current", p === state.page ? "step" : "false");
    });
  }

  function updateTopbar() {
    const light = $("#kb-light");
    light.classList.toggle("on", state.kbConnected);
    light.classList.toggle("local", state.kbConnected && state.connectMode === "local");
    let label = "未连接";
    if (state.kbConnected && state.connectMode === "ima") label = "已连 ima 云端";
    else if (state.kbConnected && state.connectMode === "local") label = "已用本地知识库";
    else if (state.kbConnected) label = "知识库已连接";
    $("#kb-light-text").textContent = label;
    const mask = $("#account-mask");
    if (state.connectMode === "ima" && state.connectInfo && state.connectInfo.kb_name) {
      mask.hidden = false;
      mask.textContent = state.connectInfo.kb_name;
    } else if (state.connectMode === "local") {
      mask.hidden = false;
      mask.textContent = "本地库";
    } else {
      mask.hidden = true;
      mask.textContent = "";
    }
  }

  /* —— Connect —— */
  const CRED_KEY = "hw_ima_session_creds";
  const API_BASE = (function () {
    try {
      if (location.protocol === "http:" || location.protocol === "https:") {
        return location.origin;
      }
    } catch (_) {}
    return "http://127.0.0.1:8787";
  })();

  function loadSessionCreds() {
    try {
      const raw = sessionStorage.getItem(CRED_KEY);
      if (!raw) return {};
      const j = JSON.parse(raw);
      return {
        client_id: j.client_id || "",
        api_key: j.api_key || "",
      };
    } catch (_) {
      return {};
    }
  }

  function saveSessionCreds(creds) {
    sessionStorage.setItem(
      CRED_KEY,
      JSON.stringify({
        client_id: (creds.client_id || "").trim(),
        api_key: (creds.api_key || "").trim(),
      })
    );
  }

  function clearSessionCreds() {
    sessionStorage.removeItem(CRED_KEY);
    const a = $("#adv-client-id");
    const b = $("#adv-api-key");
    if (a) a.value = "";
    if (b) b.value = "";
  }

  function setConnectUi(info) {
    const box = $("#connect-status");
    const title = $("#connect-title");
    const detail = $("#connect-detail");
    const result = $("#connect-result");
    const main = $("#connect-result-main");
    const details = $("#connect-kb-details");
    const kbId = $("#connect-kb-id");
    const hint = $("#connect-hint");
    const btnNext = $("#btn-confirm-kb");
    const btnReconnect = $("#btn-reconnect");

    const mode = (info && info.mode) || "none";
    const ok = Boolean(info && info.ok);
    let stateName = "idle";
    if (state.connecting) stateName = "loading";
    else if (ok && mode === "ima") stateName = "ima";
    else if (ok && mode === "local") stateName = "local";
    else if (info && info.error) stateName = "fail";
    box.dataset.state = stateName;

    if (state.connecting) {
      title.textContent = "正在连接…";
      detail.textContent = "先试 ima 云端，不通再扫本地知识库。";
      result.hidden = true;
      hint.hidden = true;
      btnNext.disabled = true;
      return;
    }

    if (ok && mode === "ima") {
      title.textContent = "已连 ima 云端";
      detail.textContent = info.detail || "云端知识库可用";
      result.hidden = false;
      main.textContent = info.kb_name
        ? `「${info.kb_name}」${info.item_hint != null ? " · " + (info.detail || "") : ""}`
        : info.detail || "";
      if (info.kb_id) {
        details.hidden = false;
        kbId.textContent = info.kb_id;
      } else {
        details.hidden = true;
      }
      hint.hidden = true;
      btnNext.disabled = false;
      btnReconnect.hidden = false;
      return;
    }

    if (ok && mode === "local") {
      title.textContent = "已用本地知识库";
      detail.textContent = info.detail || "本地目录可用";
      result.hidden = false;
      const pathLine = info.local_path ? `路径：${info.local_path}` : "";
      main.textContent = [info.detail, pathLine].filter(Boolean).join("\n");
      details.hidden = true;
      hint.hidden = true;
      btnNext.disabled = false;
      btnReconnect.hidden = false;
      return;
    }

    title.textContent = (info && info.title) || "未连接";
    detail.textContent =
      (info && info.detail) || "点击「连接知识库」，优先云端，失败自动本地。";
    result.hidden = true;
    btnNext.disabled = true;
    btnReconnect.hidden = !info;

    if (info && (info.error === "no_credentials" || /未配置凭证|凭证/.test(info.detail || ""))) {
      hint.hidden = false;
      hint.textContent =
        "未配置凭证，将尝试本地库。也可在下方「高级」粘贴本次会话 Client ID / API Key。";
    } else if (info && /请先运行|ECONNREFUSED|Failed to fetch|NetworkError|连接服务/.test(String(info.detail || info.error || ""))) {
      hint.hidden = false;
      hint.innerHTML =
        "探测服务未启动。请双击运行项目根目录的 <strong>启动连接服务.bat</strong>，再打开本页（推荐地址 http://127.0.0.1:8787/）。仍可点「仅用本地库」尝试。";
    } else if (info && !ok) {
      hint.hidden = false;
      hint.textContent = info.detail || "连接失败，可重试或改用本地库。";
    } else {
      hint.hidden = true;
    }
  }

  function applyConnectSuccess(info) {
    state.kbConnected = true;
    state.connectMode = info.mode;
    state.connectInfo = info;
    M.DEMO_KB.name = info.kb_name || (info.mode === "local" ? "本地华为PC知识库" : "");
    M.DEMO_KB.kb_id = info.kb_id || "";
    M.DEMO_KB.status = "connected";
    M.DEMO_KB.mode = info.mode;
    M.DEMO_KB.detail = info.detail || "";
    M.DEMO_KB.local_path = info.local_path || "";
    M.DEMO_KB.item_hint = info.item_hint;
    M.DEMO_KB.lastProbeAt = formatTime(new Date());
    state.unlocked.task = true;
    setConnectUi(info);
    updateTopbar();
  }

  function applyConnectFail(info) {
    state.kbConnected = false;
    state.connectMode = "none";
    state.connectInfo = info || null;
    state.unlocked.task = false;
    M.DEMO_KB.status = "disconnected";
    M.DEMO_KB.mode = "none";
    setConnectUi(info || { ok: false, mode: "none", title: "未连接" });
    updateTopbar();
  }

  function renderConnect() {
    const creds = loadSessionCreds();
    if ($("#adv-client-id") && creds.client_id) $("#adv-client-id").value = creds.client_id;
    if ($("#adv-api-key") && creds.api_key) $("#adv-api-key").value = creds.api_key;
    if (state.connectInfo) setConnectUi(state.connectInfo);
    else setConnectUi({ ok: false, mode: "none", title: "未连接" });
    $("#btn-confirm-kb").disabled = !state.kbConnected;
  }

  async function callConnectApi(prefer) {
    const creds = loadSessionCreds();
    const fromForm = {
      client_id: ($("#adv-client-id") && $("#adv-client-id").value.trim()) || creds.client_id || "",
      api_key: ($("#adv-api-key") && $("#adv-api-key").value.trim()) || creds.api_key || "",
    };
    const payload = {
      prefer: prefer || "auto",
      client_id: fromForm.client_id || undefined,
      api_key: fromForm.api_key || undefined,
    };
    state.connecting = true;
    setConnectUi({});
    try {
      const res = await fetch(API_BASE + "/api/connect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const info = await res.json();
      state.connecting = false;
      if (info && info.ok) {
        applyConnectSuccess(info);
        toast(info.mode === "ima" ? "已连接 ima 云端" : "已改用本地知识库");
      } else {
        applyConnectFail(info);
        toast((info && info.title) || "连接失败");
      }
    } catch (err) {
      state.connecting = false;
      applyConnectFail({
        ok: false,
        mode: "none",
        title: "探测服务未启动",
        detail: "请先运行启动连接服务.bat，打开 http://127.0.0.1:8787/ 。错误：" + (err && err.message),
        error: "service_unreachable",
      });
      toast("请先启动连接服务");
    }
  }

  function onConfirmKb() {
    if (!state.kbConnected) return;
    state.unlocked.task = true;
    go("task");
    toast("进入任务输入");
  }

  function onConnectClick() {
    callConnectApi("auto");
  }

  function onLocalOnly() {
    callConnectApi("local");
  }

  function onReconnect() {
    callConnectApi("auto");
  }

  function onSaveCreds() {
    const client_id = $("#adv-client-id").value.trim();
    const api_key = $("#adv-api-key").value.trim();
    saveSessionCreds({ client_id, api_key });
    toast(client_id || api_key ? "已保存到本会话" : "会话凭证为空");
  }

  /* —— Task —— */
  function readTaskFromForm() {
    return {
      product_hint: $("#f-product").value.trim(),
      audience: $("#f-audience").value.trim(),
      scenario: $("#f-scenario").value.trim(),
      platform: $("#f-platform").value,
      purchase_stage: $("#f-stage").value.trim(),
      user_question: $("#f-question").value.trim(),
      content_goal: $("#f-goal").value.trim(),
      missing_info: [],
    };
  }

  function renderTaskForm() {
    const t = state.task;
    $("#f-product").value = t.product_hint || "";
    $("#f-audience").value = t.audience || "";
    $("#f-scenario").value = t.scenario || "";
    $("#f-platform").value = t.platform || "小红书";
    $("#f-stage").value = t.purchase_stage || "";
    $("#f-question").value = t.user_question || "";
    $("#f-goal").value = t.content_goal || "";
    updateTaskPreview();
  }

  function updateTaskPreview() {
    const t = readTaskFromForm();
    const missing = M.validateTask(t);
    const bar = $("#missing-bar");
    if (missing.length) {
      bar.classList.add("show");
      bar.innerHTML = `<strong>缺项追问：</strong>请补全 ${missing.join("、")}，补完后才能生成策略。`;
    } else {
      bar.classList.remove("show");
      bar.innerHTML = "";
    }
    $("#task-preview").innerHTML = `<span>一句话预览：</span>为 <strong>${t.audience || "？"}</strong>，在 <strong>${t.scenario || "？"}</strong> 场景，发 <strong>${t.platform || "？"}</strong>，目标 <strong>${t.content_goal || "？"}</strong> · 产品 <strong>${t.product_hint || "？"}</strong>`;
    $("#btn-gen-plan").disabled = missing.length > 0;
  }

  function onGenPlan() {
    const t = readTaskFromForm();
    const missing = M.validateTask(t);
    t.missing_info = missing;
    if (missing.length) {
      updateTaskPreview();
      toast("还有缺项，请先补全");
      return;
    }
    state.task = t;
    state.plan = M.buildContentPlan(t);
    state.unlocked.strategy = true;
    go("strategy");
    toast("内容策略已生成");
  }

  /* —— Strategy —— */
  function renderStrategy() {
    const plan = state.plan;
    const task = state.task;
    if (!plan) return;
    $("#strategy-tags").innerHTML = [
      ["人群", plan.audience],
      ["场景", plan.scenario],
      ["目标", plan.content_goal],
      ["平台", plan.platform],
      ["产品", plan.product_hint || task.product_hint],
    ]
      .map(([k, v]) => `<span class="tag"><em>${k}</em>${v}</span>`)
      .join("");

    const cards = [
      ["切角 angle", plan.angle],
      [
        "卖点顺序",
        `<ul>${plan.highlight_order.map((x) => `<li>${x}</li>`).join("")}</ul>`,
      ],
      [
        "结构大纲",
        `<ul>${plan.structure.map((x) => `<li>${x}</li>`).join("")}</ul>`,
      ],
      ["语气 tone", plan.tone],
      ["配图数", String(plan.image_count)],
      ["行动引导 CTA", plan.cta],
    ];
    $("#plan-grid").innerHTML = cards
      .map(
        ([k, v]) =>
          `<div class="plan-card"><div class="k">${k}</div><div class="v">${v}</div></div>`
      )
      .join("");
    $("#plan-why").textContent = plan.why;
  }

  /* —— Pipeline + Draft —— */
  function showPipeline(onDone) {
    const overlay = $("#pipeline-overlay");
    const list = $("#pipeline-list");
    list.innerHTML = M.PIPELINE_LAYERS.map(
      (l) =>
        `<li class="pipeline-item" data-id="${l.id}"><span class="pip-dot"></span><span class="pip-label">${l.id}. ${l.name}<br><span style="font-size:11px;color:var(--muted)">${l.sub}</span></span><span class="pip-status">IDLE</span></li>`
    ).join("");
    overlay.classList.add("show");
    state.pipelineRunning = true;

    const items = $all(".pipeline-item", list);
    let i = 0;
    const reduce =
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const stepMs = reduce ? 80 : 420;

    function tick() {
      if (i > 0) {
        const prev = items[i - 1];
        prev.classList.remove("running");
        prev.classList.add("done");
        prev.querySelector(".pip-status").textContent = "DONE";
      }
      if (i >= items.length) {
        state.pipelineRunning = false;
        setTimeout(() => {
          overlay.classList.remove("show");
          onDone && onDone();
        }, reduce ? 50 : 280);
        return;
      }
      items[i].classList.add("running");
      items[i].querySelector(".pip-status").textContent = "RUN";
      i += 1;
      setTimeout(tick, stepMs);
    }
    setTimeout(tick, 200);
  }

  async function fetchEvidenceImages(task) {
    const info = state.connectInfo || {};
    const prefer =
      state.connectMode === "local" ? "local" : state.connectMode === "ima" ? "auto" : "auto";
    const payload = {
      prefer,
      knowledge_base_id: info.kb_id || M.DEMO_KB.kb_id || undefined,
      query: task.product_hint || "",
      model: task.product_hint || "",
      limit: (state.plan && state.plan.image_count) || 4,
      local_path: info.local_path || M.DEMO_KB.local_path || undefined,
    };
    try {
      const res = await fetch(API_BASE + "/api/evidence", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      if (data && Array.isArray(data.images) && data.images.length) {
        return data.images;
      }
    } catch (err) {
      console.warn("evidence fetch failed", err);
    }
    return [];
  }

  async function generateDraftBundle(reviseOpts) {
    let task = Object.assign({}, state.task);
    if (reviseOpts && reviseOpts.newPlatform) {
      task.platform = reviseOpts.newPlatform;
      state.task = task;
      state.plan = M.buildContentPlan(task);
    }
    const plan = state.plan || M.buildContentPlan(task);
    state.plan = plan;
    const realImgs = await fetchEvidenceImages(task);
    const evidence =
      typeof M.mergeRealImages === "function"
        ? M.mergeRealImages(task, realImgs)
        : M.buildEvidence(task);
    state.evidence = evidence;
    const article = M.buildArticle(task, plan, evidence, reviseOpts || null);
    state.article = article;
    const report = M.buildVerification(evidence, article);
    state.report = report;
    state.segments = M.buildFourSegments(task, plan, evidence, article, report);
    state.unlocked.draft = true;
    if (report.overall !== "FAIL") {
      state.unlocked.revise = true;
    } else {
      state.unlocked.revise = false;
    }
  }

  function onStartGenerate() {
    showPipeline(() => {
      generateDraftBundle(null).then(() => {
        go("draft");
        const n = (state.evidence && state.evidence.images || []).filter((i) => i.url).length;
        toast(n ? `图文已生成（${n} 张真图）` : "图文已生成，核验完成");
      });
    });
  }

  function renderDraft() {
    if (!state.article) return;
    renderEvidenceCol();
    renderManuscript();
    renderSealCol();
    const locked = state.report && state.report.overall === "FAIL";
    $("#btn-to-revise").disabled = locked;
    $("#draft-fail-hint").style.display = locked ? "block" : "none";
  }

  function renderEvidenceCol() {
    const ev = state.evidence;
    $("#fact-list").innerHTML = ev.facts
      .map((f) => {
        if (f.unconfirmed || !f.value) {
          return `<div class="fact-item"><div class="fk">${f.key}</div><div class="fv">待确认 <span class="badge badge-warn">无依据</span></div><div class="src">${f.title || "—"}</div></div>`;
        }
        return `<div class="fact-item"><div class="fk">${f.key}</div><div class="fv">${f.value}</div><div class="src">${f.source}</div></div>`;
      })
      .join("");
    $("#img-list").innerHTML = ev.images
      .map((img) => {
        const thumb = img.url
          ? `<div class="img-thumb has-img"><img src="${escapeHtml(img.url)}" alt="${escapeHtml(img.desc || "")}" loading="lazy" /></div>`
          : `<div class="img-thumb">${escapeHtml(img.id)}</div>`;
        return `<div class="img-item">${thumb}<div class="desc">${escapeHtml(img.desc || "")}</div><div class="model">匹配型号 · ${escapeHtml(img.matched_model || "")}</div><div class="src">${escapeHtml(img.source || "")}</div></div>`;
      })
      .join("");
  }

  function figureHtml(il) {
    const inner = il.url
      ? `<img class="img-real" src="${escapeHtml(il.url)}" alt="${escapeHtml(il.caption || "")}" loading="lazy" />`
      : `<div class="img-placeholder">配图暂缺<br>${escapeHtml(il.image_id || "")}<br>${escapeHtml(il.caption || "")}</div>`;
    return `<figure class="img-slot">${inner}<figcaption class="img-cap">${escapeHtml(il.caption || "")} · <code>${escapeHtml(il.source || "")}</code></figcaption></figure>`;
  }

  function renderManuscript() {
    const a = state.article;
    const layout = a.image_layout || [];
    const parts = a.body.split("\n\n");
    let bodyHtml = "";
    parts.forEach((p, idx) => {
      bodyHtml += `<p class="body-block">${escapeHtml(p)}</p>`;
      // insert remaining images after successive paragraphs (skip index 0 — used after title)
      if (layout[idx + 1]) bodyHtml += figureHtml(layout[idx + 1]);
    });
    // any leftover images beyond paragraph count
    for (let i = parts.length + 1; i < layout.length; i++) {
      bodyHtml += figureHtml(layout[i]);
    }
    const firstImg = layout[0] ? figureHtml(layout[0]) : "";

    $("#manuscript").innerHTML = `
      <div class="meta-row">
        <span class="pill">${escapeHtml(a.platform)}</span>
        <span class="pill">${escapeHtml(a.product_hint)}</span>
        <span class="pill">ima 取证</span>
      </div>
      <h3>${escapeHtml(a.title)}</h3>
      ${firstImg}
      <p class="lead">${escapeHtml(a.lead)}</p>
      ${bodyHtml}
      <div class="cta-box">${escapeHtml(a.cta)}</div>
    `;

    const seg = state.segments;
    $("#tab-scene").textContent = seg["场景判断"];
    $("#tab-kb").textContent = seg["知识库依据"];
    $("#tab-verify").textContent = seg["核验结果"];
    $("#tab-article-plain").textContent = seg["图文软文"];
  }

  function renderSealCol() {
    const r = state.report;
    const seal = $("#seal");
    seal.className = "seal " + (r.overall === "PASS" ? "pass" : r.overall === "WARN" ? "warn" : "fail");
    const label =
      r.overall === "PASS" ? "通过" : r.overall === "WARN" ? "待确认" : "拦截";
    $("#seal-status").textContent = label;
    $("#seal-sub").textContent = r.overall;

    function listHtml(issues) {
      return issues
        .map((i) => {
          const cls = i.level === "ok" ? "ok" : i.level === "warn" ? "warn" : "fail";
          return `<li class="${cls}">${escapeHtml(i.text)}</li>`;
        })
        .join("");
    }
    $("#fact-check-list").innerHTML = listHtml(r.fact_check.issues);
    $("#img-check-list").innerHTML = listHtml(r.image_check.issues);
    $("#comp-check-list").innerHTML = listHtml(r.compliance_check.issues);
    $("#unconfirmed-list").innerHTML = r.unconfirmed.length
      ? r.unconfirmed
          .map(
            (u) =>
              `<li class="warn">${escapeHtml(u.field)}：${escapeHtml(u.reason)}</li>`
          )
          .join("")
      : `<li class="ok">无待确认字段</li>`;
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function setDraftTab(name) {
    $all(".otab").forEach((t) => t.classList.toggle("on", t.dataset.tab === name));
    $all(".otab-panel").forEach((p) =>
      p.classList.toggle("on", p.dataset.tab === name)
    );
  }

  /* —— Revise —— */
  function renderRevise() {
    if (!state.article) return;
    $("#revise-platform").value = state.task.platform;
    $("#revise-cta").value = state.article.cta;
    $("#revise-current-title").textContent = state.article.title;
    if (state.prevArticle) {
      $("#compare-box").style.display = "grid";
      $("#compare-before").textContent = state.prevArticle.title + "\n\n" + state.prevArticle.cta;
      $("#compare-after").textContent = state.article.title + "\n\n" + state.article.cta;
    } else {
      $("#compare-box").style.display = "none";
    }
    // mini manuscript
    $("#revise-preview").innerHTML = `
      <div class="meta-row"><span class="pill">${escapeHtml(state.article.platform)}</span></div>
      <h3 style="font-size:18px">${escapeHtml(state.article.title)}</h3>
      <p class="lead" style="font-size:14px">${escapeHtml(state.article.lead)}</p>
      <p class="body-block" style="font-size:13px">${escapeHtml(state.article.body.slice(0, 280))}${state.article.body.length > 280 ? "…" : ""}</p>
      <div class="cta-box">${escapeHtml(state.article.cta)}</div>
    `;
  }

  function onRerun() {
    const opts = {
      deleteSection: $("#opt-delete").checked,
      changeHighlight: $("#opt-highlight").value || null,
      newCta: $("#revise-cta").value,
      newPlatform: $("#revise-platform").value !== state.task.platform
        ? $("#revise-platform").value
        : null,
    };
    // if platform select changed, always apply
    if ($("#revise-platform").value !== state.task.platform) {
      opts.newPlatform = $("#revise-platform").value;
    }
    state.prevArticle = state.article;
    showPipeline(() => {
      generateDraftBundle(opts).then(() => {
        renderRevise();
        toast("已重跑层 5→6：生成 + 核验");
      });
    });
  }

  function downloadBlob(filename, text, mime) {
    const blob = new Blob([text], { type: mime || "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  function onExport(kind) {
    if (!state.article || !state.report) return;
    const stamp = new Date().toISOString().slice(0, 10);
    if (kind === "copy") {
      const text = M.articleToPlain(state.article, state.report);
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(
          () => toast("已复制到剪贴板"),
          () => toast("复制失败，请改用导出")
        );
      } else {
        toast("当前环境不支持剪贴板，请用导出");
      }
      return;
    }
    if (kind === "md") {
      downloadBlob(
        `华为PC软文_${stamp}.md`,
        M.articleToMarkdown(state.article, state.report),
        "text/markdown;charset=utf-8"
      );
      toast("已导出 Markdown");
      return;
    }
    if (kind === "txt") {
      downloadBlob(
        `华为PC软文_${stamp}.txt`,
        M.articleToPlain(state.article, state.report),
        "text/plain;charset=utf-8"
      );
      toast("已导出纯文本");
    }
  }

  /* —— Bindings —— */
  function bind() {
    $all(".step-nav-item").forEach((btn) => {
      btn.addEventListener("click", () => go(btn.dataset.page));
    });
    $("#btn-confirm-kb").addEventListener("click", onConfirmKb);
    $("#btn-connect").addEventListener("click", onConnectClick);
    $("#btn-local-only").addEventListener("click", onLocalOnly);
    $("#btn-reconnect").addEventListener("click", onReconnect);
    $("#btn-save-creds").addEventListener("click", onSaveCreds);
    $("#btn-clear-creds").addEventListener("click", () => {
      clearSessionCreds();
      toast("已清除会话凭证");
    });
    ["f-product", "f-audience", "f-scenario", "f-platform", "f-stage", "f-question", "f-goal"].forEach(
      (id) => {
        const el = document.getElementById(id);
        el.addEventListener("input", updateTaskPreview);
        el.addEventListener("change", updateTaskPreview);
      }
    );
    $("#btn-gen-plan").addEventListener("click", onGenPlan);
    $("#btn-back-task").addEventListener("click", () => go("task"));
    $("#btn-gen-draft").addEventListener("click", onStartGenerate);
    $("#btn-to-revise").addEventListener("click", () => go("revise"));
    $("#btn-back-strategy").addEventListener("click", () => go("strategy"));
    $all(".otab").forEach((t) => {
      t.addEventListener("click", () => setDraftTab(t.dataset.tab));
    });
    $("#btn-rerun").addEventListener("click", onRerun);
    $("#btn-export-copy").addEventListener("click", () => onExport("copy"));
    $("#btn-export-md").addEventListener("click", () => onExport("md"));
    $("#btn-export-txt").addEventListener("click", () => onExport("txt"));
    $("#btn-revise-back-draft").addEventListener("click", () => go("draft"));

    window.addEventListener("hashchange", () => {
      const page = location.hash.replace(/^#/, "") || "connect";
      if (PAGES.includes(page) && canEnter(page)) {
        go(page, { skipHash: true });
      } else if (PAGES.includes(page)) {
        setHash(state.page);
      }
    });
  }

  function init() {
    bind();
    updateTopbar();
    const initial = location.hash.replace(/^#/, "");
    if (PAGES.includes(initial) && canEnter(initial)) {
      go(initial, { skipHash: true });
    } else {
      go("connect", { skipHash: true });
      setHash("connect");
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
