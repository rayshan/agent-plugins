"""Tests for export_x_article.

Focus on pure rendering and parsing logic. The network layer
(`fetch_tweet`) is a thin curl wrapper and is not exercised here; all
tests feed fixtures directly into the render functions so they stay
offline and fast.
"""

from __future__ import annotations

import pytest

from export_x_article import (
    apply_inline,
    extract_handle_and_id,
    is_heading_block,
    kebab,
    render_article,
    render_markdown,
)


class TestExtractHandleAndId:
    def test_x_com_url(self):
        assert extract_handle_and_id("https://x.com/jack/status/12345") == (
            "jack",
            "12345",
        )

    def test_twitter_com_url(self):
        assert extract_handle_and_id("https://twitter.com/jack/status/12345") == (
            "jack",
            "12345",
        )

    def test_url_with_query_string(self):
        assert extract_handle_and_id("https://x.com/jack/status/12345?s=46&t=abc") == (
            "jack",
            "12345",
        )

    def test_url_with_fragment(self):
        assert extract_handle_and_id("https://x.com/jack/status/12345#xyz") == (
            "jack",
            "12345",
        )

    def test_rejects_non_status_url(self):
        with pytest.raises(SystemExit):
            extract_handle_and_id("https://x.com/jack")

    def test_rejects_other_host(self):
        with pytest.raises(SystemExit):
            extract_handle_and_id("https://example.com/jack/status/12345")


class TestKebab:
    def test_lowercases_and_hyphenates(self):
        assert kebab("Services: The New Software") == "services-the-new-software"

    def test_collapses_runs_of_separators(self):
        assert kebab("foo   bar__baz") == "foo-bar-baz"

    def test_strips_leading_and_trailing_hyphens(self):
        assert kebab("---hello---") == "hello"

    def test_truncates_and_strips_trailing_hyphen_after_cut(self):
        # 25-char limit lands mid-separator; resulting slug must not end in '-'
        result = kebab("abcdefghijklmnopqrstuvwxy zzzz", max_len=25)
        assert not result.endswith("-")
        assert len(result) <= 25

    def test_empty_input_returns_fallback(self):
        assert kebab("!!!") == "untitled"


class TestApplyInline:
    def test_no_ranges_returns_text_unchanged(self):
        assert apply_inline("hello world", [], None) == "hello world"

    def test_bold_span(self):
        # "hello world" — bold on "world" (offset 6, length 5)
        ranges = [{"style": "Bold", "offset": 6, "length": 5}]
        assert apply_inline("hello world", ranges, None) == "hello **world**"

    def test_italic_span(self):
        ranges = [{"style": "Italic", "offset": 0, "length": 5}]
        assert apply_inline("hello world", ranges, None) == "*hello* world"

    def test_trims_trailing_whitespace_from_bold(self):
        """Bold ranges from the X API sometimes include trailing padding,
        which breaks markdown emphasis. The wrapper must sit flush against
        non-whitespace so `**word**` renders, not `**word **`."""
        text = "Legal (20B). Contract drafting."
        ranges = [{"style": "Bold", "offset": 0, "length": 13}]  # "Legal (20B). "
        assert apply_inline(text, ranges, None) == "**Legal (20B).** Contract drafting."

    def test_trims_leading_whitespace(self):
        text = " leading space"
        ranges = [{"style": "Bold", "offset": 0, "length": 8}]  # " leading"
        assert apply_inline(text, ranges, None) == " **leading** space"

    def test_whitespace_only_range_skipped(self):
        ranges = [{"style": "Bold", "offset": 5, "length": 1}]  # just the space
        assert apply_inline("hello world", ranges, None) == "hello world"

    def test_two_italic_ranges_preserve_offsets(self):
        # Annotations apply right-to-left so earlier offsets stay valid.
        text = "Writing code is mostly intelligence. Knowing what to build next is judgement."
        ranges = [
            {"style": "Italic", "offset": 23, "length": 12},
            {"style": "Italic", "offset": 67, "length": 9},
        ]
        out = apply_inline(text, ranges, None)
        assert "*intelligence*" in out
        assert "*judgement*" in out
        assert out.startswith("Writing code is mostly *intelligence*.")

    def test_mention_becomes_link(self):
        text = "ping @julienbek here"
        data = {"mentions": [{"fromIndex": 5, "toIndex": 15, "text": "julienbek"}]}
        out = apply_inline(text, [], data)
        assert out == "ping [@julienbek](https://x.com/julienbek) here"


class TestIsHeadingBlock:
    def test_whole_line_bold_is_heading(self):
        block = {
            "text": "Intelligence vs Judgement",
            "inlineStyleRanges": [{"style": "Bold", "offset": 0, "length": 25}],
        }
        assert is_heading_block(block)

    def test_partial_bold_is_not_heading(self):
        block = {
            "text": "Insurance brokerage ($140-200B). The largest dollar market.",
            "inlineStyleRanges": [{"style": "Bold", "offset": 0, "length": 33}],
        }
        assert not is_heading_block(block)

    def test_italic_whole_line_is_not_heading(self):
        block = {
            "text": "Aside",
            "inlineStyleRanges": [{"style": "Italic", "offset": 0, "length": 5}],
        }
        assert not is_heading_block(block)

    def test_multiple_style_ranges_disqualify(self):
        block = {
            "text": "mixed formatting",
            "inlineStyleRanges": [
                {"style": "Bold", "offset": 0, "length": 16},
                {"style": "Italic", "offset": 6, "length": 10},
            ],
        }
        assert not is_heading_block(block)

    def test_empty_text_is_not_heading(self):
        assert not is_heading_block({"text": "", "inlineStyleRanges": []})


