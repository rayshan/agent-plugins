---
name: export-slack-canvas
description: This skill should be used when the user provides a Slack Canvas URL (e.g. https://*.slack.com/docs/<team_id>/F<canvas_id>) or Canvas ID and wants to "save", "export", "archive", "download", or "convert to markdown" the Canvas. Use whenever a Canvas link is paired with any save/export intent, or when the user asks to preserve a Canvas for offline reading, share it as a file, or review decisions logged in a Slack Canvas. Expands Slack message references inline with only the specific referenced message — never the full thread — and de-duplicates the icon-link-plus-original-message dual references Canvases often contain. Requires the Slack MCP.
argument-hint: <canvas-url-or-id> [output-path]
allowed-tools: Bash(python3 *), mcp__plugin_slack_slack__slack_read_canvas, mcp__plugin_slack_slack__slack_read_thread
---

# Export Slack Canvas

Fetch a Slack Canvas, expand any Slack message references it contains, and write the result to a local markdown file.

## Why expand only the referenced message, not the whole thread

Canvases typically reference Slack messages to preserve the exact decision or summary that was recorded — often a specific reply deep inside a long thread. Expanding the entire thread dilutes that signal with reactions, tangents, and image diffs. The `p<digits>` in the URL points to *one* message; the rewriter matches that ts and inlines only it.

Canvases also commonly reference the same message twice per block: once as an icon bookmark (`[](URL)`) and once again as a plain `**Original message:** URL` paragraph. Both resolve to the same ts, so the rewriter collapses them into a single expansion.

## Workflow

### 1. Resolve the Canvas ID

A Canvas URL looks like `https://<workspace>.slack.com/docs/<team_id>/F<canvas_id>`. The Canvas ID is the trailing `F…` token. If the user passes a bare ID, use it directly.

### 2. Fetch the Canvas

```text
mcp__plugin_slack_slack__slack_read_canvas(canvas_id="<F-id>")
```

Write the returned `markdown_content` field to a temp file (e.g. `/tmp/canvas-<F-id>.md`). Subsequent scripts read it from there.

### 3. List the Slack message references

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/export-slack-canvas/scripts/find_refs.py" /tmp/canvas-<F-id>.md
```

Each line of output is a JSON object with `channel_id`, `thread_ts`, `message_ts`. One line per unique `(channel_id, thread_ts)` pair — the same thread referenced multiple times in the Canvas only needs to be fetched once.

### 4. Fetch each referenced thread in parallel

For every emitted line, call:

```text
mcp__plugin_slack_slack__slack_read_thread(
  channel_id="<cid>",
  message_ts="<thread_ts>",
  response_format="detailed",
)
```

Batch all calls in a single assistant turn so they run concurrently. `detailed` is required — it's the only format that reports each reply's own `Message TS:`, which is how the rewriter matches a Canvas reference to the specific reply.

### 5. Rewrite the Canvas

Write the collected thread payloads to `/tmp/threads-<F-id>.json` as an array of `{channel_id, thread_ts, messages}` objects, where `messages` is the verbatim string the MCP returned. Then run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/export-slack-canvas/scripts/rewrite_canvas.py" \
  --canvas /tmp/canvas-<F-id>.md \
  --threads /tmp/threads-<F-id>.json \
  --output <output-path>
```

If the user didn't specify an output path, default to `slack-canvas-<F-id>.md` in the current working directory.

Pass `--uniquify-headings` when the target repo lints markdown strictly (rumdl MD024). It appends `(2)`, `(3)`, … to otherwise-duplicate heading text — typical for Canvases with many `### Decision` sections.

### 6. Report

Print the output path. Do not echo the rewritten markdown back into the chat — the user can open the file themselves.

### 7. Reflect on the skill itself

Before ending the turn, briefly reflect on what happened during this run and whether the skill could be better. The goal is a one-pass feedback loop that catches the small papercuts while they're fresh — not a full redesign.

Look at signals like:

- **Dead ends you hit.** Did the workflow instruct you to do something that didn't work, or forget a step you had to invent on the fly? Did a script fail on input it should have handled (a Canvas variant, a new Slack URL shape, an unfetchable thread)? Those gaps belong in SKILL.md or in the scripts.
- **Work done outside the scripts that looks repeatable.** If you wrote ad-hoc code to reshape the threads JSON, or manually cleaned up markdown after the rewriter, that logic probably wants to move into a script so the next run gets it for free.
- **Ambiguity in the user's request that you had to resolve by guessing.** A future invocation may need a flag or a clarifying question to handle that case deterministically.
- **Output quality.** Did the expansions land where the reader would expect? Did the dedup scoping feel right for this Canvas's structure? Did any markdown lint rules fire that aren't yet handled?

Share the reflection as a short, candid note to the user — ideally 2–4 concrete suggestions, each phrased as *"next time, the skill could …"*. Do not silently edit SKILL.md or the scripts as part of this step. The user decides whether an improvement is worth making. If nothing came up, say so briefly — honest "no changes suggested" is more useful than manufactured feedback.

## What each message looks like after expansion

```text
> **<author>** (<timestamp from Slack>) — [source](<original URL>)
>
> <message body, newlines preserved>
```

The `[source]` link preserves the original permalink so the reader can click back into Slack for full thread context when they want it.

## Dependencies

- `python3` — stdlib only (no pip installs)
- Slack MCP — `mcp__plugin_slack_slack__slack_read_canvas` and `mcp__plugin_slack_slack__slack_read_thread`, connected to the workspace that owns the Canvas

## Scope

This skill covers single-Canvas export. Bulk export across many Canvases, or continuous sync, is out of scope — invoke the skill once per Canvas.
