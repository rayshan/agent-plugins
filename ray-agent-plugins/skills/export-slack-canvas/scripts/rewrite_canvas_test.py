"""Tests for rewrite_canvas.py.

Run with: uvx pytest scripts/rewrite_canvas_test.py -v
"""

from __future__ import annotations

from rewrite_canvas import (
    build_index,
    parse_detailed_thread,
    parse_url,
    rewrite,
)

# A realistic slice of the format returned by slack_read_thread in detailed mode.
SAMPLE_THREAD = """=== THREAD PARENT MESSAGE ===
From: Mica Cole (U9SDL9Z4M)
Time: 2025-08-07 12:28:51 PDT
Message TS: 1754594931.762139
*Interest History Problems*

Summary: Accept, Cancel, conversion, exercise do not impact inv. capital.
Reactions: thankyou (2)

=== THREAD REPLIES (2 total) ===

--- Reply 1 of 2 ---
From: Will Chan (UFMK62Y0N)
Time: 2025-08-07 12:41:08 PDT
Message TS: 1754595668.906619
Maybe we covered this and I didn't follow during our discussion.

--- Reply 2 of 2 ---
From: Jiaru Cao (U03DEC6FEM7)
Time: 2025-08-11 12:35:48 PDT
Message TS: 1754940948.911339
*Summarizing decision from huddle:*
We will show IC balance column for only IC-based interests.
Reactions: thankyou (2), log_pd (1)
Files: Screenshot.png
"""


def test_parse_detailed_thread_extracts_parent_and_replies():
    msgs = parse_detailed_thread(SAMPLE_THREAD)
    assert [m.ts for m in msgs] == [
        "1754594931.762139",
        "1754595668.906619",
        "1754940948.911339",
    ]


def test_parse_detailed_thread_strips_user_id_suffix_from_author():
    msgs = parse_detailed_thread(SAMPLE_THREAD)
    assert msgs[0].author == "Mica Cole"
    assert msgs[2].author == "Jiaru Cao"


def test_parse_detailed_thread_drops_reactions_and_files_lines():
    msgs = parse_detailed_thread(SAMPLE_THREAD)
    # The Reactions / Files trailers should not leak into the message body;
    # they're metadata, not content the reader wants inlined.
    last = msgs[2]
    assert "Reactions:" not in last.text
    assert "Files:" not in last.text
    assert "Summarizing decision from huddle" in last.text


def test_build_index_maps_by_channel_and_message_ts():
    index = build_index([{"channel_id": "C08DP1PL53R", "messages": SAMPLE_THREAD}])
    msg = index[("C08DP1PL53R", "1754940948.911339")]
    assert "Summarizing decision from huddle" in msg.text


def test_parse_url_with_thread_ts_separates_thread_and_message_ts():
    url = (
        "https://grid-carta.enterprise.slack.com/archives/C08DP1PL53R"
        "/p1754940948911339?thread_ts=1754594931.762139&cid=C08DP1PL53R"
    )
    parsed = parse_url(url)
    assert parsed is not None
    cid, thread_ts, message_ts = parsed
    assert cid == "C08DP1PL53R"
    assert thread_ts == "1754594931.762139"
    assert message_ts == "1754940948.911339"


def test_parse_url_without_thread_ts_falls_back_to_message_ts():
    url = "https://eshares.slack.com/archives/C08DP1PL53R/p1754594931762139"
    parsed = parse_url(url)
    assert parsed is not None
    _, thread_ts, message_ts = parsed
    assert thread_ts == message_ts == "1754594931.762139"


def test_rewrite_replaces_bookmark_with_referenced_message():
    canvas = (
        "## Decision\n\n"
        "[](https://grid-carta.enterprise.slack.com/archives/C08DP1PL53R"
        "/p1754940948911339?thread_ts=1754594931.762139)\n"
    )
    index = build_index([{"channel_id": "C08DP1PL53R", "messages": SAMPLE_THREAD}])
    out = rewrite(canvas, index, uniquify_headings=False)
    assert "Summarizing decision from huddle" in out
    # The Will Chan reply (a different ts in the same thread) must NOT appear —
    # this is the whole point: expand only the referenced message.
    assert "Maybe we covered this" not in out


def test_rewrite_collapses_bookmark_and_original_message_duplicate():
    # Canvas-style double reference: icon bookmark + "Original message:" line.
    # A second expansion in the same heading section would just repeat the body.
    canvas = (
        "## Decision\n\n"
        "[](https://grid-carta.enterprise.slack.com/archives/C08DP1PL53R"
        "/p1754940948911339?thread_ts=1754594931.762139)\n\n"
        "**Original message:** https://eshares.slack.com/archives/C08DP1PL53R"
        "/p1754940948911339?thread_ts=1754594931.762139\n"
    )
    index = build_index([{"channel_id": "C08DP1PL53R", "messages": SAMPLE_THREAD}])
    out = rewrite(canvas, index, uniquify_headings=False)
    assert out.count("Summarizing decision from huddle") == 1


def test_rewrite_expands_same_message_again_under_a_new_heading():
    # The dedup is scoped by heading section — a new heading resets the guard
    # so the reader still sees the expansion when they scan that section alone.
    canvas = (
        "## Decision A\n\n"
        "[](https://grid-carta.enterprise.slack.com/archives/C08DP1PL53R"
        "/p1754940948911339?thread_ts=1754594931.762139)\n\n"
        "## Decision B\n\n"
        "[](https://grid-carta.enterprise.slack.com/archives/C08DP1PL53R"
        "/p1754940948911339?thread_ts=1754594931.762139)\n"
    )
    index = build_index([{"channel_id": "C08DP1PL53R", "messages": SAMPLE_THREAD}])
    out = rewrite(canvas, index, uniquify_headings=False)
    assert out.count("Summarizing decision from huddle") == 2


def test_rewrite_leaves_line_alone_when_message_not_in_index():
    # Graceful fallback: if the referenced message isn't in the fetched bundle
    # (e.g. the Canvas links to a private channel we couldn't read), keep the
    # original line so the user still has the link to click through.
    canvas = (
        "[](https://grid-carta.enterprise.slack.com/archives/CUNKNOWN"
        "/p1111111111111111?thread_ts=1.2)\n"
    )
    out = rewrite(canvas, build_index([]), uniquify_headings=False)
    assert "CUNKNOWN" in out


def test_rewrite_uniquify_headings_disambiguates_repeats():
    canvas = "## Decision\n\n## Decision\n\n## Decision\n"
    out = rewrite(canvas, build_index([]), uniquify_headings=True)
    assert "## Decision\n" in out
    assert "## Decision (2)" in out
    assert "## Decision (3)" in out
