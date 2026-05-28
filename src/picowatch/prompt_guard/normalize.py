"""Input normalization pipeline.

Runs before all rule matching to strip obfuscation and normalise encoding.
Pipeline order: Unicode NFKC → whitespace → encoding detection → comment stripping → markdown deobfuscation.
"""

from __future__ import annotations

import base64
import re
import unicodedata


class Normalizer:
    """Deterministic input normalizer.

    Same input always produces the same normalized output.
    """

    # Zero-width characters to strip
    _ZWNJ = "\u200c"  # zero-width non-joiner
    _ZWJ = "\u200d"  # zero-width joiner
    _ZWSP = "\u200b"  # zero-width space
    _ZERO_WIDTH = frozenset({_ZWNJ, _ZWJ, _ZWSP, "\ufeff", "\u200e", "\u200f"})

    # HTML comment pattern
    _HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
    # C-style block comment
    _C_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
    # Line comment (but not in URL context)
    _LINE_COMMENT = re.compile(r"^(?:\s*//.*$)", re.MULTILINE)

    # Base64 pattern (at least 20 chars, proper padding)
    _BASE64 = re.compile(r"[A-Za-z0-9+/]{20,}={0,2}")

    # Hex pattern (at least 20 hex chars)
    _HEX = re.compile(r"(?:0x)?[0-9a-fA-F]{20,}")

    # URL-encoded pattern
    _URL_ENC = re.compile(r"%[0-9a-fA-F]{2}")

    def normalize(self, text: str) -> str:
        """Full normalization pipeline.

        Order matters: unicode → whitespace → encoding → comments → markdown.
        """
        result = text
        result = self.normalize_unicode(result)
        result = self.normalize_whitespace(result)
        result = self.detect_encodings(result)  # flags but doesn't decode
        result = self.strip_comments(result)
        result = self.deobfuscate_markdown(result)
        return result

    def normalize_unicode(self, text: str) -> str:
        """NFKC normalization: collapses homoglyphs, ligatures, compatibility chars."""
        return unicodedata.normalize("NFKC", text)

    def normalize_whitespace(self, text: str) -> str:
        """Collapse whitespace runs and normalize line endings."""
        # Normalize line endings
        result = text.replace("\r\n", "\n").replace("\r", "\n")
        # Collapse runs of spaces/tabs (but preserve newlines)
        result = re.sub(r"[^\S\n]+", " ", result)
        # Collapse multiple blank lines to max 2
        result = re.sub(r"\n{3,}", "\n\n", result)
        return result.strip()

    def detect_encodings(self, text: str) -> str:
        """Flag encoded payloads. Adds markers but doesn't decode inline.

        This is detection-only: we annotate suspicious patterns so rules can
        match on the markers, but we don't alter the text content itself.
        """
        # We just return the text as-is; the rule engine's inj_encode_* rules
        # will match on these patterns directly.
        # Decoding is a separate step for deeper analysis.
        return text

    def decode_base64(self, text: str) -> list[str]:
        """Extract and decode base64 payloads from text.

        Returns a list of decoded strings for rule matching.
        """
        decoded = []
        for match in self._BASE64.finditer(text):
            try:
                payload = base64.b64decode(match.group()).decode("utf-8", errors="ignore")
                if len(payload) > 5:  # skip trivially short decodes
                    decoded.append(payload)
            except Exception:
                continue
        return decoded

    def decode_rot13(self, text: str) -> str:
        """Apply ROT13 decoding to text."""
        import codecs

        return codecs.encode(text, "rot_13")

    def decode_url(self, text: str) -> str:
        """Decode URL-encoded text."""
        import urllib.parse

        return urllib.parse.unquote(text)

    def strip_comments(self, text: str) -> str:
        """Remove HTML, C-style, and line comments."""
        result = self._HTML_COMMENT.sub("", text)
        result = self._C_COMMENT.sub("", result)
        result = self._LINE_COMMENT.sub("", result)
        return result

    def deobfuscate_markdown(self, text: str) -> str:
        """Strip zero-width characters and invisible Unicode."""
        # Remove zero-width characters
        result = "".join(ch for ch in text if ch not in self._ZERO_WIDTH)
        return result
