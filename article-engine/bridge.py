"""
桥接层：供 agent/layers 以稳定 dict 接口调用本引擎。
失败时抛异常，由调用方回退原逻辑。
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from paths import resolve_kb_root  # noqa: E402


def _ensure_imports():
    from article_generator import ArticleGenerator  # noqa: F401
    from fact_verification import FactVerifier  # noqa: F401
    from compliance_checker import ComplianceChecker  # noqa: F401
    from content_validator import ContentValidator  # noqa: F401
    from article_system import ArticleSystem  # noqa: F401


def generate_article(
    product_name: str,
    scenario: str = "移动办公",
    platform: str = "公众号",
    target_audience: str = "职场人",
    kb_root: Optional[str] = None,
    auto_fix: bool = True,
) -> Dict[str, Any]:
    """生成+可选校验，返回前端/layers 友好的 dict。"""
    _ensure_imports()
    from article_system import ArticleSystem

    kb = str(resolve_kb_root(kb_root))
    system = ArticleSystem(kb)
    raw = system.generate_with_validation(
        product_name=product_name,
        scenario=scenario,
        platform=platform,
        target_audience=target_audience,
        auto_fix=auto_fix,
    )
    article = raw.get("article")
    report = raw.get("validation_report")
    out: Dict[str, Any] = {
        "engine": "article-engine",
        "status": raw.get("status"),
        "kb_root": kb,
        "iterations": raw.get("iterations", []),
    }
    if article is not None:
        out["article"] = article.to_dict() if hasattr(article, "to_dict") else article
        out["markdown"] = article.to_markdown() if hasattr(article, "to_markdown") else ""
        out["title"] = getattr(article, "selected_title", "") or ""
        opening = getattr(article, "opening", "") or ""
        body = getattr(article, "body", "") or ""
        cta = getattr(article, "cta", "") or ""
        out["content"] = f"{opening}\n\n{body}\n\n{cta}".strip()
        out["knowledge_sources"] = getattr(article, "knowledge_sources", []) or []
        out["facts_used"] = getattr(article, "facts_used", []) or []
        out["images"] = [
            {
                "filename": getattr(img, "filename", ""),
                "source": getattr(img, "source", ""),
                "position": getattr(img, "position", ""),
                "purpose": getattr(img, "purpose", ""),
                "caption": getattr(img, "caption", ""),
            }
            for img in (getattr(article, "images", None) or [])
        ]
    if report is not None:
        out["validation"] = report.to_dict() if hasattr(report, "to_dict") else report
        out["can_publish"] = getattr(report, "can_publish", False)
        out["score"] = getattr(report, "final_score", None)
    return out


def verify_content(
    product_name: str,
    content: str,
    images: Optional[List[Dict[str, Any]]] = None,
    platform: str = "公众号",
    knowledge_sources: Optional[List[str]] = None,
    kb_root: Optional[str] = None,
) -> Dict[str, Any]:
    """事实核验 + 合规检查。"""
    _ensure_imports()
    from content_validator import ContentValidator

    kb = str(resolve_kb_root(kb_root))
    validator = ContentValidator(kb)
    report = validator.validate(
        product_name=product_name,
        content=content,
        images=images or [],
        platform=platform,
        knowledge_sources=knowledge_sources or [],
    )
    return {
        "engine": "article-engine",
        "kb_root": kb,
        "report": report.to_dict(),
        "can_publish": report.can_publish,
        "score": report.final_score,
        "overall_status": report.overall_status,
    }


def fact_verify_only(
    product_name: str,
    content: str,
    images: Optional[List[Dict[str, Any]]] = None,
    kb_root: Optional[str] = None,
) -> Dict[str, Any]:
    _ensure_imports()
    from fact_verification import FactVerifier

    kb = str(resolve_kb_root(kb_root))
    verifier = FactVerifier(kb)
    result = verifier.verify_content(product_name, content, images or [])
    return {
        "engine": "article-engine",
        "kb_root": kb,
        "result": result.to_dict() if hasattr(result, "to_dict") else result,
    }


def compliance_check_only(content: str, platform: str = "公众号") -> Dict[str, Any]:
    _ensure_imports()
    from compliance_checker import ComplianceChecker

    checker = ComplianceChecker()
    result = None
    for meth in ("check", "check_content", "verify"):
        fn = getattr(checker, meth, None)
        if callable(fn):
            try:
                result = fn(content, platform)
                break
            except TypeError:
                try:
                    result = fn(content=content, platform=platform)
                    break
                except TypeError:
                    try:
                        result = fn(content)
                        break
                    except TypeError:
                        continue
    if result is None:
        raise RuntimeError("ComplianceChecker has no compatible check method")
    return {
        "engine": "article-engine",
        "result": result.to_dict() if hasattr(result, "to_dict") else result,
    }
