"""Parser for Extended M3U playlists."""

from __future__ import annotations

from pathlib import Path

from m3utool.model import Entry, Playlist, parse_attributes

_EXTINF_PREFIX = "#EXTINF:"


class ParseError(ValueError):
    """Raised when a playlist cannot be parsed in strict mode."""


def _split_extinf(payload: str) -> tuple[float, str, str]:
    """Split the text after '#EXTINF:' into (duration, attribute_str, title).

    Returns the raw attribute string so the caller can parse key="value" pairs.
    """
    # The title is everything after the first comma that is not inside quotes.
    in_quotes = False
    comma_index = -1
    for index, char in enumerate(payload):
        if char == '"':
            in_quotes = not in_quotes
        elif char == "," and not in_quotes:
            comma_index = index
            break
    if comma_index == -1:
        raise ParseError(f"#EXTINF line missing ',' separator: {payload!r}")

    head = payload[:comma_index].strip()
    title = payload[comma_index + 1 :].strip()

    # Duration is the leading token; attributes (if any) follow whitespace.
    parts = head.split(None, 1)
    duration_token = parts[0]
    attribute_str = parts[1] if len(parts) > 1 else ""
    try:
        duration = float(duration_token)
    except ValueError as exc:
        raise ParseError(f"Invalid #EXTINF duration {duration_token!r}") from exc
    return duration, attribute_str, title


def parse(text: str, *, strict: bool = False) -> Playlist:
    """Parse Extended M3U text into a :class:`Playlist`.

    In lenient mode (default) malformed or dangling lines are skipped. In strict
    mode a :class:`ParseError` is raised on the first problem.
    """
    lines = text.splitlines()
    playlist = Playlist()

    pending: Entry | None = None
    seen_first_entry = False

    for index, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped == "#EXTM3U" or stripped.startswith("#EXTM3U "):
            continue

        if stripped.startswith(_EXTINF_PREFIX):
            if pending is not None and strict:
                raise ParseError(
                    f"line {pending.line_number}: #EXTINF has no following URL"
                )
            payload = stripped[len(_EXTINF_PREFIX) :]
            try:
                duration, attribute_str, title = _split_extinf(payload)
            except ParseError:
                if strict:
                    raise
                pending = None
                continue
            pending = Entry(
                duration=duration,
                title=title,
                url="",
                attributes=parse_attributes(attribute_str),
                line_number=index,
            )
            continue

        if stripped.startswith("#"):
            # Some other directive/comment.
            if pending is None and not seen_first_entry:
                playlist.headers.append(stripped)
            continue

        # A non-comment, non-blank line is a URL.
        if pending is None:
            if strict:
                raise ParseError(f"line {index}: URL without a preceding #EXTINF")
            continue
        pending.url = stripped
        playlist.entries.append(pending)
        seen_first_entry = True
        pending = None

    if pending is not None and strict:
        raise ParseError(f"line {pending.line_number}: #EXTINF has no following URL")

    return playlist


def parse_file(path: str | Path, *, strict: bool = False) -> Playlist:
    """Parse a playlist from a file path."""
    content = Path(path).read_text(encoding="utf-8")
    return parse(content, strict=strict)


def read_entries(text: str) -> list[Entry]:
    """Convenience helper returning just the entries from playlist text."""
    return parse(text).entries
