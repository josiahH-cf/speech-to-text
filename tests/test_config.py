from local_dictation.config import DEFAULT_SETTINGS, deep_merge, load_settings, migrate_settings


def test_default_settings_are_created(tmp_path):
    path = tmp_path / "settings.json"
    settings = load_settings(path, create=True)

    assert path.exists()
    assert settings["hotkey"] == "ctrl+alt+space"
    assert settings["stt"]["engine"] == "faster-whisper"
    assert settings["insertion"]["mode"] == "auto"
    assert settings["recording"]["silence_stop"]["enabled"] is True
    assert settings["setup"]["ollama_install"] == "auto"


def test_deep_merge_fills_missing_values_and_preserves_unknowns():
    loaded = {
        "hotkey": "ctrl+shift+d",
        "stt": {"model": "tiny.en"},
        "custom": {"keep": True},
    }

    merged = deep_merge(DEFAULT_SETTINGS, loaded)

    assert merged["hotkey"] == "ctrl+shift+d"
    assert merged["stt"]["model"] == "tiny.en"
    assert merged["stt"]["device"] == "cpu"
    assert merged["recording"]["silence_stop"]["silence_seconds"] == 1.4
    assert merged["custom"]["keep"] is True


def test_migrate_v1_clipboard_default_to_auto():
    migrated = migrate_settings({"insertion": {"mode": "clipboard"}})

    assert migrated["config_version"] == 2
    assert migrated["insertion"]["mode"] == "auto"
