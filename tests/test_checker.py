from m3utool.checker import Status, check_playlist, summarize
from m3utool.parser import parse


def make_probe(mapping):
    def probe(url, timeout):
        return mapping.get(url, (Status.DEAD, "unknown"))

    return probe


def test_check_playlist_with_injected_probe():
    text = (
        "#EXTINF:-1,Alive\nhttp://x/alive\n"
        "#EXTINF:-1,Dead\nhttp://x/dead\n"
    )
    probe = make_probe(
        {
            "http://x/alive": (Status.ALIVE, "HTTP 200"),
            "http://x/dead": (Status.DEAD, "timeout"),
        }
    )
    results = check_playlist(parse(text), probe=probe, workers=2)
    summary = summarize(results)
    assert summary["alive"] == 1
    assert summary["dead"] == 1
    assert summary["skipped"] == 0


def test_missing_url_is_skipped():
    playlist = parse("#EXTINF:-1,A\nhttp://x/a\n")
    playlist.entries[0].url = ""
    results = check_playlist(playlist, probe=make_probe({}))
    assert results[0].status is Status.SKIPPED
