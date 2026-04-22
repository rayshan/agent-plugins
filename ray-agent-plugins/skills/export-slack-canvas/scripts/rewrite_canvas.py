#!/usr/bin/env python3
"""Rewrite a Slack Canvas markdown file with referenced messages inlined.

Given the raw Canvas markdown and a bundle of fetched threads, produce a new
markdown file where every Slack message URL reference is replaced with a
blockquoted rendering of *just the referenced message* (not the whole thread).

The script is deliberately conservative about what it rewrites: it only touches
Slack archive URLs and their immediate wrappers. Everything else in the Canvas
is passed through unchanged.

Inputs
------
--canvas <path>    Path to the Canvas markdown (typically the `markdown_content`
                   field from `slack_read_canvas`, written to a file).
--threads <path>   Path to a JSON file shaped like:
                       [
                         {
                           "channel_id": "C08DP1PL53R",
                           "thread_ts":  "1754594931.762139",
                           "messages":   "<verbatim output of slack_read_thread
                                          in detailed mode>"
                         },
                         ...
                       ]
                   (The MCP returns each thread as a single string with a
                   `=== THREAD PARENT MESSAGE ===` block and `--- Reply N of M ---`
                   sections. This script parses that format.)
--output <path>    Where to write the rewritten markdown.

Options
-------
--uniquify-headings  When a heading text repeats within the document (common
                     with boilerplate headings like `## Decision`), append a
                     short disambiguating suffix so strict Markdown linters
                     (rumdl MD024) don't choke. Off by default.

Behavior
--------
Empty-anchor bookmarks (`[](URL)`) and inline "Original message: URL" lines
that point to the same `(channel_id, message_ts)` within the same heading
section collapse to a single expansion. This matches the Canvas convention of
dual-referencing the same message (an icon link plus a plain paragraph).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

SLACK_URL = re.compile(
    r"https://[\w.-]*\.slack\.com/archives/(?P<cid>[A-Z0-9]+)/p(?P<pdigits>\d+)"
    r"(?P<query>\?[^\s)<>\"]*)?",
    re.IGNORECASE,
)

# Matches whole paragraphs we want to replace:
#   1. `[](URL)`                           — Canvas bookmark with empty alt
#   2. `**Original message:** [URL](URL)`  — Canvas "Original message" prefix
# A line with text/mixed content keeps its URL rewritten in place instead.
BOOKMARK_LINE = re.compile(r"^\s*\[\s*\]\((?P<url>https?://[^\s)]+)\)\s*$")
ORIGINAL_MESSAGE_LINE = re.compile(
    r"^\s*\*\*Original message:\*\*\s*.*?(?P<url>https?://[\S]+)\s*$",
    re.IGNORECASE,
)

THREAD_PARENT_HEADER = re.compile(r"===\s*THREAD PARENT MESSAGE\s*===", re.IGNORECASE)
THREAD_REPLY_HEADER = re.compile(r"---\s*Reply\s+\d+\s+of\s+\d+\s*---", re.IGNORECASE)
KV_LINE = re.compile(r"^(?P<key>From|Time|Message TS):\s*(?P<val>.*)$")


@dataclass
class SlackMessage:
    """A single message inside a fetched thread."""

    author: str  # "Jiaru Cao" (user id suffix stripped)
    time: str  # "2025-08-11 12:35:48 PDT"
    ts: str  # "1754940948.911339"
    text: str  # raw message text, newlines preserved


def parse_detailed_thread(raw: str) -> list[SlackMessage]:
    """Parse the text blob returned by `slack_read_thread(response_format='detailed')`.

    The blob looks like:

        === THREAD PARENT MESSAGE ===
        From: Mica Cole (U9SDL9Z4M)
        Time: 2025-08-07 12:28:51 PDT
        Message TS: 1754594931.762139
        <parent message text>

        Reactions: ...
        Files: ...

        === THREAD REPLIES (15 total) ===

        --- Reply 1 of 15 ---
        From: ...
        Time: ...
        Message TS: ...
        <reply text>

    Reactions/Files/pagination lines are dropped — we want just the message body.
    """
    messages: list[SlackMessage] = []
    # Split on reply/parent boundaries; keep the delimiters so we can detect
    # which section we're in.
    boundary = re.compile(
        r"(===\s*THREAD PARENT MESSAGE\s*===|---\s*Reply\s+\d+\s+of\s+\d+\s*---)",
        re.IGNORECASE,
    )
    parts = boundary.split(raw)
    # parts is [preamble, delim1, body1, delim2, body2, ...]
    for i in range(1, len(parts), 2):
        body = parts[i + 1] if i + 1 < len(parts) else ""
        msg = _parse_message_block(body)
        if msg is not None:
            messages.append(msg)
    return messages


def _parse_message_block(block: str) -> SlackMessage | None:
    author = ""
    time = ""
    ts = ""
    text_lines: list[str] = []
    # The MCP's per-message payload has a small, stable header (From/Time/
    # Message TS), a blank line, the body, and optional Reactions:/Files:
    # trailers. We scan every line: KV headers are extracted regardless of
    # position so empty leading lines don't trip us up, and the trailers and
    # section markers are filtered out of the body.
    seen_body = False
    for line in block.splitlines():
        kv = KV_LINE.match(line)
        if kv and not seen_body:
            key = kv.group("key")
            val = kv.group("val").strip()
            if key == "From":
                # "Mica Cole (U9SDL9Z4M)" -> "Mica Cole"
                author = re.sub(r"\s*\([^)]*\)\s*$", "", val)
            elif key == "Time":
                time = val
            elif key == "Message TS":
                ts = val
            continue
        if line.startswith("Reactions:") or line.startswith("Files:"):
            continue
        if "=== THREAD REPLIES" in line or THREAD_PARENT_HEADER.search(line):
            break
        # Any non-KV, non-trailer line flips us into body mode so later KV-
        # shaped lines inside the message (unlikely, but possible) are kept
        # verbatim.
        if line.strip():
            seen_body = True
        text_lines.append(line)
    text = "\n".join(text_lines).strip("\n")
    if not ts and not text.strip():
        return None
    return SlackMessage(author=author, time=time, ts=ts, text=text)


def build_index(
    threads: list[dict],
) -> dict[tuple[str, str], SlackMessage]:
    """Build a lookup from (channel_id, message_ts) -> SlackMessage."""
    index: dict[tuple[str, str], SlackMessage] = {}
    for t in threads:
        cid = t["channel_id"]
        for msg in parse_detailed_thread(t["messages"]):
            if msg.ts:
                index[(cid, msg.ts)] = msg
    return index


def parse_url(url: str) -> tuple[str, str, str] | None:
    m = SLACK_URL.search(url)
    if not m:
        return None
    cid = m.group("cid")
    pdigits = m.group("pdigits")
    if len(pdigits) > 6:
        message_ts = f"{pdigits[:-6]}.{pdigits[-6:]}"
    else:
        message_ts = pdigits
    thread_ts = message_ts
    q = m.group("query") or ""
    if q:
        parsed = parse_qs(urlparse(q).query)
        if parsed.get("thread_ts"):
            thread_ts = parsed["thread_ts"][0]
    return cid, thread_ts, message_ts


def render_message(msg: SlackMessage, url: str) -> list[str]:
    """Render a single message as a blockquote block."""
    header_bits = []
    if msg.author:
        header_bits.append(f"**{msg.author}**")
    if msg.time:
        header_bits.append(f"({msg.time})")
    header_bits.append(f"— [source]({url})")
    header = " ".join(header_bits)
    lines = [f"> {header}", ">"]
    body = msg.text or "_(message body was empty or only contained attachments)_"
    for raw in body.splitlines():
        lines.append(f"> {raw}" if raw else ">")
    return lines


def rewrite(
    canvas_md: str,
    index: dict[tuple[str, str], SlackMessage],
    uniquify_headings: bool,
) -> str:
    out_lines: list[str] = []
    # Track which (cid, message_ts) pairs have already been expanded within the
    # current heading section, so a Canvas block that references the same
    # message twice produces only one expansion.
    expanded_in_section: set[tuple[str, str]] = set()
    # Headings seen, for MD024 uniquification.
    heading_counts: dict[str, int] = {}

    for raw_line in canvas_md.splitlines():
        line = raw_line
        stripped = line.strip()

        # Resetting the "already expanded" set at every heading gives the
        # right behavior for typical Canvas layouts where each section is a
        # self-contained block.
        if stripped.startswith("#"):
            expanded_in_section.clear()
            if uniquify_headings:
                line = _maybe_uniquify(line, heading_counts)
            out_lines.append(line)
            continue

        # Case 1: empty-anchor bookmark on its own line.
        m = BOOKMARK_LINE.match(line)
        if m:
            expansion = _expand_url(m.group("url"), index, expanded_in_section)
            if expansion is not None:
                out_lines.extend(expansion)
            else:
                out_lines.append(line)
            continue

        # Case 2: "**Original message:** URL" pattern.
        m = ORIGINAL_MESSAGE_LINE.match(line)
        if m:
            expansion = _expand_url(m.group("url"), index, expanded_in_section)
            if expansion is not None:
                out_lines.extend(expansion)
            else:
                out_lines.append(line)
            continue

        # Case 3: any other line containing a Slack URL — leave structure alone.
        out_lines.append(line)

    return "\n".join(out_lines) + ("\n" if canvas_md.endswith("\n") else "")


def _expand_url(
    url: str,
    index: dict[tuple[str, str], SlackMessage],
    expanded_in_section: set[tuple[str, str]],
) -> list[str] | None:
    parsed = parse_url(url)
    if parsed is None:
        return None
    cid, _, message_ts = parsed
    key = (cid, message_ts)
    if key in expanded_in_section:
        return [""]  # already expanded in this section; drop the duplicate line
    msg = index.get(key)
    if msg is None:
        return None
    expanded_in_section.add(key)
    return render_message(msg, url)


def _maybe_uniquify(heading_line: str, counts: dict[str, int]) -> str:
    text = heading_line.rstrip()
    counts[text] = counts.get(text, 0) + 1
    if counts[text] == 1:
        return heading_line
    return (
        f"{heading_line.rstrip()} ({counts[text]})\n"
        if heading_line.endswith("\n")
        else f"{heading_line.rstrip()} ({counts[text]})"
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--canvas", required=True)
    parser.add_argument("--threads", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--uniquify-headings", action="store_true")
    args = parser.parse_args(argv[1:])

    with open(args.canvas, encoding="utf-8") as fh:
        canvas_md = fh.read()
    with open(args.threads, encoding="utf-8") as fh:
        threads = json.load(fh)

    index = build_index(threads)
    rewritten = rewrite(canvas_md, index, uniquify_headings=args.uniquify_headings)

    with open(args.output, "w", encoding="utf-8") as fh:
        fh.write(rewritten)
    print(args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
