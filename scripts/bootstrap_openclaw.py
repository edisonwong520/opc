#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ROOT_ENV = ROOT / ".env"
BACKEND_ENV = ROOT / "backend" / ".env"
OPENCLAW_CONFIG = Path.home() / ".openclaw" / "openclaw.json"
OPENCLAW_WORKSPACE = Path.home() / ".openclaw" / "workspace"
OPENCLAW_PROVIDER_ID = "ceodesk"


def run(args: list[str], env: dict[str, str] | None = None, check: bool = True) -> subprocess.CompletedProcess:
    printable = " ".join(args)
    print(f"$ {printable}")
    return subprocess.run(args, cwd=ROOT, env=env, text=True, check=check)


def output(args: list[str], check: bool = False) -> str:
    completed = subprocess.run(args, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=check)
    return completed.stdout.strip()


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def write_env_file(path: Path, values: dict[str, str]) -> None:
    existing = parse_env_file(path)
    existing.update(values)
    path.write_text("".join(f"{key}={value}\n" for key, value in existing.items()))


def load_env() -> dict[str, str]:
    values = parse_env_file(ROOT_ENV)
    backend_values = parse_env_file(BACKEND_ENV)
    for key, value in backend_values.items():
        values.setdefault(key, value)
    for key, value in os.environ.items():
        values.setdefault(key, value)
    return values


def required(values: dict[str, str], key: str) -> str:
    value = values.get(key, "").strip()
    if not value or value.startswith("replace-with-") or value.startswith("sk-your-"):
        raise SystemExit(f"Missing required {key}. Add it to .env first.")
    return value


def openclaw_installed() -> bool:
    return shutil.which("openclaw") is not None


def openclaw_configured() -> bool:
    return OPENCLAW_CONFIG.exists()


def gateway_running() -> bool:
    status = output(["openclaw", "gateway", "status"])
    return "RPC probe: ok" in status and "Runtime: running" in status


def wait_for_gateway(timeout_seconds: int = 30) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if gateway_running():
            return True
        time.sleep(2)
    return False


def install_openclaw_if_missing() -> None:
    if openclaw_installed():
        print("OpenClaw CLI already installed; skipping npm install.")
        return
    run(["npm", "install", "-g", "openclaw@latest"])


def deploy_gateway_if_missing() -> None:
    if openclaw_configured():
        print(f"OpenClaw config exists at {OPENCLAW_CONFIG}; skipping deployment.")
        if not gateway_running():
            print("Gateway is configured but not running; starting existing service.")
            run(["openclaw", "gateway", "start"], check=False)
        return

    token = output(["openssl", "rand", "-hex", "24"], check=True)
    run(
        [
            "openclaw",
            "onboard",
            "--non-interactive",
            "--accept-risk",
            "--mode",
            "local",
            "--auth-choice",
            "skip",
            "--gateway-bind",
            "loopback",
            "--gateway-port",
            "7788",
            "--gateway-auth",
            "token",
            "--gateway-token",
            token,
            "--install-daemon",
            "--skip-channels",
            "--skip-ui",
            "--skip-search",
            "--skip-skills",
            "--json",
        ]
    )


def read_gateway_config() -> dict[str, str]:
    config = json.loads(OPENCLAW_CONFIG.read_text())
    gateway = config.get("gateway") or {}
    auth = gateway.get("auth") or {}
    port = gateway.get("port", 7788)
    return {
        "OPENCLAW_GATEWAY_URL": f"ws://127.0.0.1:{port}",
        "OPENCLAW_GATEWAY_AUTH_MODE": auth.get("mode", "token"),
        "OPENCLAW_GATEWAY_TOKEN": auth.get("token", ""),
        "OPENCLAW_GATEWAY_PASSWORD": auth.get("password", ""),
    }


def sync_gateway_env() -> None:
    values = read_gateway_config()
    write_env_file(ROOT_ENV, values)
    write_env_file(BACKEND_ENV, values)
    print("Synced OpenClaw Gateway auth into .env and backend/.env.")


def configure_model(values: dict[str, str]) -> None:
    base_url = required(values, "AI_BASE_URL")
    api_key = required(values, "AI_API_KEY")
    model = required(values, "AI_MODEL")

    batch = [
        {"path": "models.mode", "value": "merge"},
        {
            "path": f"models.providers.{OPENCLAW_PROVIDER_ID}",
            "value": {
                "baseUrl": base_url,
                "apiKey": api_key,
                "auth": "api-key",
                "api": "openai-completions",
                "models": [
                    {
                        "id": model,
                        "name": model,
                        "input": ["text", "image"],
                        "reasoning": True,
                    }
                ],
            },
        },
    ]

    batch_path = ROOT / ".openclaw-config.batch.json"
    batch_path.write_text(json.dumps(batch, ensure_ascii=False, indent=2))
    try:
        run(["openclaw", "config", "set", "--batch-file", str(batch_path)])
    finally:
        batch_path.unlink(missing_ok=True)

    run(["openclaw", "models", "set", f"{OPENCLAW_PROVIDER_ID}/{model}"])


def maybe_copy_wanny_env() -> None:
    source = Path("/Users/edison/code/python/wanny/backend/.env")
    if not source.exists():
        return
    source_values = parse_env_file(source)
    current_values = parse_env_file(ROOT_ENV)
    copied = {
        key: source_values[key]
        for key in ["AI_BASE_URL", "AI_API_KEY", "AI_MODEL", "GEMINI_API_KEY", "GEMINI_MODEL"]
        if source_values.get(key) and not current_values.get(key)
    }
    if copied:
        write_env_file(ROOT_ENV, copied)
        print("Filled missing model settings in .env from wanny backend settings.")


def main() -> None:
    maybe_copy_wanny_env()
    values = load_env()
    install_openclaw_if_missing()
    deploy_gateway_if_missing()
    sync_gateway_env()
    values = load_env()
    configure_model(values)
    run(["openclaw", "gateway", "restart"], check=False)
    wait_for_gateway()
    run(["openclaw", "gateway", "status"], check=False)
    run(["openclaw", "models", "status", "--json"], check=False)
    print("OpenClaw is ready for CEO Desk.")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        sys.exit(exc.returncode)