def _text_block(text, styles=None, data=None):
    return {
        "text": text,
        "type": "unstyled",
        "inlineStyleRanges": styles or [],
        "entityRanges": [],
        "data": data or {},
    }


def _atomic_block(key):
    return {
        "text": " ",
        "type": "atomic",
        "entityRanges": [{"key": key, "length": 1, "offset": 0}],
        "inlineStyleRanges": [],
        "data": {},
    }


class TestRenderArticle:
    def test_renders_heading_and_paragraph(self):
        article = {
            "content": {
                "blocks": [
                    _text_block(
                        "Section",
                        [{"style": "Bold", "offset": 0, "length": 7}],
                    ),
                    _text_block("Body text."),
                ],
                "entityMap": [],
            },
            "media_entities": [],
        }
        assert render_article(article) == "## Section\n\nBody text."

    def test_renders_media_block_with_image_and_caption(self):
        article = {
            "content": {
                "blocks": [_atomic_block(0)],
                "entityMap": [
                    {
                        "key": "0",
                        "value": {
                            "data": {
                                "caption": "Source: Anthropic",
                                "mediaItems": [{"mediaId": "m1"}],
                            }
                        },
                    }
                ],
            },
            "media_entities": [
                {
                    "media_id": "m1",
                    "media_info": {"original_img_url": "https://example.com/img.png"},
                }
            ],
        }
        out = render_article(article)
        assert "![Source: Anthropic](https://example.com/img.png)" in out
        assert "*Figure: Source: Anthropic.*" in out

    def test_skips_blank_blocks(self):
        article = {
            "content": {
                "blocks": [_text_block(""), _text_block("Real text")],
                "entityMap": [],
            },
            "media_entities": [],
        }
        assert render_article(article) == "Real text"


class TestRenderMarkdown:
    @pytest.fixture
    def base_tweet(self):
        return {
            "id": "999",
            "url": "https://x.com/alice/status/999",
            "created_at": "Thu Mar 05 22:08:39 +0000 2026",
            "author": {
                "name": "Alice Example",
                "screen_name": "alice",
                "url": "https://x.com/alice",
                "description": "Writer",
                "location": "Berlin",
            },
            "likes": 10,
            "retweets": 2,
            "quotes": 1,
            "replies": 3,
            "bookmarks": 4,
            "views": 500,
        }

    def test_short_tweet_uses_text_as_title(self, base_tweet):
        base_tweet["text"] = "A short thought worth saving."
        filename, doc = render_markdown(base_tweet, base_tweet["url"])
        assert filename == "alice-a-short-thought-worth-saving-2026-03-05.md"
        assert doc.startswith("# A short thought worth saving.\n")
        assert "A short thought worth saving." in doc

    def test_article_title_takes_precedence(self, base_tweet):
        base_tweet["text"] = ""
        base_tweet["article"] = {
            "title": "Services: The New Software",
            "content": {"blocks": [_text_block("Body.")], "entityMap": []},
            "media_entities": [],
        }
        filename, doc = render_markdown(base_tweet, base_tweet["url"])
        assert filename == "alice-services-the-new-software-2026-03-05.md"
        assert "# Services: The New Software" in doc
        assert "Body." in doc

    def test_header_fields_present(self, base_tweet):
        base_tweet["text"] = "hi"
        _, doc = render_markdown(base_tweet, base_tweet["url"])
        assert (
            "**Author:** Alice Example ([@alice](https://x.com/alice)), Writer" in doc
        )
        assert "**Location:** Berlin" in doc
        assert "**Posted:** 2026-03-05" in doc
        assert "**Source:** <https://x.com/alice/status/999>" in doc

    def test_footer_includes_all_stats(self, base_tweet):
        base_tweet["text"] = "hi"
        _, doc = render_markdown(base_tweet, base_tweet["url"])
        assert "10 likes" in doc
        assert "2 reposts" in doc
        assert "1 quotes" in doc
        assert "500 views" in doc

    def test_role_omitted_when_blank(self, base_tweet):
        base_tweet["text"] = "hi"
        base_tweet["author"]["description"] = ""
        _, doc = render_markdown(base_tweet, base_tweet["url"])
        assert "**Author:** Alice Example ([@alice](https://x.com/alice))\n" in doc

    def test_location_omitted_when_absent(self, base_tweet):
        base_tweet["text"] = "hi"
        base_tweet["author"].pop("location")
        _, doc = render_markdown(base_tweet, base_tweet["url"])
        assert "**Location:**" not in doc
