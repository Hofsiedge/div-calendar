import os.path
from collections import namedtuple

Rule = namedtuple('Rule', ['left', 'right'])

class Mapper:

    def __init__(self):
        self.rules = []
        self.symbols = set()


    # TODO: refactor as property
    def set_symbols(self, symbols: str) -> None:
        self.symbols = set(symbols)


    def add_rule(self, left, right) -> None:
        self.rules.append(Rule(left, right))


    def process(self, source: str) -> str:
        result = []
        chars = list(filter(lambda x: x in self.symbols, source))

        cache = {}
        i = 0
        while i < len(chars):
            if chars[i] not in self.symbols:
                chars[i] = ' '
                continue

            for rule in self.rules:
                L = len(rule.left)
                if L not in cache:
                    cache[L] = ''.join(chars[i:i + L] if i + L <= len(chars) else '')
                string_part = cache[L]
                if string_part == rule.left:
                    result.append(rule.right)
                    i += L
                    cache.clear()
                    break
            else:
                cache.clear()
                i += 1

        return ''.join(result)


class Transliterator:

    def __init__(self, mapping_directory: str):
        self.mapping_directory = mapping_directory
        self._mappers = {}


    def translit(self, source: str, origin: str, target: str) -> str:
        if f'{origin}_{target}' not in self._mappers:
            self._load(origin, target)
        return self._mappers[f'{origin}_{target}'].process(source)


    def _load(self, origin: str, target: str) -> None:
        mapper = Mapper()
        with open(os.path.join(self.mapping_directory, f'{origin}_{target}'), 'r') as f:
            lines = iter(f.read().splitlines())
            symbols = next(lines)
            mapper.set_symbols(symbols)

            for line in lines:
                if line.startswith('#') or line == '':    # skip comments and blank lines
                    continue
                left, right = line.split('\t')
                mapper.add_rule(left, right)
        self._mappers[f'{origin}_{target}'] = mapper

