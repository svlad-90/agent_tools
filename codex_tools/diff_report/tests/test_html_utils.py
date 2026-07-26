from __future__ import annotations

import unittest

from codex_tools.diff_report.html_utils import (
    anchor,
    comment_anchor,
    esc,
    format_text,
    line_anchor,
)
from codex_tools.diff_report.models import VocabularyTerm


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

    def test_format_text_links_vocabulary_terms_outside_urls(self) -> None:
        html = format_text(
            "A vCPU reads https://example.test/vCPU and virtual CPU state.",
            (
                VocabularyTerm(
                    term="vCPU",
                    definition="Virtual CPU exposed to the guest.",
                    aliases=("virtual CPU",),
                ),
            ),
        )

        self.assertIn('class="vocabulary-ref"', html)
        self.assertIn("Virtual CPU exposed to the guest.", html)
        self.assertIn("virtual CPU</button>", html)
        self.assertIn("https://example.test/vCPU</a>", html)
        self.assertEqual(2, html.count('class="vocabulary-ref"'))


if __name__ == "__main__":
    unittest.main()
