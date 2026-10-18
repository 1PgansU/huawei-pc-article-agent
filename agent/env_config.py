"""
环境变量加载工具
- 优先从 .env 读取
- 不进源码（已 .gitignore）
- 缺失时给出明确提示
"""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


def load_env(env_file: Path = None, force: bool = False) -> dict:
    """读取 .env 到 os.environ（默认不覆盖已存在的系统变量；force=True 时强制覆盖）"""
    env_file = env_file or ENV_FILE
    loaded = {}
    if not env_file.exists():
        return loaded
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if key and (force or key not in os.environ):  # force 时覆盖
            os.environ[key] = val
            loaded[key] = val
    return loaded


def mask_secret(s: str, head: int = 4, tail: int = 4) -> str:
    """脱敏显示，例：abcd****wxyz"""
    if not s or len(s) <= head + tail:
        return "****" if s else "(empty)"
    return f"{s[:head]}****{s[-tail:]}"


def check_ima_creds() -> dict:
    """返回 ima 凭证状态（不打印明文）"""
    cid = os.getenv("IMA_OPENAPI_CLIENTID", "")
    key = os.getenv("IMA_OPENAPI_APIKEY", "")
    return {
        "client_id_configured": bool(cid) and cid != "your_client_id_here",
        "api_key_configured": bool(key) and key != "your_api_key_here",
        "client_id_masked": mask_secret(cid) if cid else "(empty)",
        "api_key_masked": mask_secret(key) if key else "(empty)",
    }


# 启动时自动加载一次
load_env()


if __name__ == "__main__":
    load_env()
    status = check_ima_creds()
    print("=== IMA 凭证状态 ===")
    for k, v in status.items():
        print(f"  {k}: {v}")
    print(f"\n.env 路径: {ENV_FILE}")
    print(f"存在: {ENV_FILE.exists()}")
