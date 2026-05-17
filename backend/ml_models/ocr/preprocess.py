import re

LATIN_TO_CYRILLIC = {
      'A': 'А', 'B': 'В', 'C': 'С', 'E': 'Е', 'H': 'Н',
      'K': 'К', 'M': 'М', 'O': 'О', 'P': 'Р', 'T': 'Т',
      'X': 'Х', 'Y': 'У', 'a': 'а', 'c': 'с', 'e': 'е',
      'o': 'о', 'p': 'р', 'x': 'х', 'y': 'у'
}

_JUNK_PATTERN = re.compile(
    r'\d+[\s.,]?\s*(?:г|гр|мл|кг|ккал|руб|р|₽|шт|rp|rр|cal|mg|ml|kg|g)\b'
    r'|\d+',
    re.IGNORECASE
)

_STOP_WORDS = {
    'меню', 'завтрак', 'обед', 'ужин', 'полдник', 'перекус',
    'столовая', 'ресторан', 'кафе', 'бар', 'буфет', 'бистро',
    'название', 'блюдо', 'блюда', 'состав', 'выход', 'цена',
    'итого', 'всего', 'сумма', 'стоимость', 'прейскурант',
    'горячее', 'холодное', 'гарнир', 'десерт', 'напиток', 'напитки',
    'салаты', 'супы', 'закуски', 'выпечка', 'соусы',
}

def normilize_ocr_text(text: str) -> str:
    text = ''.join(LATIN_TO_CYRILLIC.get(ch, ch) for ch in text)
    text = _JUNK_PATTERN.sub('', text)
    text = re.sub(r'[:/;\\|.\[\](){}]', '', text)
    tokens = [t for t in text.split() if re.search(r'[а-яёА-ЯЁ]', t)]
    text = ' '.join(tokens)
    return text if text.lower() not in _STOP_WORDS else ''