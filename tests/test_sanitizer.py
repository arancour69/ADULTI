from m3utool.parser import parse
from m3utool.sanitizer import resolve, sanitize


def test_userinfo_credentials_externalized():
    playlist = parse("#EXTINF:-1,A\nhttp://alice:secret@host/stream\n")
    result = sanitize(playlist)
    url = result.playlist.entries[0].url
    assert "alice" not in url
    assert "secret" not in url
    assert "${M3U_USER}" in url
    assert "${M3U_PASS}" in url
    assert result.secrets["M3U_USER"] == "alice"
    assert result.secrets["M3U_PASS"] == "secret"


def test_query_credentials_externalized():
    playlist = parse("#EXTINF:-1,A\nhttp://host/s?username=bob&token=abc123&id=7\n")
    result = sanitize(playlist)
    url = result.playlist.entries[0].url
    assert "bob" not in url
    assert "abc123" not in url
    assert "id=7" in url
    assert result.secrets["M3U_USERNAME"] == "bob"
    assert result.secrets["M3U_TOKEN"] == "abc123"


def test_path_credentials_externalized():
    playlist = parse("#EXTINF:-1,A\nhttp://host:8080/joe/pw123/14493\n")
    result = sanitize(playlist, path_credentials=2)
    url = result.playlist.entries[0].url
    assert "joe" not in url
    assert "pw123" not in url
    assert "14493" in url
    assert result.secrets["M3U_USER"] == "joe"
    assert result.secrets["M3U_PASS"] == "pw123"


def test_identical_values_reuse_same_placeholder():
    text = (
        "#EXTINF:-1,A\nhttp://host/a/tok/1\n"
        "#EXTINF:-1,B\nhttp://host/a/tok/2\n"
    )
    result = sanitize(parse(text), path_credentials=2)
    # Both entries share user "a" and pass "tok" -> one var each.
    assert result.secrets["M3U_USER"] == "a"
    assert result.secrets["M3U_PASS"] == "tok"
    assert len(result.secrets) == 2


def test_env_file_and_roundtrip_resolve():
    playlist = parse("#EXTINF:-1,A\nhttp://u:p@host/x\n")
    result = sanitize(playlist)
    env_text = result.env_file()
    assert "M3U_USER=u" in env_text
    assert "M3U_PASS=p" in env_text
    restored = resolve(result.playlist.to_m3u(), result.secrets)
    assert "http://u:p@host/x" in restored


def test_no_credentials_is_noop():
    text = "#EXTINF:-1,A\nhttp://host/plain?id=1\n"
    result = sanitize(parse(text))
    assert result.replacements == 0
    assert result.secrets == {}
