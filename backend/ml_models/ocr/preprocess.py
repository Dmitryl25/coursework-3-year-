import re

LATIN_TO_CYRILLIC = {
      'A': 'А', 'B': 'В', 'C': 'С', 'E': 'Е', 'H': 'Н',
      'K': 'К', 'M': 'М', 'O': 'О', 'P': 'Р', 'T': 'Т',
      'X': 'Х', 'Y': 'У', 'a': 'а', 'c': 'с', 'e': 'е',
      'o': 'о', 'p': 'р', 'x': 'х', 'y': 'у'
}

_JUNK_PATTERN = re.compile(
    r'\d+[\s.,]?\s*(?:г|гр|мл|кг|ккал|руб|р|₽|шт|rp|cal|mg|ml|kg|g)\b'
    r'|\d+[\s.,]\d+'
    r'|\b\d+\b',
    re.IGNORECASE
)

def normilize_ocr_text(text: str) -> str:
    text = ''.join(LATIN_TO_CYRILLIC.get(ch, ch) for ch in text)
    text = _JUNK_PATTERN.sub('', text)
    text = re.sub(r'[:/;\\|]', '', text)
    return ' '.join(text.split())