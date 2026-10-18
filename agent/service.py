"""HTTP-facing orchestration for the existing seven domain layers.

ARTICLE_ENGINE_HOOK_V1: layers may prefer article-engine with fallback.
"""
from __future__ import annotations

import copy
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import os
import re
from threading import RLock
from typing import Any
from uuid import uuid4

from .env_config import load_env
from .layers.kb_connection import check_knowledge_base, DEFAULT_KB_NAME
from .layers.task_understanding import TaskSpec
from .layers.scenario_strategy import build_content_plan
from .layers.ima_retrieval import EvidenceMap, retrieve_evidence, P1_ROOT
from .layers.article_generation import DraftArticle, generate_draft
from .layers.verification import verify

PLATFORMS = {"小红书": "xhs", "公众号": "wechat_mp", "朋友圈": "moments", "海报": "poster"}
SCENARIOS = {"开学季": "school_season", "商务办公": "business_office", "内容创作": "content_creation", "家庭换新": "family_refresh", "企业采购": "enterprise_procurement", "到店体验": "store_visit", "新品上市": "new_launch", "节日营销": "holiday", "门店引流": "store_visit", "节日送礼": "holiday"}
TAIL = "不同销售版本配置可能不同，请以官方规格页及实际销售 SKU 为准。"


class ServiceError(Exception):
    """A safe error suitable for returning to the browser."""

    def __init__(self, message: str, code: str = "INVALID_INPUT", status: int = 422) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


def normalize(value: str) -> str:
    """Normalize formatting without guessing a different model."""
    return re.sub(r"[\s\-_（）()·]", "", value).lower()


