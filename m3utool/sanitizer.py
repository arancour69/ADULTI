"""Externalize credentials embedded in playlist URLs.

The sanitizer never *uses* credentials; it removes them from committed URLs and
replaces them with ``${VAR}`` placeholders, returning the extracted values so a
caller can store them in a ``.env`` file (which should not be committed).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from m3utool.model import Entry, Playlist

# Query-string keys commonly used to carry credentials.
CREDENTIAL_QUERY_KEYS = {
    "username",
    "user",
    "password",
    "pass",
    "pwd",
    "token",
    "auth",
    "apikey",
    "api_key",
    "key",
}

_PLACEHOLDER_RE = re.compile(r"\$\{([A-Z0-9_]+)\}")


@dataclass
class SanitizeResult:
    playlist: Playlist
    secrets: dict[str, str] = field(default_factory=dict)
    replacements: int = 0

    def env_file(self) -> str:
        """Render the extracted secrets as .env file content."""
        lines = [f"{key}={value}" for key, value in self.secrets.items()]
        return "\n".join(lines) + ("\n" if lines else "")


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").upper()
    return slug or "VALUE"


class _SecretStore:
    """Assigns stable placeholder names to secret values."""

    def __init__(self, prefix: str = "M3U") -> None:
        self.prefix = prefix
        self.by_value: dict[tuple[str, str], str] = {}
        self.secrets: dict[str, str] = {}

    def placeholder(self, hint: str, value: str) -> str:
        cache_key = (hint, value)
        if cache_key in self.by_value:
            return self.by_value[cache_key]
        base = f"{self.prefix}_{_slug(hint)}"
        name = base
        suffix = 1
        # Reuse the name for identical values; disambiguate different values.
        while name in self.secrets and self.secrets[name] != value:
            suffix += 1
            name = f"{base}_{suffix}"
        self.secrets[name] = value
        self.by_value[cache_key] = name
        return f"${{{name}}}"


def _sanitize_url(url: str, store: _SecretStore, path_credentials: int) -> tuple[str, int]:
    replacements = 0
    parts = urlsplit(url)

    netloc = parts.netloc
    # Extract userinfo (user:pass@host).
    if "@" in netloc:
        userinfo, host = netloc.rsplit("@", 1)
        if ":" in userinfo:
            user, password = userinfo.split(":", 1)
            user_ph = store.placeholder("user", user) if user else user
            pass_ph = store.placeholder("pass", password)
            netloc = f"{user_ph}:{pass_ph}@{host}"
            replacements += 2
        elif userinfo:
            user_ph = store.placeholder("user", userinfo)
            netloc = f"{user_ph}@{host}"
            replacements += 1

    # Extract credential-bearing query parameters.
    query_pairs = parse_qsl(parts.query, keep_blank_values=True)
    if query_pairs:
        new_pairs: list[tuple[str, str]] = []
        for key, value in query_pairs:
            if key.lower() in CREDENTIAL_QUERY_KEYS and value:
                new_pairs.append((key, store.placeholder(key, value)))
                replacements += 1
            else:
                new_pairs.append((key, value))
        query = urlencode(new_pairs, safe="${}")
    else:
        query = parts.query

    # Optionally treat the first N path segments as credentials (e.g. Xtream
    # codes style /USER/PASS/id).
    path = parts.path
    if path_credentials > 0 and path:
        segments = path.split("/")
        # segments[0] is empty because path starts with '/'.
        cred_indices = [i for i in range(1, len(segments)) if segments[i]][:path_credentials]
        for order, idx in enumerate(cred_indices):
            hint = "user" if order == 0 else ("pass" if order == 1 else f"seg{order}")
            segments[idx] = store.placeholder(hint, segments[idx])
            replacements += 1
        path = "/".join(segments)

    new_url = urlunsplit((parts.scheme, netloc, path, query, parts.fragment))
    return new_url, replacements


def sanitize(
    playlist: Playlist,
    *,
    path_credentials: int = 0,
    prefix: str = "M3U",
) -> SanitizeResult:
    """Return a new playlist with credentials replaced by ``${VAR}`` placeholders.

    Parameters
    ----------
    path_credentials:
        Number of leading path segments to treat as credentials (0 disables).
    prefix:
        Prefix for generated environment variable names.
    """
    store = _SecretStore(prefix=prefix)
    new_entries: list[Entry] = []
    total = 0
    for entry in playlist:
        new_url, replaced = _sanitize_url(entry.url, store, path_credentials)
        total += replaced
        new_entries.append(
            Entry(
                duration=entry.duration,
                title=entry.title,
                url=new_url,
                attributes=dict(entry.attributes),
                line_number=entry.line_number,
            )
        )
    new_playlist = Playlist(entries=new_entries, headers=list(playlist.headers))
    return SanitizeResult(playlist=new_playlist, secrets=store.secrets, replacements=total)


def resolve(text: str, env: dict[str, str]) -> str:
    """Substitute ``${VAR}`` placeholders in text using the given env mapping.

    Missing variables are left untouched so problems are visible rather than
    silently producing broken URLs.
    """

    def _replace(match: re.Match[str]) -> str:
        name = match.group(1)
        return env.get(name, match.group(0))

    return _PLACEHOLDER_RE.sub(_replace, text)
