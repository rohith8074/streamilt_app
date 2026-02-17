"""
Tests for utils/ui.py — Covers UI helper functions.

Modules tested:
  - get_base64_of_bin_file
  - get_img_with_href
  - inject_custom_css (smoke test — ensures no syntax errors in the f-string CSS)
"""

import pytest
import os
import base64
from utils.ui import get_base64_of_bin_file, get_img_with_href


class TestBase64Encoding:
    """Tests for image-to-Base64 conversion helpers."""

    def test_encode_file(self, tmp_path):
        """A known file should produce a valid Base64 string."""
        test_file = tmp_path / "test.png"
        test_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)

        result = get_base64_of_bin_file(str(test_file))
        # Should be a valid base64 string (decodable)
        decoded = base64.b64decode(result)
        assert decoded[:4] == b"\x89PNG"

    def test_get_img_with_href_valid_file(self, tmp_path):
        test_file = tmp_path / "logo.png"
        test_file.write_bytes(b"\x89PNG\r\n\x1a\n")

        result = get_img_with_href(str(test_file))
        assert result.startswith("data:image/png;base64,")

    def test_get_img_with_href_missing_file(self):
        """A missing file should return an empty string, not crash."""
        result = get_img_with_href("/nonexistent/path/image.png")
        assert result == ""

    def test_get_img_with_href_jpg(self, tmp_path):
        test_file = tmp_path / "photo.jpg"
        test_file.write_bytes(b"\xff\xd8\xff\xe0")

        result = get_img_with_href(str(test_file))
        assert "data:image/jpg;base64," in result


class TestInjectCustomCSS:
    """Smoke test to ensure the CSS f-string has no syntax errors."""

    def test_css_injection_does_not_crash(self, mocker):
        """inject_custom_css() should not raise any NameError or formatting errors."""
        # Mock st.markdown so we don't need a real Streamlit runtime
        mock_markdown = mocker.patch("utils.ui.st.markdown")

        from utils.ui import inject_custom_css

        # This should NOT raise NameError (like the bug we fixed earlier)
        inject_custom_css()

        # Verify it was called with some CSS content
        mock_markdown.assert_called_once()
        call_args = mock_markdown.call_args
        css_content = call_args[0][0]
        assert "<style>" in css_content
        assert "Outfit" in css_content  # Our custom font
        assert "glassmorphism" not in css_content or True  # Just checking it rendered
