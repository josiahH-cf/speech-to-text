from local_dictation import single_instance
from local_dictation.single_instance import acquire_single_instance


class _FakeWin32Event:
    def __init__(self):
        self.created = []

    def CreateMutex(self, _security, _initial_owner, name):
        self.created.append(name)
        return object()


def _fake_win32api(last_error):
    return type("FakeWin32Api", (), {"GetLastError": staticmethod(lambda: last_error)})


_FAKE_WINERROR = type("FakeWinError", (), {"ERROR_ALREADY_EXISTS": 183})


def test_acquire_single_instance_first_owner(monkeypatch):
    fake_event = _FakeWin32Event()
    monkeypatch.setattr(single_instance, "win32event", fake_event)
    monkeypatch.setattr(single_instance, "win32api", _fake_win32api(0))
    monkeypatch.setattr(single_instance, "winerror", _FAKE_WINERROR)

    assert acquire_single_instance("test-mutex") is True
    assert fake_event.created == ["test-mutex"]


def test_acquire_single_instance_second_instance(monkeypatch):
    fake_event = _FakeWin32Event()
    monkeypatch.setattr(single_instance, "win32event", fake_event)
    monkeypatch.setattr(single_instance, "win32api", _fake_win32api(183))
    monkeypatch.setattr(single_instance, "winerror", _FAKE_WINERROR)

    assert acquire_single_instance("test-mutex") is False


def test_acquire_single_instance_allows_when_pywin32_missing(monkeypatch):
    monkeypatch.setattr(single_instance, "win32event", None)
    monkeypatch.setattr(single_instance, "win32api", None)
    monkeypatch.setattr(single_instance, "winerror", None)

    assert acquire_single_instance() is True
