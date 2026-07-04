from m3utool.parser import parse
from m3utool.validator import Severity, has_errors, validate


def test_detects_missing_url():
    playlist = parse("#EXTINF:-1,A\nhttp://x/a\n#EXTINF:-1,B\nhttp://x/b\n")
    # Force a missing URL.
    playlist.entries[0].url = ""
    issues = validate(playlist)
    assert has_errors(issues)
    assert any("has no URL" in issue.message for issue in issues)


def test_detects_malformed_url():
    playlist = parse("#EXTINF:-1,A\nhttp://\n")
    issues = validate(playlist)
    assert any(issue.severity is Severity.ERROR for issue in issues)


def test_detects_duplicate_names_and_urls():
    text = (
        "#EXTINF:-1,Same\nhttp://x/dup\n"
        "#EXTINF:-1,Same\nhttp://x/dup\n"
    )
    issues = validate(parse(text))
    messages = " ".join(i.message for i in issues)
    assert "duplicate channel name" in messages
    assert "duplicate URL" in messages


def test_clean_playlist_has_no_errors():
    text = "#EXTINF:-1,A\nhttp://x/a\n#EXTINF:-1,B\nhttp://x/b\n"
    issues = validate(parse(text))
    assert not has_errors(issues)


def test_empty_playlist_warns():
    issues = validate(parse("#EXTM3U\n"))
    assert any("no entries" in i.message for i in issues)
    assert not has_errors(issues)
