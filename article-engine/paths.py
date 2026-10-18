"""知识库与引擎路径解析。三盘分离：仅解析本项目内相对路径。"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

_ENGINE_ROOT = Path(__file__).resolve().parent
_PROJECT_ROOT = _ENGINE_ROOT.parent


def get_engine_root() -> Path:
    return _ENGINE_ROOT


def get_project_root() -> Path:
    return _PROJECT_ROOT


def _candidate_kb_dirs(project_root: Path):
    env = os.environ.get("HUAWEI_KB_ROOT") or os.environ.get("KB_ROOT")
    if env:
        yield Path(env)
    names = [
        "华为PC知识库/华为PC全板块深度知识库_v7",
        "华为PC知识库/华为PC全量经营知识库_v7",
        "华为PC知识库/华为PC全板块深度知识库",
        "华为PC知识库/华为PC全量经营知识库",
    ]
    for n in names:
        yield project_root / n
    kb = project_root / "华为PC知识库"
    if kb.is_dir():
        for child in sorted(kb.iterdir()):
            if child.is_dir() and (child / "P1-产品参数库").exists():
                yield child
            if child.is_dir():
                for sub in sorted(child.iterdir()):
                    if sub.is_dir() and (sub / "P1-产品参数库").exists():
                        yield sub


def resolve_kb_root(explicit: Optional[str] = None) -> Path:
    """解析本地知识库根目录；不复制知识库，只指向现有路径。"""
    if explicit:
        p = Path(explicit)
        if not p.exists():
            raise FileNotFoundError(f"KB_ROOT not found: {p}")
        return p.resolve()
    for c in _candidate_kb_dirs(_PROJECT_ROOT):
        if c.exists() and (c / "P1-产品参数库").exists():
            return c.resolve()
    raise FileNotFoundError(
        "未找到知识库（需含 P1-产品参数库）。请设置环境变量 HUAWEI_KB_ROOT "
        "或将知识库放在 华为赛题/华为PC知识库/…_v7/"
    )