class IntegrationService:
    """Keep versioned local sessions and serialize domain-layer outputs."""

    def __init__(self) -> None:
        load_env()
        self._lock = RLock()
        self._plans: dict[str, dict[str, Any]] = {}
        self._results: dict[str, dict[str, Any]] = {}
        self._latest: dict[str, str] = {}
        self._assets: dict[str, Path] = {}
        self._status: dict[str, Any] | None = None
        self._kb = None

    def options(self) -> dict[str, Any]:
        """Return the actual indexed products and supported UI choices."""
        products = sorted({p.parent.name for p in Path(P1_ROOT).rglob("产品事实.md")})
        return {"products": products, "platforms": [{"id": v, "label": k} for k, v in PLATFORMS.items()], "scenarios": [{"id": v, "label": k} for k, v in list(SCENARIOS.items())[:8]]}

    def status(self, probe: bool = False) -> dict[str, Any]:
        """Probe the actual KB connection; configuration is not LLM reachability."""
        with self._lock:
            if self._status is not None and not probe:
                return copy.deepcopy(self._status)
        kb = check_knowledge_base(os.getenv("IMA_KB_NAME", DEFAULT_KB_NAME))
        strict = os.getenv("IMA_MODE", "local_demo") == "strict"
        connection = "failed" if strict and kb.connection != "connected" else kb.connection
        data = {
            "account": {"display_name": "本机运行环境", "client_id_masked": kb.account_id_masked, "configured": bool(os.getenv("IMA_OPENAPI_CLIENTID") and os.getenv("IMA_OPENAPI_APIKEY"))},
            "kb": {"name": kb.kb_name, "id": kb.kb_id, "connection": connection},
            "kb_name": kb.kb_name,
            "kb_id": kb.kb_id,
            "connection": connection,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "llm": {"configured": bool(os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")), "probe_status": "skipped", "model": os.getenv("LLM_MODEL", ""), "generation_mode": "template"},
            "allowed_mode": "strict" if strict else "local_demo",
            "fallback_reason": "" if connection == "connected" else "ima 未连通；使用本地镜像演示" if connection == "local_index" else "知识库不可用，请检查服务端配置",
            "probes": [
                {"name": "search_knowledge_base", "status": "ok" if kb.connection == "connected" else "failed", "detail": "共享库定位成功" if kb.connection == "connected" else "线上库未连通"},
                {"name": "local_index", "status": "ok" if kb.connection == "local_index" else "skipped", "detail": "本地镜像演示" if kb.connection == "local_index" else "未使用本地索引"},
                {"name": "LLM", "status": "skipped", "detail": "未执行模型探测；生成采用受控模板"},
            ],
        }
        with self._lock:
            self._kb = kb
            self._status = data
        return copy.deepcopy(data)

    def _task(self, raw: dict[str, Any]) -> TaskSpec:
        if not isinstance(raw, dict):
            raise ServiceError("task 必须是对象")
        values: dict[str, str] = {}
        for key in ("product_hint", "audience", "scenario", "platform", "purchase_stage", "user_question", "content_goal"):
            value = raw.get(key, raw.get("product" if key == "product_hint" else "query" if key == "user_question" else key, ""))
            if not isinstance(value, str) or len(value) > 4000:
                raise ServiceError(f"{key} 应为不超过 4000 字的文本")
            values[key] = value.strip()
        missing = [key for key in ("product_hint", "audience", "scenario", "platform", "content_goal") if not values[key]]
        if missing:
            raise ServiceError("请补全：" + "、".join(missing), "MISSING_FIELDS")
        values["platform"] = PLATFORMS.get(values["platform"], values["platform"])
        values["scenario"] = SCENARIOS.get(values["scenario"], values["scenario"])
        if values["platform"] not in PLATFORMS.values() or values["scenario"] not in SCENARIOS.values():
            raise ServiceError("请选择支持的场景和渠道", "UNKNOWN_ENUM")
        products = self.options()["products"]
        matches = [p for p in products if normalize(p) == normalize(values["product_hint"])]
        if not matches:
            raise ServiceError("未找到准确型号，请从产品候选中选择：" + "、".join(products[:12]), "UNKNOWN_PRODUCT")
        values["product_hint"] = matches[0]
        return TaskSpec(**values)

    def plan(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Validate the full form without overriding explicit audience or goals."""
        task = self._task(payload.get("task", payload))
        plan = build_content_plan(task)
        plan_data = asdict(plan)
        plan_data.update({"audience": task.audience, "content_goal": task.content_goal, "product_hint": task.product_hint, "platform_label": next((label for label, pid in PLATFORMS.items() if pid == task.platform), task.platform), "scenario_label": next((label for label, sid in SCENARIOS.items() if sid == task.scenario), task.scenario), "why": f"根据{task.scenario}与{task.platform}策略生成，卖点与篇幅来自服务端配置。"})
        result = {"task_id": uuid4().hex, "version": 1, "task": asdict(task), "plan": plan_data}
        with self._lock:
            self._plans[result["task_id"]] = copy.deepcopy(result)
        return result

    def _get_plan(self, payload: dict[str, Any]) -> dict[str, Any]:
        plan_id = payload.get("task_id") or payload.get("plan_id")
        if not plan_id:
            return self.plan(payload)
        with self._lock:
            result = copy.deepcopy(self._plans.get(str(plan_id)))
        if result is None:
            raise ServiceError("任务已失效，请重新生成策略", "NOT_FOUND", 404)
        if payload.get("version", result["version"]) != result["version"]:
            raise ServiceError("策略版本已过期", "STALE_VERSION", 409)
        return result

    def generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Run retrieval, generation and verification, never frontend mock data."""
        snapshot = self._get_plan(payload)
        status = self.status()
        if status["kb"]["connection"] == "failed":
            raise ServiceError("知识库不可用，请重新探测或检查服务端配置", "KB_UNAVAILABLE", 503)
        task = TaskSpec(**snapshot["task"])
        plan = build_content_plan(task)
        evidence = retrieve_evidence(os.getenv("IMA_KB_NAME", DEFAULT_KB_NAME), task.product_hint, task.scenario)
        if evidence.retrieval_mode == "mock":
            raise ServiceError("没有取得可核对的知识库证据", "EVIDENCE_UNAVAILABLE", 503)
        if os.getenv("IMA_MODE", "local_demo") == "strict" and evidence.retrieval_mode != "ima_api":
            raise ServiceError("严格模式不允许镜像回退", "STRICT_MODE", 503)
        draft = generate_draft(task, plan, evidence)
        return self._bundle(snapshot["task_id"], task, plan, evidence, draft)

    def _bundle(self, task_id: str, task: TaskSpec, plan: Any, evidence: EvidenceMap, draft: DraftArticle, previous: dict[str, Any] | None = None, changed: list[str] | None = None) -> dict[str, Any]:
        report_raw = verify(draft, evidence, plan, product_hint=task.product_hint)  # ARTICLE_ENGINE_HOOK_V1
        report = asdict(report_raw)
        # Every issue is converted to the frontend's explicit severity contract.
        for name in ("fact_check", "image_check", "compliance_check"):
            check = report[name]
            check["executed"] = True
            check["issues"] = [{"level": "fail", "text": str(item)} for item in check.get("issues", [])]
            if not check["issues"]:
                check["issues"] = [{"level": "ok", "text": "检查已执行，通过"}]
        if not evidence.facts:
            report["fact_check"]["pass"] = False
            report["fact_check"]["issues"].append({"level": "fail", "text": "没有产品事实依据"})
        # Supplement older domain versions which did not inspect CTA.
        if re.search(r"保证|最低价|\d+\s*元|国补|绝对兼容|全网最低", draft.cta):
            report["compliance_check"]["pass"] = False
            report["compliance_check"]["issues"].append({"level": "fail", "text": "CTA 含无依据的价格、政策或保证承诺"})
        unconfirmed = [{"field": "待确认", "reason": str(item)} for item in report.get("unconfirmed", [])]
        if len(draft.image_layout) < plan.image_min:
            report["image_check"]["pass"] = False
            report["image_check"]["issues"].append({"level": "fail", "text": f"实际配图 {len(draft.image_layout)}，少于策略下限 {plan.image_min}"})
        if evidence.retrieval_mode != "ima_api":
            unconfirmed.append({"field": "来源模式", "reason": "本地镜像演示，未完成 ima 在线原文与媒体取证"})
        report["unconfirmed"] = unconfirmed
        report["overall"] = "FAIL" if not all(report[name]["pass"] for name in ("fact_check", "image_check", "compliance_check")) else "WARN" if unconfirmed else "PASS"
        report["overall_pass"] = report["overall"] != "FAIL"
        ev = asdict(evidence)
        for image in ev["images"]:
            local_path = image.pop("path", "")
            image["preview_url"] = image.get("preview_url", "")
            if local_path:
                image_path = Path(local_path).resolve()
                if image_path.is_file() and Path(P1_ROOT).resolve() in image_path.parents:
                    asset_id = uuid4().hex
                    with self._lock:
                        self._assets[asset_id] = image_path
                    image["preview_url"] = "/api/assets/" + asset_id
        article = asdict(draft)
        article.update({"platform": task.platform, "product_hint": task.product_hint})
        article["sections"] = [{"id": f"section-{i}", "text": text} for i, text in enumerate(draft.body.split("\n\n")) if text and TAIL not in text]
        article["disclaimer"] = TAIL
        result_id = uuid4().hex
        result = {
            "result_id": result_id, "task_id": task_id, "version": previous["version"] + 1 if previous else 1,
            "previous_result_id": previous["result_id"] if previous else None,
            "task": asdict(task), "plan": {**asdict(plan), "audience": task.audience, "content_goal": task.content_goal, "product_hint": task.product_hint, "platform_label": next((label for label, pid in PLATFORMS.items() if pid == task.platform), task.platform), "scenario_label": next((label for label, sid in SCENARIOS.items() if sid == task.scenario), task.scenario), "why": f"根据{task.scenario}与{task.platform}策略生成，卖点与篇幅来自服务端配置。"}, "evidence": ev, "article": article, "report": report,
            "retrieval_mode": evidence.retrieval_mode, "generation_mode": "template", "changed": changed or [],
            "warnings": [item["reason"] for item in unconfirmed],
        }
        result["segments"] = {
            "场景判断": f"产品：{task.product_hint}\n人群：{task.audience}\n场景：{task.scenario}\n渠道：{task.platform}\n目标：{task.content_goal}\n切角：{plan.angle}",
            "知识库依据": "来源模式：" + evidence.retrieval_mode + "\n" + "\n".join(f"{f['key']}：{f['value']}（{f['source']}）" for f in ev["facts"]),
            "图文软文": "\n\n".join([draft.title, draft.lead, draft.body, draft.cta]),
            "核验结果": report["overall"] + "\n" + "\n".join(item["text"] for name in ("fact_check", "image_check", "compliance_check") for item in report[name]["issues"]) + "\n" + "\n".join(result["warnings"]),
        }
        with self._lock:
            if previous and self._latest.get(task_id) != previous["result_id"]:
                raise ServiceError("当前稿件已更新，请重新载入", "STALE_VERSION", 409)
            self._results[result_id] = copy.deepcopy(result)
            self._latest[task_id] = result_id
        return result

    def _result(self, payload: dict[str, Any]) -> dict[str, Any]:
        result_id = payload.get("result_id") or payload.get("bundle", {}).get("result_id")
        with self._lock:
            result = copy.deepcopy(self._results.get(str(result_id)))
            if result is None:
                raise ServiceError("稿件已失效，请重新生成", "NOT_FOUND", 404)
            if self._latest.get(result["task_id"]) != result_id or payload.get("version", result["version"]) != result["version"]:
                raise ServiceError("稿件版本已过期，请使用当前稿", "STALE_VERSION", 409)
        return result

    def revise(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Clone the current snapshot, apply structured edits and reverify."""
        old = self._result(payload)
        changes = payload.get("changes", {})
        if not isinstance(changes, dict):
            raise ServiceError("changes 必须是对象")
        task = TaskSpec(**old["task"])
        changed: list[str] = []
        platform = changes.get("platform") or changes.get("newPlatform")
        if platform:
            task.platform = PLATFORMS.get(platform, platform)
            if task.platform not in PLATFORMS.values():
                raise ServiceError("不支持该渠道")
            changed.append("渠道：" + task.platform)
        plan = build_content_plan(task)
        evidence = EvidenceMap(facts=copy.deepcopy(old["evidence"]["facts"]), images=copy.deepcopy(old["evidence"]["images"]), retrieval_mode=old["retrieval_mode"])
        highlight = changes.get("highlight") or changes.get("changeHighlight")
        label = {"battery": "续航", "screen": "屏幕", "续航优先": "续航", "屏幕优先": "屏幕"}.get(highlight, "")
        if highlight and not label:
            raise ServiceError("不支持该卖点侧重")
        if label:
            plan.highlight_order = [label] + [x for x in plan.highlight_order if label not in x]
            plan.angle = f"先核对{label}相关依据；" + plan.angle
            changed.append(label + "优先")
        regenerate = bool(platform or label)
        draft = generate_draft(task, plan, evidence) if regenerate else DraftArticle(**{k: copy.deepcopy(old["article"][k]) for k in ("title", "lead", "body", "cta", "image_layout")})
        if label:
            parts = draft.body.replace(TAIL, "").strip().split("\n\n")
            parts.sort(key=lambda part: 0 if label in part else 1)
            draft.body = "\n\n".join(parts) + "\n\n" + TAIL
        if changes.get("delete_last_section") or changes.get("deleteSection"):
            parts = [p for p in draft.body.replace(TAIL, "").split("\n\n") if p.strip()]
            if not parts:
                raise ServiceError("当前没有可删除的正文段", "NO_EDITABLE_SECTION")
            parts.pop()
            draft.body = "\n\n".join(parts) + "\n\n" + TAIL
            changed.append("删除最后一段正文，保留免责句")
        if "cta" in changes or "newCta" in changes:
            cta = changes.get("cta", changes.get("newCta"))
            if not isinstance(cta, str) or len(cta) > 4000:
                raise ServiceError("CTA 必须是不超过 4000 字的文本")
            draft.cta = cta
            changed.append("更新 CTA")
        return self._bundle(old["task_id"], task, plan, evidence, draft, old, changed)

    def export(self, payload: dict[str, Any]) -> dict[str, str]:
        """Export the current verified snapshot with source and report summary."""
        result = self._result(payload)
        if result["report"]["overall"] == "FAIL":
            raise ServiceError("核验未通过，禁止导出终稿；请先修订", "EXPORT_BLOCKED", 409)
        fmt = payload.get("format", "txt")
        if fmt not in ("md", "txt"):
            raise ServiceError("导出格式只能为 md 或 txt")
        article = result["article"]
        title = ("# " if fmt == "md" else "") + article["title"]
        content = "\n\n".join([title, article["lead"], article["body"], article["cta"], "配图与来源：", *[f"{i['image_id']}：{i['caption']}（{i['source']}）" for i in article["image_layout"]], "知识库依据：", result["segments"]["知识库依据"], "核验摘要：", result["segments"]["核验结果"], f"版本：{result['version']}；生成模式：template"])
        return {"filename": "华为PC软文." + fmt, "mime": "text/markdown;charset=utf-8" if fmt == "md" else "text/plain;charset=utf-8", "content": content}

    def asset(self, asset_id: str) -> Path:
        """Resolve only server-registered assets; no filesystem path input."""
        with self._lock:
            path = self._assets.get(asset_id)
        if path is None or not path.is_file():
            raise ServiceError("图片不存在", "NOT_FOUND", 404)
        return path
