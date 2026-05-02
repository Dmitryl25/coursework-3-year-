import sys

sys.path.insert(0, 'backend')
from app.services.matching import match

tests = ['куриная котлета', 'овсянка', 'банан', 'абракадабра xyz']
for t in tests:
    result = match(t)
    print(f'{t!r} -> {result}')