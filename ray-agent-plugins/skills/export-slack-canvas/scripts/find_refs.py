#!/usr/bin/env python3
"""Extract unique Slack message references from a Canvas markdown file.

Input: path to a markdown file (typically the `markdown_content` returned by
`slack_read_canvas`).

Output: one JSON object per line, each with:
  - channel_id: the Slack channel ID (e.g. "C08DP1PL53R")
  - thread_ts:  the parent timestamp of the enclosing thread
                (falls back to message_ts when the reference is to a top-level
                message with no `thread_ts` query param)
  - message_ts: the timestamp of the specific referenced message, derived from
                the `p<digits>` URL segment by splitting at len-6 — e.g.
                `p1754940948911339` -> `1754940948.911339`

Dedup rule: one line per (channel_id, thread_ts). A single Canvas frequently
references the same thread twice in the same block — once as an icon bookmark
`[](URL)` and once as a plain `Original message: URL` — so fetching each thread
once is sufficient.

The caller then fans out `slack_read_thread` calls (in `detailed` mode) over
the emitted lines.
"""

from __future__ import annotations

import json
import re
import sys
from urllib.parse import parse_qs, urlparse

SLACK_ARCHIVE_URL = re.compile(
    r"https://[\w.-]*\.slack\.com/archives/(?P<cid>[A-Z0-9]+)/p(?P<pdigits>\d+)"
    r"(?P<query>\?[^\s)<>\"]*)?",
    re.IGNORECASE,
)


def pdigits_to_ts(pdigits: str) -> str:
    """Convert the `p<digits>` URL segment to Slack's dotted `ts` format.

    Slack timestamps are always "<10-digit seconds>.<6-digit microseconds>"
    joined into the URL without the dot. The trailing 6 digits are microseconds.
    """
    if len(pdigits) <= 6:
        return pdigits
    return f"{pdigits[:-6]}.{pdigits[-6:]}"


def extract_refs(markdown: str) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    refs: list[dict[str, str]] = []
    for match in SLACK_ARCHIVE_URL.finditer(markdown):
        channel_id = match.group("cid")
        message_ts = pdigits_to_ts(match.group("pdigits"))
        query = match.group("query") or ""
        thread_ts = message_ts
        if query:
            parsed = parse_qs(urlparse(query).query)
            if "thread_ts" in parsed and parsed["thread_ts"]:
                thread_ts = parsed["thread_ts"][0]
        key = (channel_id, thread_ts)
        if key in seen:
            continue
        seen.add(key)
        refs.append(
            {
                "channel_id": channel_id,
                "thread_ts": thread_ts,
                "message_ts": message_ts,
            }
        )
    return refs


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: find_refs.py <canvas-markdown-file>", file=sys.stderr)
        return 2
    with open(argv[1], encoding="utf-8") as fh:
        markdown = fh.read()
    for ref in extract_refs(markdown):
        print(json.dumps(ref))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
