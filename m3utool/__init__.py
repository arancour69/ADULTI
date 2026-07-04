"""m3utool: a generic, content-agnostic M3U playlist toolkit.

Provides parsing, validation, credential sanitization, normalization and
dead-link checking for M3U / M3U8 (Extended M3U) playlists.
"""

from m3utool.model import Entry, Playlist
from m3utool.parser import ParseError, parse, parse_file

__all__ = [
    "Entry",
    "Playlist",
    "ParseError",
    "parse",
    "parse_file",
]

__version__ = "0.1.0"
