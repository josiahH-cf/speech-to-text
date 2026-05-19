from local_dictation.insertion import (
    ClipboardItem,
    ClipboardSnapshot,
    IntegrityLevel,
    can_inject_into_target,
    classify_integrity_rid,
    should_restore_text_clipboard,
    utf16_units,
)


def test_should_restore_previous_text_clipboard():
    assert should_restore_text_clipboard(True, "before", "after") is True


def test_should_not_restore_when_disabled_or_missing():
    assert should_restore_text_clipboard(False, "before", "after") is False
    assert should_restore_text_clipboard(True, None, "after") is False
    assert should_restore_text_clipboard(True, "same", "same") is False


def test_utf16_units_handles_surrogate_pairs():
    assert utf16_units("A") == [0x0041]
    assert utf16_units("🙂") == [0xD83D, 0xDE42]


def test_integrity_classification_and_injection_rules():
    assert classify_integrity_rid(0x1000) == IntegrityLevel.LOW
    assert classify_integrity_rid(0x2000) == IntegrityLevel.MEDIUM
    assert classify_integrity_rid(0x3000) == IntegrityLevel.HIGH
    assert can_inject_into_target(IntegrityLevel.MEDIUM, IntegrityLevel.MEDIUM) is True
    assert can_inject_into_target(IntegrityLevel.MEDIUM, IntegrityLevel.HIGH) is False
    assert can_inject_into_target(IntegrityLevel.UNKNOWN, IntegrityLevel.HIGH) is True


def test_clipboard_snapshot_reports_items():
    assert ClipboardSnapshot(()).has_items is False
    assert ClipboardSnapshot((ClipboardItem(13, "text"),)).has_items is True
