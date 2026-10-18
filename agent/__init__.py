"""
agent 包初始化
==============
唯一职责：导入本包下的任意模块时，自动把项目根目录的 .env 载入 os.environ。

背景（重要）：
    .env 里配了 IMA_OPENAPI_* 和 LLM_*，但 main.py / ui/gradio_app.py / demo.py
    都不会主动 import agent.env_config，导致凭证从未进入环境变量，
    kb_connection / ima_retrieval / llm_client 全部静默回退（本地索引 + mock），
    表现为"明明配了密钥却连不上"。此处统一兜底修复。

约定：不覆盖已有的系统环境变量（env_config.load_env 内部已保证）。
"""
from .env_config import load_env

load_env()

__all__ = ["load_env"]
