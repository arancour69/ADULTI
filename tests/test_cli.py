from pathlib import Path

import pytest

from m3utool.cli import main


def write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_validate_clean_returns_zero(tmp_path, capsys):
    playlist = write(tmp_path, "p.m3u", "#EXTINF:-1,A\nhttp://x/a\n")
    assert main(["validate", playlist]) == 0


def test_validate_errors_return_one(tmp_path):
    playlist = write(tmp_path, "p.m3u", "#EXTINF:-1,A\nhttp://\n")
    assert main(["validate", playlist]) == 1


def test_sanitize_writes_output_and_env(tmp_path):
    src = write(tmp_path, "p.m3u", "#EXTINF:-1,A\nhttp://u:p@host/x\n")
    out = str(tmp_path / "clean.m3u")
    env = str(tmp_path / "creds.env")
    assert main(["sanitize", src, "-o", out, "--env", env]) == 0
    assert "u:p" not in Path(out).read_text()
    assert "M3U_USER=u" in Path(env).read_text()


def test_format_dedupes_and_sorts(tmp_path):
    text = (
        '#EXTINF:-1 group-title="B",two\nhttp://x/2\n'
        '#EXTINF:-1 group-title="A",one\nhttp://x/1\n'
        '#EXTINF:-1 group-title="A",one\nhttp://x/1\n'
    )
    src = write(tmp_path, "p.m3u", text)
    out = str(tmp_path / "out.m3u")
    assert main(["format", src, "-o", out]) == 0
    lines = [line for line in Path(out).read_text().splitlines() if line.startswith("#EXTINF")]
    assert len(lines) == 2
    assert "one" in lines[0]


def test_missing_file_exits_2(tmp_path):
    with pytest.raises(SystemExit) as exc:
        main(["validate", str(tmp_path / "nope.m3u")])
    assert exc.value.code == 2
