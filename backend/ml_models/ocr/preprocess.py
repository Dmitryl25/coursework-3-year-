LATIN_TO_CYRILLIC = {
      'A': 'А', 'B': 'В', 'C': 'С', 'E': 'Е', 'H': 'Н',
      'K': 'К', 'M': 'М', 'O': 'О', 'P': 'Р', 'T': 'Т',
      'X': 'Х', 'Y': 'У', 'a': 'а', 'c': 'с', 'e': 'е',
      'o': 'о', 'p': 'р', 'x': 'х', 'y': 'у'
}

def normilize_ocr_text(text: str) -> str:
    return ''.join(LATIN_TO_CYRILLIC.get(ch, ch) for ch in text)