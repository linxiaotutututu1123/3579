from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from src.config import AppSettings, load_settings


def main() -> None:
    env_path: Path = Path(".env")
    if env_path.exists():
        _ = load_dotenv(dotenv_path=env_path)

    settings: AppSettings = load_settings()
    print("cn-futures-auto-trader: boot OK (skeleton)")
    print(f"baseline_time={settings.baseline_time}")
    print(f"dingtalk_enabled={settings.dingtalk is not None}")


if __name__ == "__main__":
    main()
