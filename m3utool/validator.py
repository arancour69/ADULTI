"""Validation checks for M3U playlists."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse

from m3utool.model import Playlist


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass
class Issue:
    severity: Severity
    message: str
    line_number: int | None = None

    def __str__(self) -> str:
        location = f"line {self.line_number}: " if self.line_number is not None else ""
        return f"[{self.severity.value}] {location}{self.message}"


def _is_valid_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme in {"http", "https", "rtmp", "rtsp", "udp", "rtp"}:
        return bool(parsed.netloc)
    if parsed.scheme == "file":
        return bool(parsed.path)
    # Allow bare relative/absolute file paths.
    return "://" not in url and bool(url)


def validate(playlist: Playlist) -> list[Issue]:
    """Return a list of issues found in the playlist.

    Checks: missing URLs, malformed URLs, empty titles, negative/zero-count
    playlists, and duplicate channel names or URLs.
    """
    issues: list[Issue] = []

    if len(playlist) == 0:
        issues.append(Issue(Severity.WARNING, "playlist contains no entries"))

    names = Counter()
    urls = Counter()

    for entry in playlist:
        if not entry.url:
            issues.append(
                Issue(Severity.ERROR, f"entry {entry.title!r} has no URL", entry.line_number)
            )
        elif not _is_valid_url(entry.url):
            issues.append(
                Issue(
                    Severity.ERROR,
                    f"entry {entry.title!r} has a malformed URL: {entry.url!r}",
                    entry.line_number,
                )
            )
        if not entry.title.strip():
            issues.append(
                Issue(Severity.WARNING, "entry has an empty title", entry.line_number)
            )
        names[entry.name] += 1
        if entry.url:
            urls[entry.url] += 1

    for name, count in names.items():
        if count > 1:
            issues.append(
                Issue(Severity.WARNING, f"duplicate channel name {name!r} ({count} times)")
            )
    for url, count in urls.items():
        if count > 1:
            issues.append(
                Issue(Severity.WARNING, f"duplicate URL appears {count} times: {url!r}")
            )

    return issues


def has_errors(issues: list[Issue]) -> bool:
    return any(issue.severity is Severity.ERROR for issue in issues)
