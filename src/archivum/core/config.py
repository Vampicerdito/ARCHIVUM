from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from platformdirs import user_config_dir, user_data_dir


APP_NAME = "ARCHIVUM"


@dataclass
class AppConfig:
    data_dir: Path
    config_file: Path

    @classmethod
    def load(cls) -> "AppConfig":
        config_dir = Path(user_config_dir(APP_NAME, APP_NAME))
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "settings.json"

        if config_file.exists():
            try:
                payload = json.loads(config_file.read_text(encoding="utf-8"))
                configured = payload.get("data_dir")
                if configured:
                    data_dir = Path(configured).expanduser()
                else:
                    data_dir = Path(user_data_dir(APP_NAME, APP_NAME))
            except (OSError, json.JSONDecodeError, TypeError):
                data_dir = Path(user_data_dir(APP_NAME, APP_NAME))
        else:
            data_dir = Path(user_data_dir(APP_NAME, APP_NAME))

        return cls(data_dir=data_dir, config_file=config_file)

    def save(self) -> None:
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {"data_dir": str(self.data_dir.resolve())}
        temporary = self.config_file.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        temporary.replace(self.config_file)
