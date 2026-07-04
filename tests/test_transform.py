from m3utool.parser import parse
from m3utool.transform import dedupe, sort_entries


def test_dedupe_by_url_preserves_order():
    text = (
        "#EXTINF:-1,A\nhttp://x/1\n"
        "#EXTINF:-1,B\nhttp://x/2\n"
        "#EXTINF:-1,C\nhttp://x/1\n"
    )
    result = dedupe(parse(text), by="url")
    assert [e.title for e in result] == ["A", "B"]


def test_dedupe_by_name():
    text = (
        "#EXTINF:-1,Dup\nhttp://x/1\n"
        "#EXTINF:-1,Dup\nhttp://x/2\n"
    )
    result = dedupe(parse(text), by="name")
    assert len(result) == 1


def test_sort_by_group_then_name():
    text = (
        '#EXTINF:-1 group-title="Zoo",beta\nhttp://x/1\n'
        '#EXTINF:-1 group-title="Apples",delta\nhttp://x/2\n'
        '#EXTINF:-1 group-title="Apples",alpha\nhttp://x/3\n'
    )
    result = sort_entries(parse(text))
    assert [e.title for e in result] == ["alpha", "delta", "beta"]


def test_sort_by_name_only():
    text = (
        '#EXTINF:-1 group-title="Z",banana\nhttp://x/1\n'
        '#EXTINF:-1 group-title="A",apple\nhttp://x/2\n'
    )
    result = sort_entries(parse(text), by_group=False)
    assert [e.title for e in result] == ["apple", "banana"]
