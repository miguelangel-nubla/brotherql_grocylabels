"""Text processing utilities for labels."""

from typing import Tuple, List
from PIL import ImageFont


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, max_lines: int) -> Tuple[str, float]:
    """Wrap text to fit within specified width and line limits."""
    min_width = font.getlength("A") * 3
    if max_width < min_width:
        return _truncate_text(text, font, max_width)
    
    words = _break_long_words(text.split(), font, max_width)
    lines = _create_lines(words, font, max_width)
    lines = _limit_lines(lines, max_lines, font)
    
    longest_line = max(font.getlength(line) for line in lines) if lines else 0
    return '\n'.join(lines), longest_line


def _truncate_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> Tuple[str, float]:
    """Truncate text for very narrow labels."""
    max_chars = max(1, int(max_width / font.getlength("A")))
    truncated = text[:max_chars] + ("..." if len(text) > max_chars else "")
    return truncated, font.getlength(truncated)


def _break_long_words(words: List[str], font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
    """Break words that are too long to fit on a single line."""
    result = []
    min_char_width = font.getlength("A")
    
    for word in words:
        if font.getlength(word) >= max_width:
            if max_width < min_char_width * 1.5:
                result.append(word[0] if word else "")
            else:
                mid = len(word) // 2
                result.extend([word[:mid] + '-', word[mid:]])
        else:
            result.append(word)
    return result


def _create_lines(words: List[str], font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
    """Create lines from words, fitting as many as possible per line."""
    lines = []
    words_copy = words.copy()
    
    while words_copy:
        line_words = []
        while words_copy:
            word = words_copy.pop(0)
            test_line = ' '.join(line_words + [word])
            if font.getlength(test_line) < max_width:
                line_words.append(word)
            else:
                words_copy.insert(0, word)
                break
        
        # Prevent infinite loop by forcing at least one character
        if not line_words and words_copy:
            line_words.append(words_copy.pop(0)[:1])
        
        if line_words:
            lines.append(' '.join(line_words))
    
    return lines


def _limit_lines(lines: List[str], max_lines: int, font: ImageFont.FreeTypeFont) -> List[str]:
    """Limit number of lines, adding ellipsis if truncated."""
    if len(lines) <= max_lines:
        return lines
    
    limited_lines = lines[:max_lines]
    limited_lines[-1] += '...'
    return limited_lines