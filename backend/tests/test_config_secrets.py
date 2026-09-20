"""Tests for credential loading and encoder settings.

Every test here redirects CONFIG_PATH at a tmp_path first. The module-level
default is /data/config.json, which in a running container is the real saved
login — a test that forgets this overwrites it.
"""

import json

import pytest

from app import encoding, state as state_mod
from app.state import AppState


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    """Redirect both on-disk locations and clear the environment.

    CONFIG_PATH and SECRETS_DIR default to real container paths; without this
    a test run overwrites the live saved login.
    """
    monkeypatch.setattr(state_mod, "CONFIG_PATH", tmp_path / "config.json")
    monkeypatch.setattr(state_mod, "SECRETS_DIR", tmp_path / "run_secrets")
    for var in ("TABLO_PASSWORD", "TABLO_PASSWORD_FILE", "TABLO_EMAIL", "TABLO_SID"):
        monkeypatch.delenv(var, raising=False)
    return tmp_path


def test_no_credentials_anywhere(isolate):
    assert AppState._secret("tablo_password") is None


def test_env_var_is_used(isolate, monkeypatch):
    monkeypatch.setenv("TABLO_PASSWORD", "from-env")
    assert AppState._secret("tablo_password") == "from-env"


def test_file_beats_env(isolate, monkeypatch):
    secret = isolate / "secret"
    secret.write_text("  from-file  \n")
    monkeypatch.setenv("TABLO_PASSWORD_FILE", str(secret))
    monkeypatch.setenv("TABLO_PASSWORD", "from-env")
    assert AppState._secret("tablo_password") == "from-file"


def test_missing_file_falls_back(isolate, monkeypatch):
    monkeypatch.setenv("TABLO_PASSWORD_FILE", str(isolate / "absent"))
    monkeypatch.setenv("TABLO_PASSWORD", "from-env")
    assert AppState._secret("tablo_password") == "from-env"


def test_secret_password_is_not_written_to_disk(isolate, monkeypatch):
    secret = isolate / "secret"
    secret.write_text("from-file")
    monkeypatch.setenv("TABLO_PASSWORD_FILE", str(secret))

    AppState().save_config("me@example.com", "from-file")

    cfg = json.loads((isolate / "config.json").read_text())
    assert cfg == {"email": "me@example.com"}


def test_typed_password_is_still_written(isolate):
    AppState().save_config("me@example.com", "typed-in-ui")

    cfg = json.loads((isolate / "config.json").read_text())
    assert cfg["password"] == "typed-in-ui"


def test_existing_config_still_loads(isolate):
    """Upgrading from a version that stored the password must not log you out."""
    (isolate / "config.json").write_text(
        json.dumps({"email": "me@example.com", "password": "stored"}))

    st = AppState()
    st.load_config()

    assert st.email == "me@example.com"
    assert st.auth is not None


class _Dev:
    def __init__(self, sid):
        self.sid = sid


def test_single_device_needs_no_setting(isolate):
    only = _Dev("SID_AAA")
    assert AppState._pick_device([only]) is only


def test_two_devices_are_ambiguous_without_tablo_sid(isolate):
    assert AppState._pick_device([_Dev("SID_AAA"), _Dev("SID_BBB")]) is None


def test_tablo_sid_resolves_the_ambiguity(isolate, monkeypatch):
    a, b = _Dev("SID_AAA"), _Dev("SID_BBB")
    monkeypatch.setenv("TABLO_SID", "SID_BBB")
    assert AppState._pick_device([a, b]) is b


def test_tablo_sid_accepts_a_suffix(isolate, monkeypatch):
    a, b = _Dev("SID_5087B850A797"), _Dev("SID_5087B8546D56")
    monkeypatch.setenv("TABLO_SID", "5087B8546D56")
    assert AppState._pick_device([a, b]) is b


def test_unknown_tablo_sid_does_not_pick_the_wrong_box(isolate, monkeypatch):
    monkeypatch.setenv("TABLO_SID", "SID_NOPE")
    assert AppState._pick_device([_Dev("SID_AAA"), _Dev("SID_BBB")]) is None


def test_encoder_defaults_beat_upstreams(monkeypatch):
    for var in ("TABLO_CRF", "TABLO_PRESET", "TABLO_MAXRATE", "TABLO_AUDIO_BITRATE"):
        monkeypatch.delenv(var, raising=False)
    args = encoding.video_args() + encoding.audio_args()

    assert args[args.index("-crf") + 1] == "21"          # upstream: 28
    assert args[args.index("-preset") + 1] == "veryfast"  # upstream: ultrafast
    assert args[args.index("-maxrate") + 1] == "8000k"    # upstream: 2000k
    assert args[args.index("-b:a") + 1] == "192k"         # upstream: 128k


def test_encoder_env_overrides_apply(monkeypatch):
    monkeypatch.setenv("TABLO_CRF", "18")
    monkeypatch.setenv("TABLO_DEINTERLACE", "1")
    args = encoding.video_args()

    assert args[args.index("-crf") + 1] == "18"
    assert "yadif=1" in args


def test_compose_default_secret_path_is_read(isolate, monkeypatch):
    """A plain Compose `secrets:` entry needs no extra configuration."""
    mounted = isolate / "run_secrets"
    mounted.mkdir()
    (mounted / "tablo_password").write_text("from-compose\n")
    monkeypatch.setenv("TABLO_PASSWORD", "from-env")

    assert AppState._secret("tablo_password") == "from-compose"
