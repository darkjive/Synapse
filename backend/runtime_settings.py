import json

from backend.config import Config


def _settings_file(config: Config):
    return config.data_dir / "settings.json"


def is_read_only(config: Config) -> bool:
    try:
        data = json.loads(_settings_file(config).read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return config.read_only
    value = data.get("read_only")
    return value if isinstance(value, bool) else config.read_only


def set_read_only(config: Config, value: bool) -> None:
    path = _settings_file(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"read_only": value}), encoding="utf-8")
