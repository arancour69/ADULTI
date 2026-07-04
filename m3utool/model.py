"""Data model for M3U playlists."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Matches key="value" attribute pairs on an #EXTINF line.
_ATTR_RE = re.compile(r'([A-Za-z0-9_-]+)="([^"]*)"')


@dataclass
class Entry:
    """A single playlist entry: one #EXTINF line and its stream URL."""

    duration: float
    title: str
    url: str
    attributes: dict[str, str] = field(default_factory=dict)
    # 1-based line number of the #EXTINF line in the source, when known.
    line_number: int | None = None

    @property
    def group_title(self) -> str:
        return self.attributes.get("group-title", "")

    @property
    def name(self) -> str:
        """Human-facing channel name (tvg-name falls back to the title)."""
        return self.attributes.get("tvg-name") or self.title

    def format_extinf(self) -> str:
        """Render the #EXTINF line for this entry."""
        duration = self.duration
        duration_str = str(int(duration)) if float(duration).is_integer() else str(duration)
        attrs = "".join(
            f' {key}="{value}"' for key, value in self.attributes.items()
        )
        return f"#EXTINF:{duration_str}{attrs},{self.title}"


@dataclass
class Playlist:
    """An ordered collection of playlist entries plus any header tags."""

    entries: list[Entry] = field(default_factory=list)
    # Lines that appear before the first entry (besides #EXTM3U), preserved verbatim.
    headers: list[str] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.entries)

    def __iter__(self):
        return iter(self.entries)

    def to_m3u(self) -> str:
        """Serialize the playlist back to Extended M3U text."""
        lines: list[str] = ["#EXTM3U"]
        lines.extend(self.headers)
        for entry in self.entries:
            lines.append(entry.format_extinf())
            lines.append(entry.url)
        return "\n".join(lines) + "\n"


def parse_attributes(raw: str) -> dict[str, str]:
    """Parse the key="value" attribute pairs from an #EXTINF attribute string."""
    return {match.group(1): match.group(2) for match in _ATTR_RE.finditer(raw)}
