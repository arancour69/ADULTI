"""Dead-link checker for playlist stream URLs."""

from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass
from enum import Enum
from typing import Callable
from urllib import error, request
from urllib.parse import urlsplit

from m3utool.model import Entry, Playlist


class Status(str, Enum):
    ALIVE = "alive"
    DEAD = "dead"
    SKIPPED = "skipped"


@dataclass
class CheckResult:
    entry: Entry
    status: Status
    detail: str = ""

    @property
    def name(self) -> str:
        return self.entry.name


ProbeFn = Callable[[str, float], "CheckResult"]


def _probe(url: str, timeout: float) -> tuple[Status, str]:
    scheme = urlsplit(url).scheme
    if scheme not in {"http", "https"}:
        return Status.SKIPPED, f"unsupported scheme {scheme!r}"
    req = request.Request(url, method="GET", headers={"User-Agent": "m3utool/0.1"})
    try:
        with request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (user-provided URLs)
            code = resp.getcode()
            if code is not None and 200 <= code < 400:
                return Status.ALIVE, f"HTTP {code}"
            return Status.DEAD, f"HTTP {code}"
    except error.HTTPError as exc:
        # A 401/403 means the endpoint responded, so the host is reachable.
        if exc.code in {401, 403, 405}:
            return Status.ALIVE, f"HTTP {exc.code}"
        return Status.DEAD, f"HTTP {exc.code}"
    except (error.URLError, TimeoutError, OSError) as exc:
        return Status.DEAD, str(exc)


def check_playlist(
    playlist: Playlist,
    *,
    timeout: float = 10.0,
    workers: int = 8,
    probe: Callable[[str, float], tuple[Status, str]] | None = None,
) -> list[CheckResult]:
    """Probe every entry's URL and return per-entry results.

    ``probe`` can be injected for testing; it receives ``(url, timeout)`` and
    returns ``(Status, detail)``.
    """
    probe_fn = probe or _probe
    results: list[CheckResult | None] = [None] * len(playlist.entries)

    def run(index: int, entry: Entry) -> None:
        if not entry.url:
            results[index] = CheckResult(entry, Status.SKIPPED, "no URL")
            return
        status, detail = probe_fn(entry.url, timeout)
        results[index] = CheckResult(entry, status, detail)

    max_workers = max(1, min(workers, len(playlist.entries) or 1))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [
            pool.submit(run, index, entry)
            for index, entry in enumerate(playlist.entries)
        ]
        for future in concurrent.futures.as_completed(futures):
            future.result()

    return [result for result in results if result is not None]


def summarize(results: list[CheckResult]) -> dict:
    """Return counts per status."""
    counts = {status: 0 for status in Status}
    for result in results:
        counts[result.status] += 1
    return {status.value: count for status, count in counts.items()}
