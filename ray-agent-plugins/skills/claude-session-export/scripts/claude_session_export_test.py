"""Tests for claude_session_export.py."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from claude_session_export import (
    consolidate_mcp_lines,
    encode_project_path,
    export_session,
    extract_assistant_text,
    extract_user_text,
    format_mcp_notes,
    format_timestamp,
    parse_mcp_tool,
    resolve_session,
    slugify,
    strip_system_tags,
)


# --- encode_project_path ---


def test_encode_replaces_non_alnum():
    with patch.object(Path, "resolve", return_value=Path("/Users/me/project")):
        assert encode_project_path("/Users/me/project") == "-Users-me-project"


def test_encode_preserves_alnum():
    with patch.object(Path, "resolve", return_value=Path("/abc123")):
        assert encode_project_path("/abc123") == "-abc123"


# --- slugify ---


def test_slugify_basic():
    assert slugify("My Test Session") == "my-test-session"


def test_slugify_special_chars():
    assert slugify("link-claude-project skill dev") == "link-claude-project-skill-dev"


def test_slugify_empty():
    assert slugify("!!!") == "untitled"


# --- resolve_session ---


@pytest.fixture()
def sessions_dir(tmp_path):
    """Create a fake project dir with multiple session transcripts."""
    encoded = "-Users-test-my-project"
    proj_dir = tmp_path / "home" / ".claude" / "projects" / encoded
    proj_dir.mkdir(parents=True)

    # Session 1: has both title and agent name
    s1 = proj_dir / "aaaa-1111-bbbb-2222-cccc33334444.jsonl"
    s1.write_text(
        json.dumps({"type": "agent-name", "agentName": "mcp app dev"})
        + "\n"
        + json.dumps(
            {"type": "custom-title", "customTitle": "mcp app - cap table chart"}
        )
        + "\n"
    )

    # Session 2: agent name only, shares "mcp" keyword with session 1
    s2 = proj_dir / "dddd-5555-eeee-6666-ffff77778888.jsonl"
    s2.write_text(
        json.dumps({"type": "agent-name", "agentName": "mcp env switcher script"})
        + "\n"
    )

    return tmp_path


def test_resolve_uuid_passthrough():
    """UUID identifiers pass through without scanning files."""
    uuid = "aaaa1111-bb22-cc33-dd44-eeeeffffaaaa"
    assert resolve_session("/any/path", uuid) == uuid


def test_resolve_name_match(sessions_dir):
    with patch("claude_session_export.Path.home", return_value=sessions_dir / "home"):
        result = resolve_session("/Users/test/my-project", "cap table")
    assert result == "aaaa-1111-bbbb-2222-cccc33334444"


def test_resolve_name_case_insensitive(sessions_dir):
    with patch("claude_session_export.Path.home", return_value=sessions_dir / "home"):
        result = resolve_session("/Users/test/my-project", "ENV SWITCHER SCRIPT")
    assert result == "dddd-5555-eeee-6666-ffff77778888"


def test_resolve_name_no_match(sessions_dir):
    with patch("claude_session_export.Path.home", return_value=sessions_dir / "home"):
        with pytest.raises(FileNotFoundError, match="No session matching"):
            resolve_session("/Users/test/my-project", "nonexistent")


def test_resolve_name_multiple_matches(sessions_dir):
    with patch("claude_session_export.Path.home", return_value=sessions_dir / "home"):
        with pytest.raises(ValueError, match="Multiple sessions match"):
            resolve_session("/Users/test/my-project", "mcp")


# --- strip_system_tags ---


def test_strip_removes_system_reminder():
    text = "<system-reminder>context here</system-reminder>\nHello"
    assert strip_system_tags(text) == "Hello"


def test_strip_removes_local_command_tags():
    text = (
        "<local-command-caveat>caveat</local-command-caveat>\n"
        "<command-name>/clear</command-name>\n"
        "<command-message>clear</command-message>\n"
        "<command-args></command-args>\n"
        "<local-command-stdout></local-command-stdout>\n"
        "Write a script"
    )
    assert strip_system_tags(text) == "Write a script"


def test_strip_removes_deferred_tools():
    text = "<available-deferred-tools>\ntool1\ntool2\n</available-deferred-tools>\nHi"
    assert strip_system_tags(text) == "Hi"


def test_strip_returns_none_when_empty():
    text = "<system-reminder>only system content</system-reminder>"
    assert strip_system_tags(text) is None


def test_strip_preserves_clean_text():
    assert strip_system_tags("Just a normal message") == "Just a normal message"


# --- parse_mcp_tool ---


def test_parse_mcp_basic():
    assert parse_mcp_tool("mcp__github__pull_request_read") == (
        "github",
        "pull_request_read",
    )


def test_parse_mcp_plugin_prefix():
    assert parse_mcp_tool("mcp__plugin_context7_context7__resolve-library-id") == (
        "context7",
        "resolve-library-id",
    )


def test_parse_mcp_claude_ai_prefix():
    assert parse_mcp_tool("mcp__claude_ai_Gmail__gmail_create_draft") == (
        "Gmail",
        "gmail_create_draft",
    )


def test_parse_mcp_not_mcp():
    assert parse_mcp_tool("Bash") is None
    assert parse_mcp_tool("Read") is None


def test_parse_mcp_too_few_parts():
    assert parse_mcp_tool("mcp__github") is None


# --- format_mcp_notes ---


def test_format_mcp_notes_groups_by_server():
    content = [
        {"type": "tool_use", "name": "mcp__github__pull_request_read", "id": "1"},
        {"type": "tool_use", "name": "mcp__github__pull_request_read", "id": "2"},
        {"type": "tool_use", "name": "mcp__github__pull_request_read", "id": "3"},
        {
            "type": "tool_use",
            "name": "mcp__plugin_context7_context7__resolve-library-id",
            "id": "4",
        },
        {
            "type": "tool_use",
            "name": "mcp__plugin_context7_context7__query-docs",
            "id": "5",
        },
    ]
    result = format_mcp_notes(content)
    assert "`github` \u2192 `pull_request_read` (\u00d73)" in result
    assert "`context7` \u2192 `resolve-library-id`, `query-docs`" in result


def test_format_mcp_notes_no_mcp():
    content = [
        {"type": "tool_use", "name": "Bash", "id": "1"},
        {"type": "text", "text": "hello"},
    ]
    assert format_mcp_notes(content) is None


# --- consolidate_mcp_lines ---


def test_consolidate_same_server():
    text = (
        "Some text.\n\n"
        "> Used MCP \U0001f50c `context7` \u2192 `resolve-library-id`\n\n"
        "> Used MCP \U0001f50c `context7` \u2192 `query-docs`"
    )
    result = consolidate_mcp_lines(text)
    assert "Some text." in result
    assert result.count("> Used MCP") == 1
    assert "`resolve-library-id`, `query-docs`" in result


def test_consolidate_different_servers():
    text = (
        "> Used MCP \U0001f50c `github` \u2192 `pull_request_read`\n\n"
        "> Used MCP \U0001f50c `context7` \u2192 `query-docs`"
    )
    result = consolidate_mcp_lines(text)
    assert result.count("> Used MCP") == 2


def test_consolidate_same_tool_counted():
    text = (
        "> Used MCP \U0001f50c `github` \u2192 `pull_request_read`\n\n"
        "> Used MCP \U0001f50c `github` \u2192 `pull_request_read`\n\n"
        "> Used MCP \U0001f50c `github` \u2192 `pull_request_read`"
    )
    result = consolidate_mcp_lines(text)
    assert result.count("> Used MCP") == 1
    assert "`pull_request_read` (\u00d73)" in result


def test_consolidate_no_mcp():
    text = "Just plain text."
    assert consolidate_mcp_lines(text) == text


# --- extract_user_text ---


def test_user_text_string_content():
    msg = {"message": {"content": "Hello Claude"}}
    assert extract_user_text(msg) == "Hello Claude"


def test_user_text_skips_tool_result():
    msg = {
        "toolUseResult": {"type": "update", "filePath": "foo.py"},
        "message": {
            "content": [
                {"type": "tool_result", "tool_use_id": "abc", "content": []},
            ]
        },
    }
    assert extract_user_text(msg) is None


def test_user_text_skips_skill_message():
    msg = {
        "sourceToolUseID": "toolu_abc123",
        "isMeta": True,
        "message": {
            "content": [
                {
                    "type": "text",
                    "text": "Base directory for this skill: /path/to/skill",
                },
            ]
        },
    }
    assert extract_user_text(msg) is None


def test_user_text_array_with_text_blocks():
    msg = {
        "message": {
            "content": [
                {"type": "text", "text": "First part"},
                {"type": "text", "text": "Second part"},
            ]
        }
    }
    assert extract_user_text(msg) == "First part\n\nSecond part"


def test_user_text_array_only_tool_result():
    msg = {
        "message": {
            "content": [
                {"type": "tool_result", "tool_use_id": "abc", "content": []},
            ]
        }
    }
    assert extract_user_text(msg) is None


def test_user_text_strips_system_tags():
    msg = {
        "message": {"content": "<system-reminder>ctx</system-reminder>\nDo something"}
    }
    assert extract_user_text(msg) == "Do something"


def test_user_text_missing_message():
    assert extract_user_text({}) is None


# --- extract_assistant_text ---


def test_assistant_text_only():
    msg = {
        "message": {
            "content": [
                {"type": "text", "text": "Here is my answer."},
            ]
        }
    }
    assert extract_assistant_text(msg) == "Here is my answer."


def test_assistant_skips_thinking_and_tool_use():
    msg = {
        "message": {
            "content": [
                {"type": "thinking", "thinking": "hmm...", "signature": "sig"},
                {"type": "text", "text": "The answer is 42."},
                {"type": "tool_use", "id": "t1", "name": "Read", "input": {}},
            ]
        }
    }
    assert extract_assistant_text(msg) == "The answer is 42."


def test_assistant_no_text_blocks():
    msg = {
        "message": {
            "content": [
                {"type": "tool_use", "id": "t1", "name": "Bash", "input": {}},
            ]
        }
    }
    assert extract_assistant_text(msg) is None


def test_assistant_multiple_text_blocks():
    msg = {
        "message": {
            "content": [
                {"type": "text", "text": "Part one."},
                {"type": "tool_use", "id": "t1", "name": "Read", "input": {}},
                {"type": "text", "text": "Part two."},
            ]
        }
    }
    assert extract_assistant_text(msg) == "Part one.\n\nPart two."


def test_assistant_text_with_mcp():
    msg = {
        "message": {
            "content": [
                {"type": "text", "text": "Let me check the PR."},
                {
                    "type": "tool_use",
                    "id": "t1",
                    "name": "mcp__github__pull_request_read",
                    "input": {},
                },
            ]
        }
    }
    result = extract_assistant_text(msg)
    assert result.startswith("Let me check the PR.")
    assert "> Used MCP" in result
    assert "`github`" in result


def test_assistant_mcp_only():
    msg = {
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "id": "t1",
                    "name": "mcp__github__pull_request_read",
                    "input": {},
                },
            ]
        }
    }
    result = extract_assistant_text(msg)
    assert result is not None
    assert "> Used MCP" in result


# --- format_timestamp ---


def test_format_iso_timestamp():
    assert format_timestamp("2026-03-30T14:30:00.000Z") == "2026-03-30 14:30:00"


def test_format_none():
    assert format_timestamp(None) == ""


def test_format_empty():
    assert format_timestamp("") == ""


def test_format_invalid():
    assert format_timestamp("not-a-date") == ""


# --- export_session (integration) ---


@pytest.fixture()
def transcript_dir(tmp_path):
    """Create a fake Claude projects directory with a transcript."""
    project_path = "/Users/test/my-project"
    encoded = "-Users-test-my-project"
    proj_dir = tmp_path / encoded
    proj_dir.mkdir()

    session_id = "abc-123-def"
    messages = [
        {
            "type": "agent-name",
            "agentName": "TestAgent",
            "sessionId": session_id,
            "timestamp": "2026-03-30T10:00:00Z",
        },
        {
            "type": "custom-title",
            "customTitle": "My Test Session",
            "sessionId": session_id,
            "timestamp": "2026-03-30T10:00:01Z",
        },
        {
            "type": "user",
            "message": {"role": "user", "content": "Hello!"},
            "timestamp": "2026-03-30T10:00:02Z",
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "thinking", "thinking": "reasoning...", "signature": "s"},
                    {"type": "text", "text": "Hi there!"},
                ],
            },
            "timestamp": "2026-03-30T10:00:03Z",
        },
        {
            "type": "user",
            "toolUseResult": {"type": "update"},
            "message": {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": "t1", "content": []},
                ],
            },
            "timestamp": "2026-03-30T10:00:04Z",
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "id": "t2", "name": "Bash", "input": {}},
                ],
            },
            "timestamp": "2026-03-30T10:00:05Z",
        },
        {
            "type": "progress",
            "data": {"type": "hook_progress"},
            "timestamp": "2026-03-30T10:00:06Z",
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Let me load that skill."},
                    {
                        "type": "tool_use",
                        "id": "skill_1",
                        "name": "Skill",
                        "input": {"skill": "gws-docs", "args": "http://example.com"},
                    },
                ],
            },
            "timestamp": "2026-03-30T10:00:06.5Z",
        },
        {
            "type": "user",
            "sourceToolUseID": "skill_1",
            "isMeta": True,
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Base directory: /path/to/skill\n\n# Long skill content...",
                    },
                ],
            },
            "timestamp": "2026-03-30T10:00:06.6Z",
        },
        {
            "type": "user",
            "message": {"role": "user", "content": "Thanks!"},
            "timestamp": "2026-03-30T10:00:07Z",
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "You're welcome!"}],
            },
            "timestamp": "2026-03-30T10:00:08Z",
        },
    ]

    transcript = proj_dir / f"{session_id}.jsonl"
    transcript.write_text("\n".join(json.dumps(m) for m in messages) + "\n")

    return tmp_path, project_path, session_id


def test_export_filters_and_formats(transcript_dir):
    tmp_path, project_path, session_id = transcript_dir

    with patch("claude_session_export.Path.home", return_value=tmp_path / "home"):
        # Move transcript to match Path.home()/.claude/projects/...
        src = tmp_path / "-Users-test-my-project"
        dest = tmp_path / "home" / ".claude" / "projects" / "-Users-test-my-project"
        dest.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dest)

        md, count, name, last_ts = export_session(project_path, session_id)

    # 6 entries: 2 user + 3 assistant + 1 skill note (tool-only ones filtered)
    assert count == 6
    assert name == "TestAgent"
    assert last_ts == "2026-03-30T10:00:08Z"

    assert "# My Test Session" in md
    assert "**Agent:** TestAgent" in md
    assert "\U0001f464 User" in md
    assert "\U0001f916 Claude" in md
    assert "Hello!" in md
    assert "Hi there!" in md
    assert "Thanks!" in md
    assert "You're welcome!" in md

    # Skill: note present, content absent.
    assert "Loaded \u26a1\ufe0f Skill `gws-docs`" in md
    assert "Let me load that skill." in md
    assert "Base directory" not in md
    assert "Long skill content" not in md

    # Filtered out:
    assert "reasoning..." not in md
    assert "tool_use" not in md
    assert "hook_progress" not in md
    assert "tool_result" not in md


def test_export_not_found():
    with pytest.raises(FileNotFoundError, match="Transcript not found"):
        export_session("/nonexistent/path", "no-such-session")
