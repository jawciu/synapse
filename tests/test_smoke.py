from reflect.auth import create_jwt, decode_jwt, hash_password, verify_password
from reflect.service import _normalize_reflection_source, _normalize_thread_id


def test_password_hash_roundtrip() -> None:
    password = "correct horse battery staple"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong-password", hashed)


def test_jwt_roundtrip() -> None:
    user_id = "app_user:test-user"
    token = create_jwt(user_id)

    assert decode_jwt(token) == user_id


def test_reflection_source_aliases() -> None:
    assert _normalize_reflection_source(None) == "app"
    assert _normalize_reflection_source("telegram") == "telegram_text"
    assert _normalize_reflection_source("telegram-voice") == "voice"
    assert _normalize_reflection_source("voice note") == "voice"
    assert _normalize_reflection_source("unknown-source") == "app"


def test_thread_id_normalization() -> None:
    assert _normalize_thread_id("chat-session-abc", "chat-session") == "chat-session-abc"

    generated = _normalize_thread_id(None, "chat-session")
    assert generated.startswith("chat-session-")
    assert len(generated) > len("chat-session-")
