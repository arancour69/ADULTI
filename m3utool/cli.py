"""Command-line interface for m3utool."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from m3utool import __version__
from m3utool.checker import Status, check_playlist, summarize
from m3utool.parser import ParseError, parse_file
from m3utool.sanitizer import sanitize
from m3utool.transform import dedupe, sort_entries
from m3utool.validator import Severity, has_errors, validate


def _load(path: str, strict: bool = False):
    try:
        return parse_file(path, strict=strict)
    except FileNotFoundError as exc:
        print(f"error: file not found: {path}", file=sys.stderr)
        raise SystemExit(2) from exc
    except ParseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


def _write_output(text: str, output: str | None) -> None:
    if output:
        Path(output).write_text(text, encoding="utf-8")
        print(f"wrote {output}")
    else:
        sys.stdout.write(text)


def cmd_validate(args: argparse.Namespace) -> int:
    playlist = _load(args.playlist, strict=args.strict)
    issues = validate(playlist)
    for issue in issues:
        stream = sys.stderr if issue.severity is Severity.ERROR else sys.stdout
        print(issue, file=stream)
    print(f"{len(playlist)} entries, {len(issues)} issue(s)")
    return 1 if has_errors(issues) else 0


def cmd_sanitize(args: argparse.Namespace) -> int:
    playlist = _load(args.playlist)
    result = sanitize(
        playlist, path_credentials=args.path_credentials, prefix=args.prefix
    )
    _write_output(result.playlist.to_m3u(), args.output)
    if args.env:
        Path(args.env).write_text(result.env_file(), encoding="utf-8")
        print(
            f"extracted {len(result.secrets)} secret(s) to {args.env} "
            f"({result.replacements} URL replacement(s))",
            file=sys.stderr,
        )
    else:
        print(
            f"extracted {len(result.secrets)} secret(s), "
            f"{result.replacements} URL replacement(s) "
            f"(pass --env to write them out)",
            file=sys.stderr,
        )
    return 0


def cmd_format(args: argparse.Namespace) -> int:
    playlist = _load(args.playlist)
    if not args.no_dedupe:
        playlist = dedupe(playlist, by=args.dedupe_by)
    if not args.no_sort:
        playlist = sort_entries(playlist, by_group=not args.no_group)
    _write_output(playlist.to_m3u(), args.output)
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    playlist = _load(args.playlist)
    results = check_playlist(playlist, timeout=args.timeout, workers=args.workers)
    for result in results:
        if result.status is Status.ALIVE and args.dead_only:
            continue
        print(f"{result.status.value:8} {result.name}  ({result.detail})")
    summary = summarize(results)
    print(
        f"alive={summary['alive']} dead={summary['dead']} skipped={summary['skipped']}",
        file=sys.stderr,
    )
    return 1 if summary["dead"] else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="m3utool",
        description="Generic, content-agnostic M3U playlist toolkit.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate", help="validate a playlist")
    p_validate.add_argument("playlist")
    p_validate.add_argument(
        "--strict", action="store_true", help="fail on the first parse error"
    )
    p_validate.set_defaults(func=cmd_validate)

    p_sanitize = sub.add_parser(
        "sanitize", help="externalize credentials from URLs into ${VAR} placeholders"
    )
    p_sanitize.add_argument("playlist")
    p_sanitize.add_argument("-o", "--output", help="write sanitized playlist here")
    p_sanitize.add_argument("--env", help="write extracted secrets to this .env file")
    p_sanitize.add_argument(
        "--prefix", default="M3U", help="prefix for generated env var names"
    )
    p_sanitize.add_argument(
        "--path-credentials",
        type=int,
        default=0,
        metavar="N",
        help="treat the first N path segments as credentials (e.g. 2 for /user/pass/)",
    )
    p_sanitize.set_defaults(func=cmd_sanitize)

    p_format = sub.add_parser("format", help="dedupe and sort a playlist")
    p_format.add_argument("playlist")
    p_format.add_argument("-o", "--output", help="write formatted playlist here")
    p_format.add_argument("--no-dedupe", action="store_true")
    p_format.add_argument("--no-sort", action="store_true")
    p_format.add_argument("--no-group", action="store_true", help="sort by name only")
    p_format.add_argument(
        "--dedupe-by", choices=["url", "name", "both"], default="url"
    )
    p_format.set_defaults(func=cmd_format)

    p_check = sub.add_parser("check", help="probe stream URLs for reachability")
    p_check.add_argument("playlist")
    p_check.add_argument("--timeout", type=float, default=10.0)
    p_check.add_argument("--workers", type=int, default=8)
    p_check.add_argument(
        "--dead-only", action="store_true", help="only print dead/skipped entries"
    )
    p_check.set_defaults(func=cmd_check)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
