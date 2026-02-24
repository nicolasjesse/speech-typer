"""Text formatting and filler word removal."""

import re
from typing import Optional


class TextFormatter:
    """Formats transcribed text by removing fillers and cleaning up."""

    # Common filler words/phrases to remove
    FILLER_PATTERNS = [
        r"\b(um+|uh+|er+|ah+)\b",
        r"\b(like,?\s*)+(?=\w)",  # "like" as filler
        r"\b(you know,?\s*)+",
        r"\b(so,?\s*)+(?=like|um|uh|you know)",  # "so" before other fillers
        r"\b(actually,?\s*)+(?=um|uh|like)",
        r"\b(basically,?\s*)+(?=um|uh|like)",
        r"\b(I mean,?\s*)+(?=um|uh|like)",
        r"\b(kind of|kinda)\s+(?=um|uh|like)",
        r"\b(sort of|sorta)\s+(?=um|uh|like)",
    ]

    def __init__(self, remove_fillers: bool = True):
        """Initialize formatter."""
        self._remove_fillers = remove_fillers
        self._filler_regex = re.compile(
            "|".join(self.FILLER_PATTERNS),
            re.IGNORECASE
        )

    def format(self, text: str) -> str:
        """Apply all formatting to text."""
        if not text:
            return ""

        result = text.strip()

        if self._remove_fillers:
            result = self._remove_filler_words(result)

        result = self._fix_capitalization(result)
        result = self._fix_punctuation(result)
        result = self._clean_whitespace(result)

        return result

    def _remove_filler_words(self, text: str) -> str:
        """Remove filler words from text."""
        # Apply filler patterns
        result = self._filler_regex.sub("", text)

        # Remove standalone fillers that might have been missed
        standalone = r"(?:^|\s)(um+|uh+|er+|ah+)(?:\s|[,.]|$)"
        result = re.sub(standalone, " ", result, flags=re.IGNORECASE)

        return result

    def _fix_capitalization(self, text: str) -> str:
        """Ensure proper capitalization."""
        if not text:
            return ""

        # Capitalize first character
        result = text[0].upper() + text[1:] if len(text) > 1 else text.upper()

        # Capitalize after sentence-ending punctuation
        result = re.sub(
            r'([.!?]\s+)([a-z])',
            lambda m: m.group(1) + m.group(2).upper(),
            result
        )

        return result

    def _fix_punctuation(self, text: str) -> str:
        """Clean up punctuation issues."""
        result = text

        # Remove multiple punctuation marks (keep first)
        result = re.sub(r'([.!?,;:])\1+', r'\1', result)

        # Remove space before punctuation
        result = re.sub(r'\s+([.!?,;:])', r'\1', result)

        # Ensure space after punctuation (except at end)
        result = re.sub(r'([.!?,;:])([A-Za-z])', r'\1 \2', result)

        # Add period at end if missing punctuation
        result = result.strip()
        if result and result[-1] not in ".!?":
            result += "."

        return result

    def _clean_whitespace(self, text: str) -> str:
        """Clean up extra whitespace."""
        # Collapse multiple spaces
        result = re.sub(r' +', ' ', text)

        # Remove leading/trailing whitespace
        result = result.strip()

        return result

    def set_remove_fillers(self, remove: bool) -> None:
        """Enable or disable filler removal."""
        self._remove_fillers = remove
