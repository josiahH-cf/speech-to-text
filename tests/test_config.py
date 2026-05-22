from local_dictation.config import DEFAULT_SETTINGS, cleanup_paths, deep_merge, load_settings, migrate_settings, stt_model_cache_paths


def test_default_settings_are_created(tmp_path):
    path = tmp_path / "settings.json"
    settings = load_settings(path, create=True)

    assert path.exists()
    assert settings["hotkey"] == "ctrl+alt+space"
    assert settings["stt"]["engine"] == "faster-whisper"
    assert settings["insertion"]["mode"] == "auto"
    assert settings["recording"]["input_device_id"] is None
    assert settings["recording"]["cue_tone"] == "off"
    assert settings["recording"]["gain_db"] == 0.0
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
    assert merged["recording"]["cue_tone"] == "off"
    assert merged["recording"]["silence_stop"]["silence_seconds"] == 1.4
    assert merged["custom"]["keep"] is True


def test_migrate_v1_clipboard_default_to_auto():
    migrated = migrate_settings({"insertion": {"mode": "clipboard"}})

    assert migrated["config_version"] == 3
    assert migrated["insertion"]["mode"] == "auto"


def test_stt_model_cache_paths_use_huggingface_home(monkeypatch, tmp_path):
    monkeypatch.setenv("HF_HOME", str(tmp_path / "hf"))

    paths = stt_model_cache_paths(("base.en",))

    assert paths == (
        tmp_path / "hf" / "hub" / "models--Systran--faster-whisper-base.en",
        tmp_path / "hf" / "hub" / ".locks" / "models--Systran--faster-whisper-base.en",
    )


def test_cleanup_paths_removes_existing_files_and_directories(tmp_path):
    directory = tmp_path / "appdata"
    file_path = tmp_path / "cache.lock"
    directory.mkdir()
    (directory / "settings.json").write_text("{}", encoding="utf-8")
    file_path.write_text("locked", encoding="utf-8")

    results = cleanup_paths((directory, file_path, tmp_path / "missing"))

    assert [result.removed for result in results] == [True, True, False]
    assert not directory.exists()
    assert not file_path.exists()
