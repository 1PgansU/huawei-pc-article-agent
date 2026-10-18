"use strict";
(function (global) {
  async function request(path, payload, timeoutMs) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs || 120000);
    try {
      const response = await fetch(path, {
        method: payload ? "POST" : "GET",
        headers: payload ? { "Content-Type": "application/json" } : {},
        body: payload ? JSON.stringify(payload) : undefined,
        signal: controller.signal,
      });
      const data = await response.json();
      if (!response.ok) {
        const error = data.error || {};
        throw new Error(error.message || `请求失败（HTTP ${response.status}），请重试。`);
      }
      return data;
    } catch (error) {
      if (error.name === "AbortError") throw new Error("请求超时，未取得结果；请检查服务状态后重试。");
      if (error instanceof TypeError) throw new Error("无法连接本地服务。请在项目目录运行：python api_server.py");
      throw error;
    } finally {
      clearTimeout(timer);
    }
  }

  global.AgentApi = {
    status: () => request("/api/status", null, 35000).then((response) => response.data || response),
    options: () => request("/api/options", null, 35000).then((response) => response.data || response),
    validate: (task) => request("/api/task/validate", { task }, 35000).then((response) => response.data || response),
    plan: (task) => request("/api/plan", { task }, 35000).then((response) => response.data || response),
    generate: (payload) => request("/api/generate", payload).then((response) => response.data || response),
    revise: (resultId, task, changes) => request("/api/revise", { result_id: resultId, version: task && task.version, changes }).then((response) => response.data || response),
    export: (resultId, format) => request("/api/export", { result_id: resultId, format }).then((response) => response.data || response),
  };
})(window);
