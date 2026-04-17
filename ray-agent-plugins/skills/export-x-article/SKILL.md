---
name: export-x-article
description: This skill should be used when the user provides an x.com or twitter.com status URL and wants to "save", "export", "archive", or "download" the tweet or article as a local markdown file. Also use when the user shares a long-form tweet (X article) and asks to preserve it, convert it to markdown, or keep a copy for later reading. Handles both short tweets and X long-form articles via the fxtwitter API, preserving author metadata, bold/italic formatting, inline links, mentions, media captions, and engagement stats.
argument-hint: <x.com-status-url> [output-dir]
allowed-tools: Bash(python3 *)
---

Export a single X (Twitter) status — short tweet or long-form article — to a markdown file.

## Usage

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/export-x-article/scripts/export_x_article.py" "$ARGUMENTS"
```

The script prints the output file path on success. If the user passes only a URL, the file is written to the current working directory. A second positional argument overrides the output directory.

## What the script produces

A markdown file with:

- **Header** — title (article title or fallback), Author name + handle link, role (from profile bio), Posted date (`YYYY-MM-DD`), Source URL, optional Location.
- **Body** — for X articles: every content block, preserving headings (detected from whole-block bold runs), inline bold/italic spans, @mentions as links, and media blocks rendered as `![caption](image-url)` followed by an italic `*Figure: caption.*` note. For short tweets: the raw tweet text.
- **Footer** — engagement stats (likes, reposts, quotes, replies, bookmarks, views) recorded at the moment of save.

Filename: `<handle-kebab>-<title-kebab>-<YYYY-MM-DD>.md`.

## When to invoke

Trigger on URLs matching `https://x.com/<handle>/status/<id>` or `https://twitter.com/<handle>/status/<id>` (with or without query params) paired with a save/export intent. The fxtwitter API returns the rendered article payload without requiring authentication, which is why the script works even though `x.com` itself paywalls scraping.

## Dependencies

- `python3` — stdlib only (no pip deps)
- `curl` — HTTP request to `api.fxtwitter.com`
