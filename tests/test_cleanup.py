from local_dictation.cleanup import build_cleanup_prompt, cleanup_text


def test_disabled_cleanup_returns_raw_text():
    assert cleanup_text("hello world", {"enabled": False}) == "hello world"


def test_cleanup_prompt_is_deterministic():
    prompt = build_cleanup_prompt("hello world", "punctuate")

    assert "Return only the final text" in prompt
    assert "hello world" in prompt


def test_cleanup_uses_ollama_response_when_enabled():
    def fake_post(endpoint, payload, timeout):
        assert endpoint == "http://localhost:11434/api/generate"
        assert payload["stream"] is False
        assert timeout == 20
        return {"response": "Hello world."}

    result = cleanup_text(
        "hello world",
        {
            "enabled": True,
            "provider": "ollama",
            "endpoint": "http://localhost:11434/api/generate",
            "model": "gemma3:1b",
            "mode": "punctuate",
            "timeout_seconds": 20,
        },
        post_func=fake_post,
    )

    assert result == "Hello world."


def test_cleanup_failure_falls_back_to_raw_text():
    def failing_post(endpoint, payload, timeout):
        raise OSError("offline")

    result = cleanup_text(
        "raw text",
        {"enabled": True, "provider": "ollama"},
        post_func=failing_post,
    )

    assert result == "raw text"
