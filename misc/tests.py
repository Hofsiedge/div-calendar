from django.test import TestCase
from .services import Transliterator

class TransliteratorTestCase(TestCase):

    def setUp(self):
        self.transliterator = Transliterator('mappings')


    def test_enru(self):
        pairs = [
            ('sberbank 123 @ 4', 'сбербанк 123  4'),
            ('gazprom neft _ 2', 'газпром нефт  2'),
            ('yandex-8', 'яндекс-8'),
        ]

        for pair in pairs:
            self.assertEqual(self.transliterator.translit(pair[0], 'en', 'ru'), pair[1])


    def test_ruen(self):
        pairs = [
            ('яндекс', 'yandex'),
            ('м.видео', 'm.video'),
            ('мэил ру', 'mail ru'),
        ]

        for pair in pairs:
            self.assertEqual(self.transliterator.translit(pair[0], 'ru', 'en'), pair[1])
