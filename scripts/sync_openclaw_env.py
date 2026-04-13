#!/usr/bin/env python3
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = Path.home() / ".openclaw" / "openclaw.json"
ROOT_ENV = ROOT / ".env"
BACKEND_ENV = ROOT / "backend" / ".env"


def load_gateway() -> dict:
    config = json.loads(CONFIG_PATH.read_text())
    gateway = config.get("gateway") or {}
    auth = gateway.get("auth") or {}
    return {
        "url": f"ws://127.0.0.1:{gateway.get('port', 7788)}",
        "auth_mode": auth.get("mode", "token"),
        "token": auth.get("token", ""),
        "password": auth.get("password", ""),
    }


def upsert_env(path: Path, values: dict[str, str]) -> None:
    existing: dict[str, str] = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            existing[key] = value

    existing.update(values)
    path.write_text("".join(f"{key}={value}\n" for key, value in existing.items()))


def main() -> None:
    gateway = load_gateway()
    values = {
        "OPENCLAW_GATEWAY_URL": gateway["url"],
        "OPENCLAW_GATEWAY_AUTH_MODE": gateway["auth_mode"],
        "OPENCLAW_GATEWAY_TOKEN": gateway["token"],
        "OPENCLAW_GATEWAY_PASSWORD": gateway["password"],
    }
    upsert_env(ROOT_ENV, values)
    upsert_env(BACKEND_ENV, values)
    print(f"Synced OpenClaw Gateway auth into {ROOT_ENV} and {BACKEND_ENV}.")


if __name__ == "__main__":
    main()
