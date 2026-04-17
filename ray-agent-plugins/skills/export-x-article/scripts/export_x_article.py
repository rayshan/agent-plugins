#!/usr/bin/env python3
"""Export an X (Twitter) status as a markdown file.

Fetches via the unauthenticated fxtwitter API, which returns the full
long-form article payload when one is attached. Renders the article's
draftjs-style block list into clean markdown while preserving headings,
bold/italic spans, inline links, @mentions, and media captions.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime


TWEET_URL_RE = re.compile(r"(?:x|twitter)\.com/([^/?#]+)/status/(\d+)")


def extract_handle_and_id(url: str) -> tuple[str, str]:
    m = TWEET_URL_RE.search(url)
    if not m:
        sys.exit(f"Not a valid X/Twitter status URL: {url}")
    return m.group(1), m.group(2)


def fetch_tweet(handle: str, tweet_id: str) -> dict:
    api = f"https://api.fxtwitter.com/{handle}/status/{tweet_id}"
    result = subprocess.run(["curl", "-sSfL", api], capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"curl failed: {result.stderr.strip()}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        sys.exit(f"API returned non-JSON response: {e}")
    if payload.get("code") != 200 or "tweet" not in payload:
        sys.exit(f"API error: {payload.get('message', 'unknown')}")
    return payload["tweet"]


def kebab(value: str, max_len: int = 80) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug[:max_len].rstrip("-") or "untitled"


def parse_twitter_date(created_at: str) -> datetime:
    # Format: "Thu Mar 05 22:08:39 +0000 2026"
    return datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")


def apply_inline(text: str, style_ranges, block_data) -> str:
    """Overlay bold/italic/mention annotations onto a plain text block.

    Applies annotations right-to-left so earlier offsets stay valid.
    """
    annotations: list[tuple[int, int, str, str]] = []

    def trim_range(offset: int, length: int) -> tuple[int, int]:
        """Shrink a range to exclude leading/trailing whitespace.

        Markdown emphasis breaks when wrappers abut whitespace (e.g.,
        `**word **`), so pull any padding outside the bold/italic span.
        """
        end = offset + length
        while offset < end and text[offset].isspace():
            offset += 1
        while end > offset and text[end - 1].isspace():
            end -= 1
        return offset, end - offset

    for r in style_ranges or []:
        style = r.get("style")
        offset, length = trim_range(r.get("offset", 0), r.get("length", 0))
        if length <= 0:
            continue
        if style == "Bold":
            annotations.append((offset, length, "**", "**"))
        elif style == "Italic":
            annotations.append((offset, length, "*", "*"))

    for mention in (block_data or {}).get("mentions", []) or []:
        start, end = mention["fromIndex"], mention["toIndex"]
        handle = mention["text"]
        annotations.append((start, end - start, "[", f"](https://x.com/{handle})"))

    annotations.sort(key=lambda a: a[0], reverse=True)
    out = text
    for offset, length, left, right in annotations:
        out = (
            out[:offset]
            + left
            + out[offset : offset + length]
            + right
            + out[offset + length :]
        )
    return out


def is_heading_block(block: dict) -> bool:
    """A block is an H2 when a single Bold span covers its entire text.

    X's article editor uses full-line bold as the only in-band signal for
    section headings; partial-bold openers (e.g. 'Insurance brokerage
    ($140-200B).') are body text with inline emphasis.
    """
    text = block.get("text", "")
    styles = block.get("inlineStyleRanges", [])
    if not text.strip() or len(styles) != 1:
        return False
    s = styles[0]
    return (
        s.get("style") == "Bold"
        and s.get("offset") == 0
        and s.get("length") == len(text)
    )


def find_media(entity_map, media_entities, key) -> tuple[str, str]:
    """Look up caption + image URL for an atomic block's entity reference."""
    entry = next((e for e in entity_map if str(e.get("key")) == str(key)), None)
    if not entry:
        return "", ""
    data = entry.get("value", {}).get("data", {})
    caption = data.get("caption", "")
    items = data.get("mediaItems") or []
    if not items:
        return caption, ""
    media_id = items[0].get("mediaId")
    media = next(
        (m for m in media_entities if str(m.get("media_id")) == str(media_id)), None
    )
    url = (media or {}).get("media_info", {}).get("original_img_url", "")
    return caption, url


def render_article(article: dict) -> str:
    content = article.get("content", {}) or {}
    blocks = content.get("blocks", []) or []
    entity_map = content.get("entityMap", []) or []
    media_entities = article.get("media_entities", []) or []

    rendered: list[str] = []
    for block in blocks:
        btype = block.get("type")
        if btype == "atomic":
            ents = block.get("entityRanges", [])
            if not ents:
                continue
            caption, url = find_media(entity_map, media_entities, ents[0]["key"])
            if url and caption:
                rendered.append(f"![{caption}]({url})\n\n*Figure: {caption}.*")
            elif url:
                rendered.append(f"![]({url})")
            elif caption:
                rendered.append(f"*Figure: {caption}.*")
            continue

        text = block.get("text", "")
        if not text.strip():
            continue
        if is_heading_block(block):
            rendered.append(f"## {text}")
        else:
            rendered.append(
                apply_inline(text, block.get("inlineStyleRanges"), block.get("data"))
            )
    return "\n\n".join(rendered)


def render_markdown(tweet: dict, source_url: str) -> tuple[str, str]:
    author = tweet.get("author", {}) or {}
    created = parse_twitter_date(tweet["created_at"])
    date_str = created.strftime("%Y-%m-%d")
    article = tweet.get("article")

    if article and article.get("title"):
        title = article["title"]
    else:
        text = tweet.get("text") or tweet.get("raw_text", {}).get("text") or ""
        title = (
            text.strip().splitlines()[0][:80]
            if text.strip()
            else f"Tweet {tweet.get('id', '')}"
        )

    role = (author.get("description") or "").strip()
    handle = author.get("screen_name", "")
    author_line = f"**Author:** {author.get('name', handle)} ([@{handle}]({author.get('url', '')}))"
    if role:
        author_line += f", {role}"

    header_lines = [
        f"# {title}",
        "",
        author_line,
    ]
    if author.get("location"):
        header_lines.append(f"**Location:** {author['location']}")
    header_lines += [
        f"**Posted:** {date_str}",
        f"**Source:** <{source_url}>",
    ]

    if article:
        body = render_article(article)
    else:
        body = (
            tweet.get("text") or tweet.get("raw_text", {}).get("text") or ""
        ).strip()

    stats_bits = [
        f"{tweet.get('likes', 0):,} likes",
        f"{tweet.get('retweets', 0):,} reposts",
        f"{tweet.get('quotes', 0):,} quotes",
        f"{tweet.get('replies', 0):,} replies",
        f"{tweet.get('bookmarks', 0):,} bookmarks",
        f"{tweet.get('views', 0):,} views",
    ]
    footer_lines = [
        "---",
        "",
        "**Tweet stats at time of save:** " + " · ".join(stats_bits),
    ]

    doc = (
        "\n".join(header_lines)
        + "\n\n---\n\n"
        + body
        + "\n\n"
        + "\n".join(footer_lines)
        + "\n"
    )

    filename = f"{kebab(handle)}-{kebab(title)}-{date_str}.md"
    return filename, doc


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in {"-h", "--help"}:
        print("Usage: export_x_article.py <tweet-url> [output-dir]", file=sys.stderr)
        sys.exit(2)

    url = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()
    if not os.path.isdir(out_dir):
        sys.exit(f"Output directory does not exist: {out_dir}")

    handle, tweet_id = extract_handle_and_id(url)
    tweet = fetch_tweet(handle, tweet_id)
    source_url = tweet.get("url") or url
    filename, doc = render_markdown(tweet, source_url)
    path = os.path.join(out_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc)
    print(path)


if __name__ == "__main__":
    main()
