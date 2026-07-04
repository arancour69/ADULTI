import pytest

from m3utool.parser import ParseError, parse

SAMPLE = """#EXTM3U
#EXTINF:-1 tvg-id="" tvg-name="Channel One" tvg-logo="a.png" group-title="News",Channel One
http://example.com/one
#EXTINF:0 group-title="Movies",Channel, With Comma
http://example.com/two
"""


def test_parse_basic():
    playlist = parse(SAMPLE)
    assert len(playlist) == 2
    first = playlist.entries[0]
    assert first.duration == -1
    assert first.name == "Channel One"
    assert first.group_title == "News"
    assert first.url == "http://example.com/one"


def test_title_with_comma_preserved():
    playlist = parse(SAMPLE)
    second = playlist.entries[1]
    assert second.title == "Channel, With Comma"
    assert second.group_title == "Movies"


def test_name_falls_back_to_title():
    playlist = parse('#EXTM3U\n#EXTINF:-1,Bare Title\nhttp://x/y\n')
    assert playlist.entries[0].name == "Bare Title"


def test_lenient_skips_extinf_without_url():
    text = "#EXTINF:-1,Orphan\n#EXTINF:-1,Real\nhttp://x/y\n"
    playlist = parse(text)
    assert len(playlist) == 1
    assert playlist.entries[0].title == "Real"


def test_strict_raises_on_missing_url():
    text = "#EXTINF:-1,Orphan\n#EXTINF:-1,Real\nhttp://x/y\n"
    with pytest.raises(ParseError):
        parse(text, strict=True)


def test_strict_raises_on_bad_extinf():
    with pytest.raises(ParseError):
        parse("#EXTINF:-1 no comma here\nhttp://x/y\n", strict=True)


def test_blank_lines_ignored():
    text = "#EXTM3U\n\n\n#EXTINF:-1,A\nhttp://x/a\n\n"
    assert len(parse(text)) == 1
