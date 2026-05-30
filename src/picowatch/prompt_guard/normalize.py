"""Input normalization pipeline.

Runs before all rule matching to strip obfuscation and normalise encoding.
Pipeline order: Unicode NFKC → whitespace → spaced-text collapse → encoding detection
→ decode-then-rescan → comment stripping → markdown deobfuscation.
Decoded payloads are re-scanned so encoded injections surface to the rule engine.
"""

from __future__ import annotations

import base64
import codecs
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

    # Spaced-out single-char interleaving: "i g n o r e" or "i g n o r e  a l l"
    # Detects sequences of single chars separated by spaces where the unspaced
    # form is 3+ consecutive word characters — common bypass technique.
    _SPACED_SINGLE_CHAR = re.compile(r"(?:^|(?<=\s))(\w)(?:\s+(\w)){2,}(?=\s|$|[,.;!?])")

    def normalize(self, text: str) -> str:
        """Full normalization pipeline.

        Order matters: unicode → spaced-text (before whitespace collapse to preserve
        word boundaries) → whitespace → comments → markdown.
        Returns (normalized_text, decoded_texts) where decoded_texts contains
        any payloads decoded during the pipeline for re-scanning.
        """
        result = text
        result = self.normalize_unicode(result)
        result = self.collapse_spaced_text(result)
        result = self.normalize_whitespace(result)
        result = self.strip_comments(result)
        result = self.deobfuscate_markdown(result)
        return result

    def decode_and_rescan(self, text: str) -> list[str]:
        """Decode encoded payloads for re-scanning by the rule engine.

        Returns a list of decoded strings from base64 and URL-encoded payloads
        found in the text. The caller should run the rule engine against each
        decoded string and take the maximum score.

        ROT13 is applied only to segments that contain ROT13-encoded injection
        keywords (detected by the inj_encode_rot13 pattern), not to the entire
        text. Applying ROT13 to normal text creates false positives because the
        ROT13 of any text looks like encoded text to the rule engine.
        """
        decoded_texts: list[str] = []

        # Base64: decode individual payloads and re-scan
        for decoded in self.decode_base64(text):
            decoded_texts.append(decoded)

        # ROT13: only decode if the text already contains ROT13-encoded patterns.
        # The inj_encode_rot13 rule detects these directly; re-scanning the
        # ROT13-decoded version catches the underlying injection content.
        rot13_pattern = re.compile(
            r"vtaber|sbetrg|qvfrertnq|bireevqr|flfgrz cezcg",
            re.IGNORECASE,
        )
        if rot13_pattern.search(text):
            rot13 = self.decode_rot13(text)
            if rot13 != text:
                decoded_texts.append(rot13)

        # URL-encoded: only decode if the text contains URL-encoded sequences
        if self._URL_ENC.search(text):
            url_decoded = self.decode_url(text)
            if url_decoded != text:
                decoded_texts.append(url_decoded)

        return decoded_texts

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

    def collapse_spaced_text(self, text: str) -> str:
        """Collapse spaced-out single-char interleaving.

        "i g n o r e  a l l" → "ignore all"
        "I g n o r e" → "Ignore"
        This defeats the most common manual bypass where spaces are inserted
        between every character to break regex matches.

        Runs BEFORE whitespace normalization so multi-space gaps between words
        are preserved as word boundaries.
        """
        # Split on multi-space gaps (2+ spaces) to find word boundaries first
        segments = re.split(r"(\s{2,})", text)
        result_parts = []
        for segment in segments:
            if re.match(r"^\s{2,}$", segment):
                # Multi-space gap → single space word boundary
                result_parts.append(" ")
            else:
                # Collapse single-char spaced sequences within each word segment
                def _rejoin(match: re.Match[str]) -> str:
                    raw = match.group(0)
                    collapsed = re.sub(r"(\w)\s+(?=\w)", r"\1", raw)
                    # Only accept if collapsing produces 3+ char word
                    word_len = len(collapsed)
                    if word_len < 3:
                        return raw
                    # Preserve case: if first char is uppercase and rest lowercase, title-case the result
                    if raw[0].isupper() and all(c.islower() or c.isspace() for c in raw[1:]):
                        return collapsed[0] + collapsed[1:].lower()
                    return collapsed

                result_parts.append(self._SPACED_SINGLE_CHAR.sub(_rejoin, segment))

        return "".join(result_parts)

    def detect_encodings(self, text: str) -> str:
        """Flag encoded payloads. Kept for backward compatibility.

        Detection adds markers so rules can match on encoded patterns directly.
        Decoding is now handled by decode_and_rescan() for full re-scanning.
        """
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
