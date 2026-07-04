"""Normalization transforms: dedupe and sort playlist entries."""

from __future__ import annotations

from m3utool.model import Entry, Playlist


def dedupe(playlist: Playlist, *, by: str = "url") -> Playlist:
    """Return a new playlist with duplicate entries removed, preserving order.

    ``by`` selects the dedupe key: ``"url"``, ``"name"`` or ``"both"``.
    """
    seen = set()
    kept: list[Entry] = []
    for entry in playlist:
        if by == "url":
            key = entry.url
        elif by == "name":
            key = entry.name
        elif by == "both":
            key = (entry.name, entry.url)
        else:
            raise ValueError(f"unknown dedupe key: {by!r}")
        if key in seen:
            continue
        seen.add(key)
        kept.append(entry)
    return Playlist(entries=kept, headers=list(playlist.headers))


def sort_entries(playlist: Playlist, *, by_group: bool = True) -> Playlist:
    """Return a new playlist sorted by group-title then channel name.

    Sorting is stable and case-insensitive.
    """

    def key(entry: Entry):
        name = entry.name.lower()
        if by_group:
            return (entry.group_title.lower(), name)
        return (name,)

    ordered = sorted(playlist.entries, key=key)
    return Playlist(entries=ordered, headers=list(playlist.headers))
