/**
 * 华为PC营销软文智能体 · Mock 数据与规则
 * 演示用，不接真实 ima / 密钥
 */
(function (global) {
  "use strict";

  const DEMO_ACCOUNT = {
    displayName: "本机用户",
    clientIdMasked: "",
    clientIdLast4: "",
  };

  // 连接态由 connect-server / 前端真实探测填充；默认未连接（不再假绿勾）
  const DEMO_KB = {
    name: "",
    kb_id: "",
    status: "disconnected",
    mode: "none", // ima | local | none
    lastProbeAt: null,
    detail: "",
    local_path: "",
    item_hint: null,
    probes: [],
  };

  const PIPELINE_LAYERS = [
    { id: 1, name: "意图与任务理解", sub: "TaskSpec" },
    { id: 2, name: "场景与平台策略", sub: "ContentPlan" },
    { id: 3, name: "ima 知识库检索", sub: "原文 + 图片" },
    { id: 4, name: "事实点提取", sub: "EvidenceMap" },
    { id: 5, name: "图文编排与软文生成", sub: "DraftArticle" },
    { id: 6, name: "核验与合规拦截", sub: "VerificationReport" },
    { id: 7, name: "反馈与修改就绪", sub: "导出 / 修订" },
  ];

  const PLATFORM_PLANS = {
    小红书: {
      angle: "轻薄+多设备协同+长续航，弱化跑分",
      highlight_order: ["重量", "屏幕护眼", "续航", "超级终端"],
      structure: ["口语化标题", "痛点开场", "3段场景体感", "评论区行动引导"],
      tone: "学姐分享风",
      image_count: 4,
      cta: "评论区扣「1」，到店免费体验真机",
      why: "小红书偏种草与体感：短句、场景化、多图，CTA 放评论互动比硬广转化更好。",
    },
    公众号: {
      angle: "选型决策+参数可信+购机路径",
      highlight_order: ["屏幕", "性能与散热", "续航", "售后与到店"],
      structure: ["信息型标题", "场景引入", "参数分段解读", "对比表意", "结尾到店引导"],
      tone: "理性种草、编辑口吻",
      image_count: 3,
      cta: "文末扫码预约门店体验，顾问一对一答疑",
      why: "公众号读者耐读更长：需要清晰结构与可核验参数，语气偏编辑而非口语。",
    },
    朋友圈: {
      angle: "一句痛点+一张主视觉+轻行动",
      highlight_order: ["轻薄便携", "续航"],
      structure: ["一句痛点", "一句卖点", "主图", "短 CTA"],
      tone: "熟人推荐、克制不煽",
      image_count: 1,
      cta: "私信「体验」预约到店",
      why: "朋友圈注意力极短：单图主视觉 + 两句文案，避免长文与硬促销话术。",
    },
    海报: {
      angle: "视觉主卖点一眼可读",
      highlight_order: ["重量", "续航", "屏幕"],
      structure: ["主标题", "三卖点条", "机型名", "门店 CTA"],
      tone: "简洁有力、零售陈列风",
      image_count: 1,
      cta: "到店体验 MateBook X Pro",
      why: "海报是扫视媒介：大字号卖点 + 单主图，不写长段落，CTA 指向到店。",
    },
  };

  const BASE_EVIDENCE = {
    facts: [
      {
        key: "重量",
        value: "约 1.26kg",
        source: "ima://kb_hw_pc_marketing_demo/article/mbxp2024-spec#weight",
        title: "MateBook X Pro 2024 规格页",
      },
      {
        key: "屏幕",
        value: "14.2 英寸 3.1K 触控全面屏 · 护眼模式",
        source: "ima://kb_hw_pc_marketing_demo/article/mbxp2024-display#panel",
        title: "屏幕与护眼说明",
      },
      {
        key: "续航",
        value: "典型办公场景可达约 12 小时（实验室数据，以实测为准）",
        source: "ima://kb_hw_pc_marketing_demo/article/mbxp2024-battery#office",
        title: "续航测试说明",
      },
      {
        key: "超级终端",
        value: "支持与手机 / 平板多屏协同、键鼠穿梭",
        source: "ima://kb_hw_pc_marketing_demo/article/superdevice#collab",
        title: "超级终端能力说明",
      },
      {
        key: "价格",
        value: null,
        source: null,
        title: "知识库未收录官方报价",
        unconfirmed: true,
      },
    ],
    images: [
      {
        id: "img_001",
        desc: "机身侧视 · 轻薄轮廓",
        source: "ima://kb_hw_pc_marketing_demo/asset/img_001",
        matched_model: "MateBook X Pro 2024",
      },
      {
        id: "img_002",
        desc: "屏幕特写 · 触控全面屏",
        source: "ima://kb_hw_pc_marketing_demo/asset/img_002",
        matched_model: "MateBook X Pro 2024",
      },
      {
        id: "img_003",
        desc: "宿舍 / 图书馆场景示意",
        source: "ima://kb_hw_pc_marketing_demo/asset/img_003",
        matched_model: "MateBook X Pro 2024",
      },
      {
        id: "img_004",
        desc: "手机与 PC 协同界面",
        source: "ima://kb_hw_pc_marketing_demo/asset/img_004",
        matched_model: "MateBook X Pro 2024",
      },
    ],
  };

  function defaultTaskSpec() {
    return {
      product_hint: "MateBook X Pro 2024",
      audience: "大学新生",
      scenario: "开学季",
      platform: "小红书",
      purchase_stage: "信息收集",
      user_question: "兼顾学习、携带、续航",
      content_goal: "种草+到店",
      missing_info: [],
    };
  }

  function validateTask(task) {
    const required = [
      ["product_hint", "产品"],
      ["audience", "人群"],
      ["scenario", "场景"],
      ["platform", "渠道"],
      ["content_goal", "内容目标"],
    ];
    const missing = [];
    required.forEach(([k, label]) => {
      if (!task[k] || String(task[k]).trim() === "") missing.push(label);
    });
    return missing;
  }

  function buildContentPlan(task) {
    const base = PLATFORM_PLANS[task.platform] || PLATFORM_PLANS["小红书"];
    return {
      audience: task.audience,
      scenario: task.scenario,
      content_goal: task.content_goal,
      platform: task.platform,
      product_hint: task.product_hint,
      angle: base.angle,
      highlight_order: base.highlight_order.slice(),
      structure: base.structure.slice(),
      tone: base.tone,
      image_count: base.image_count,
      cta: base.cta,
      why: base.why,
    };
  }

  function mergeRealImages(task, realImages) {
    const facts = BASE_EVIDENCE.facts.map((f) => Object.assign({}, f));
    const want = (PLATFORM_PLANS[task.platform] && PLATFORM_PLANS[task.platform].image_count) || 4;
    let images = [];
    if (Array.isArray(realImages) && realImages.length) {
      images = realImages.slice(0, want).map((img) => ({
        id: img.id || img.media_id || "img",
        desc: img.caption || img.desc || img.id || "配图",
        source: img.source || "",
        matched_model: img.matched_model || task.product_hint,
        url: img.url || "",
        mode: img.mode || "",
      }));
    }
    if (!images.length) {
      images = BASE_EVIDENCE.images.slice(0, want).map((img) =>
        Object.assign({}, img, { matched_model: task.product_hint, url: "" })
      );
    }
    return { facts, images };
  }

  function buildEvidence(task) {
    const facts = BASE_EVIDENCE.facts.map((f) => Object.assign({}, f));
    const images = BASE_EVIDENCE.images
      .slice(0, PLATFORM_PLANS[task.platform]?.image_count || 4)
      .map((img) => Object.assign({}, img, { matched_model: task.product_hint }));
    return { facts, images };
  }

  function buildArticle(task, plan, evidence, reviseOpts) {
    const product = task.product_hint;
    const platform = task.platform;
    let title, lead, sections, cta;

    if (platform === "小红书") {
      title = `开学背它刚刚好｜${product} 轻到忘记包里有电脑`;
      lead = `写给准备拎着电脑穿梭教室、图书馆、咖啡店的${task.audience}：这学期最怕什么？沉、闷、没电。`;
      sections = [
        `先说体感：官方规格页写到整机约 1.26kg，塞进书包后肩膀压力小很多——赶早八也不会嫌弃多带一台电脑。`,
        `屏幕是 14.2 英寸 3.1K 触控全面屏，长时间看课件、划重点不那么刺眼；护眼模式打开后，熬夜赶作业眼睛也舒服一点。`,
        `续航按知识库「典型办公场景」说明，大约能撑住一天的课表流转（实验室数据，以你自己的用法为准）。课间拷 PPT、记笔记，不用到处找插座。`,
        `还有超级终端：手机拍的资料、平板上的草稿，可以和 PC 一起协同——宿舍里手机当副屏，学习流不断档。`,
      ];
      cta = plan.cta;
    } else if (platform === "公众号") {
      title = `${product} 开学选型指南：轻薄、护眼、续航，怎么选才不踩坑`;
      lead = `面向${task.audience}的${task.scenario}购机决策：我们只引用知识库可核验事实，价格未收录处一律标注待确认。`;
      sections = [
        `【便携】规格页标注整机约 1.26kg，适合每日往返宿舍与教学楼的携带需求。`,
        `【屏幕】14.2 英寸 3.1K 触控全面屏，支持护眼模式，适合长时间阅读课件与文档。`,
        `【续航】典型办公场景约 12 小时（实验室数据）。高强度渲染/游戏不在本说明范围内。`,
        `【生态】超级终端支持与手机、平板多屏协同，降低多设备切换成本。`,
      ];
      cta = plan.cta;
    } else if (platform === "朋友圈") {
      title = `${product} · 开学减负装备`;
      lead = `包里少点负担：约 1.26kg，续航够撑一天课。`;
      sections = [`屏幕护眼、能和手机协同。到店摸摸真机再决定。`];
      cta = plan.cta;
    } else {
      title = `${product}`;
      lead = `约 1.26kg · 护眼屏 · 长续航`;
      sections = [`超级终端多设备协同`];
      cta = plan.cta;
    }

    // Revise options
    if (reviseOpts) {
      if (reviseOpts.deleteSection && sections.length > 1) {
        sections = sections.slice(0, -1);
      }
      if (reviseOpts.changeHighlight === "续航优先") {
        sections.unshift(`【本版强化续航】按知识库典型办公说明，约 12 小时量级，减少找插座焦虑。`);
        plan = Object.assign({}, plan, {
          highlight_order: ["续航", "重量", "屏幕护眼", "超级终端"],
        });
      }
      if (reviseOpts.changeHighlight === "屏幕优先") {
        sections.unshift(`【本版强化屏幕】3.1K 触控全面屏 + 护眼模式，适合长时间看课件。`);
      }
      if (reviseOpts.newCta && reviseOpts.newCta.trim()) {
        cta = reviseOpts.newCta.trim();
      }
      if (reviseOpts.newPlatform) {
        // platform change handled by caller rebuilding plan
      }
    }

    // Never invent price
    const priceFact = evidence.facts.find((f) => f.key === "价格");
    const priceNote = !priceFact || !priceFact.value
      ? `\n\n（价格：知识库暂无依据，标为「待确认」，本稿不写具体报价或补贴。）`
      : "";

    const image_layout = evidence.images.map((img, i) => ({
      pos: i === 0 ? "开头" : `段${i}`,
      image_id: img.id,
      caption: img.desc || img.caption || "",
      source: img.source,
      url: img.url || "",
    }));

    const body = sections.join("\n\n") + priceNote;

    return {
      title,
      lead,
      body,
      sections,
      cta,
      image_layout,
      platform,
      product_hint: product,
    };
  }

  function buildVerification(evidence, article) {
    const factIssues = [];
    const unconfirmed = [];
    evidence.facts.forEach((f) => {
      if (f.unconfirmed || !f.value || !f.source) {
        unconfirmed.push({
          field: f.key,
          reason: "知识库无依据，不得编造",
        });
        if (f.key === "价格") {
          factIssues.push({
            level: "warn",
            text: "价格无 ima 依据 → 一律「待确认」，正文已禁止写报价/补贴",
          });
        }
      } else {
        factIssues.push({
          level: "ok",
          text: `${f.key}：${f.value} · 已对 ${f.source.split("#")[0]}`,
        });
      }
    });

    const imageIssues = evidence.images.map((img) => ({
      level: "ok",
      text: `${img.id} 型号匹配 ${img.matched_model} · ${img.source}`,
    }));

    const complianceIssues = [
      { level: "ok", text: "未使用「最」「第一」「绝对」等绝对化用语" },
      { level: "ok", text: "未出现无依据竞品贬低或对比" },
      { level: "ok", text: "未承诺无法核验的补贴/赠品" },
      {
        level: unconfirmed.some((u) => u.field === "价格") ? "warn" : "ok",
        text: unconfirmed.some((u) => u.field === "价格")
          ? "价格相关表述已降级为待确认"
          : "价格表述有据",
      },
    ];

    const hasFail = [...factIssues, ...imageIssues, ...complianceIssues].some(
      (i) => i.level === "fail"
    );
    const hasWarn =
      !hasFail &&
      ([...factIssues, ...complianceIssues].some((i) => i.level === "warn") ||
        unconfirmed.length > 0);

    const overall = hasFail ? "FAIL" : hasWarn ? "WARN" : "PASS";

    return {
      overall,
      fact_check: {
        pass: !factIssues.some((i) => i.level === "fail"),
        issues: factIssues,
      },
      image_check: {
        pass: !imageIssues.some((i) => i.level === "fail"),
        issues: imageIssues,
      },
      compliance_check: {
        pass: !complianceIssues.some((i) => i.level === "fail"),
        issues: complianceIssues,
      },
      unconfirmed,
    };
  }

  function buildFourSegments(task, plan, evidence, article, report) {
    const scene = [
      `人群：${task.audience}`,
      `场景：${task.scenario}`,
      `平台：${task.platform}`,
      `内容目标：${task.content_goal}`,
      `购买阶段：${task.purchase_stage || "—"}`,
      `用户问题：${task.user_question || "—"}`,
      "",
      `策略切角：${plan.angle}`,
      `语气：${plan.tone}`,
      `结构：${plan.structure.join(" → ")}`,
    ].join("\n");

    const kb = evidence.facts
      .map((f) => {
        if (f.unconfirmed || !f.value) {
          return `· ${f.key}：待确认（无知识库依据）`;
        }
        return `· ${f.key}：${f.value}\n  来源：${f.source}\n  篇名：${f.title}`;
      })
      .concat(
        evidence.images.map(
          (img) =>
            `· 图片 ${img.id}：${img.desc} · 型号 ${img.matched_model}\n  来源：${img.source}`
        )
      )
      .join("\n\n");

    const soft = [
      `【标题】${article.title}`,
      `【导语】${article.lead}`,
      `【正文】\n${article.body}`,
      `【行动引导】${article.cta}`,
    ].join("\n\n");

    const verify = [
      `总览签章：${report.overall}`,
      "",
      "事实核验：",
      ...report.fact_check.issues.map((i) => `  [${i.level}] ${i.text}`),
      "",
      "图片核验：",
      ...report.image_check.issues.map((i) => `  [${i.level}] ${i.text}`),
      "",
      "合规检查：",
      ...report.compliance_check.issues.map((i) => `  [${i.level}] ${i.text}`),
      "",
      "待确认字段：",
      ...(report.unconfirmed.length
        ? report.unconfirmed.map((u) => `  · ${u.field}：${u.reason}`)
        : ["  （无）"]),
    ].join("\n");

    return {
      场景判断: scene,
      知识库依据: kb,
      图文软文: soft,
      核验结果: verify,
    };
  }

  function articleToMarkdown(article, report) {
    const imgs = (article.image_layout || [])
      .map(
        (il) =>
          `![${il.caption}](${il.source})\n*${il.caption} · \`${il.source}\`*`
      )
      .join("\n\n");
    return [
      `# ${article.title}`,
      "",
      `> ${article.lead}`,
      "",
      imgs,
      "",
      article.body,
      "",
      `**${article.cta}**`,
      "",
      "---",
      "",
      `核验摘要：${report.overall} · 价格等无依据字段已标待确认`,
    ].join("\n");
  }

  function articleToPlain(article, report) {
    return [
      article.title,
      "",
      article.lead,
      "",
      article.body,
      "",
      article.cta,
      "",
      `—— 核验：${report.overall}`,
    ].join("\n");
  }

  global.HWMock = {
    DEMO_ACCOUNT,
    DEMO_KB,
    PIPELINE_LAYERS,
    PLATFORM_PLANS,
    defaultTaskSpec,
    validateTask,
    buildContentPlan,
    buildEvidence,
    mergeRealImages,
    buildArticle,
    buildVerification,
    buildFourSegments,
    articleToMarkdown,
    articleToPlain,
  };
})(typeof window !== "undefined" ? window : globalThis);
