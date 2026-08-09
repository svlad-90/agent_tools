from __future__ import annotations

import unittest

from agent_tools.tools.diff_report.html_utils import (
    anchor,
    comment_anchor,
    esc,
    format_text,
    line_anchor,
)
from agent_tools.tools.diff_report.models import VocabularyTerm


class HtmlUtilsTests(unittest.TestCase):
    def test_anchor_replaces_unsafe_characters(self) -> None:
        self.assertEqual("arch-arm64-core-xen-fdt.c", anchor("arch/arm64/core/xen/fdt.c"))
        self.assertEqual("-spaced-name-", anchor(" spaced name "))

    def test_line_and_comment_anchors_share_file_anchor(self) -> None:
        self.assertEqual("line-src-app.c-42", line_anchor("src/app.c", 42))
        self.assertEqual("comment-src-app.c-42", comment_anchor("src/app.c", 42))

    def test_esc_quotes_attribute_values(self) -> None:
        self.assertEqual("&lt;a href=&quot;x&quot;&gt;", esc('<a href="x">'))

    def test_format_text_linkifies_urls_and_keeps_trailing_punctuation(self) -> None:
        html = format_text("See https://example.test/path?q=1, then continue.")

        self.assertIn(
            '<a href="https://example.test/path?q=1" target="_blank" rel="noopener noreferrer">',
            html,
        )
        self.assertIn("https://example.test/path?q=1</a>, then continue.", html)

    def test_format_text_escapes_non_url_text(self) -> None:
        self.assertEqual("&lt;b&gt;safe&lt;/b&gt;", format_text("<b>safe</b>"))

    def test_format_text_highlights_vocabulary_terms_with_definitions(self) -> None:
        html = format_text(
            "The event channel targets a vCPU.",
            (
                VocabularyTerm(
                    term="event channel",
                    definition="Xen notification path.",
                    aliases=("event channels",),
                ),
                VocabularyTerm(term="vCPU", definition="Virtual CPU."),
            ),
        )

        self.assertIn('class="vocabulary-ref"', html)
        self.assertIn('data-term="event channel"', html)
        self.assertIn(">event channel</button>", html)
        self.assertIn("Xen notification path.", html)
        self.assertIn(">vCPU</button>", html)
        self.assertIn("Virtual CPU.", html)

    def test_format_text_does_not_highlight_inside_urls(self) -> None:
        html = format_text(
            "See https://example.test/vCPU and vCPU.",
            (VocabularyTerm(term="vCPU", definition="Virtual CPU."),),
        )

        self.assertIn('href="https://example.test/vCPU"', html)
        self.assertEqual(1, html.count('class="vocabulary-ref"'))

    def test_format_text_highlights_each_vocabulary_term_once_per_text_block(self) -> None:
        html = format_text(
            "A vCPU uses an event channel. The event channel targets the same virtual CPU.",
            (
                VocabularyTerm(term="event channel", definition="Xen notification path."),
                VocabularyTerm(term="vCPU", definition="Virtual CPU.", aliases=("virtual CPU",)),
            ),
        )

        self.assertEqual(2, html.count('class="vocabulary-ref"'))
        self.assertEqual(1, html.count('data-term="event channel"'))
        self.assertEqual(1, html.count('data-term="vCPU"'))
        self.assertIn("The event channel targets the same virtual CPU.", html)


if __name__ == "__main__":
    unittest.main()
