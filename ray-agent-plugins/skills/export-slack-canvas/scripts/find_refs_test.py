"""Tests for find_refs.py.

Run with: uvx pytest scripts/find_refs_test.py -v
"""

from __future__ import annotations

from find_refs import extract_refs, pdigits_to_ts


def test_pdigits_conversion_standard_microsecond_format():
    # Slack timestamps are always "<seconds>.<6 digits of microseconds>".
    assert pdigits_to_ts("1754940948911339") == "1754940948.911339"


def test_pdigits_conversion_leaves_short_strings_alone():
    # Fallback path: we prefer to emit something parseable even for malformed
    # input rather than raising — callers can compare against the MCP response.
    assert pdigits_to_ts("12345") == "12345"


def test_extract_refs_prefers_thread_ts_when_present():
    md = (
        "[](https://grid-carta.enterprise.slack.com/archives/C08DP1PL53R"
        "/p1754940948911339?thread_ts=1754594931.762139&cid=C08DP1PL53R)"
    )
    refs = extract_refs(md)
    assert refs == [
        {
            "channel_id": "C08DP1PL53R",
            "thread_ts": "1754594931.762139",
            "message_ts": "1754940948.911339",
        }
    ]


def test_extract_refs_falls_back_to_message_ts_when_no_thread_ts():
    # A URL without `thread_ts` describes a top-level message; the thread
    # parent is the message itself.
    md = "https://eshares.slack.com/archives/C08DP1PL53R/p1753296148451119"
    refs = extract_refs(md)
    assert refs == [
        {
            "channel_id": "C08DP1PL53R",
            "thread_ts": "1753296148.451119",
            "message_ts": "1753296148.451119",
        }
    ]


def test_extract_refs_deduplicates_same_thread_mentioned_twice():
    # Canvases include an icon bookmark next to an "Original message:" line
    # both pointing at the same thread — the caller should only fetch once.
    md = """
[](https://grid-carta.enterprise.slack.com/archives/C08DP1PL53R/p1754940948911339?thread_ts=1754594931.762139&cid=C08DP1PL53R)

**Original message:**  https://eshares.slack.com/archives/C08DP1PL53R/p1754940948911339?thread_ts=1754594931.762139&cid=C08DP1PL53R
"""
    refs = extract_refs(md)
    assert len(refs) == 1
    assert refs[0]["thread_ts"] == "1754594931.762139"


def test_extract_refs_treats_different_threads_separately():
    # Two references to different threads must both appear in the output.
    md = """
https://grid-carta.enterprise.slack.com/archives/C08DP1PL53R/p1754940948911339?thread_ts=1754594931.762139
https://grid-carta.enterprise.slack.com/archives/C08DP1PL53R/p1753296148451119?thread_ts=1753296148.451119
"""
    refs = extract_refs(md)
    assert {r["thread_ts"] for r in refs} == {
        "1754594931.762139",
        "1753296148.451119",
    }


def test_extract_refs_ignores_non_slack_urls():
    md = (
        "[unrelated](https://example.com/archives/C12345/p1234567890)\n"
        "[slack](https://grid-carta.enterprise.slack.com/archives/"
        "C12345/p1754940948911339?thread_ts=1.2)"
    )
    refs = extract_refs(md)
    assert len(refs) == 1
    assert refs[0]["channel_id"] == "C12345"
