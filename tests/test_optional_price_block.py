"""Copied position values must remain visible even in an unpriced order."""
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace
import unittest

from jinja2 import Environment, FileSystemLoader


class PriceBlock(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.price = {}
        self.panel = {}
        self.toggle = {}
        self.current_select = None
        self.selected_taxes = []
        self.feed(html)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if attrs.get('id') == 'article_price':
            self.price = attrs
        if attrs.get('id') == 'collapsePrice':
            self.panel = attrs
        if attrs.get('aria-controls') == 'collapsePrice':
            self.toggle = attrs
        if tag == 'select':
            self.current_select = attrs.get('id')
        if tag == 'option' and self.current_select == 'tax' and 'selected' in attrs:
            self.selected_taxes.append(attrs.get('value'))

    def handle_endtag(self, tag):
        if tag == 'select':
            self.current_select = None


class OptionalPriceBlockTests(unittest.TestCase):
    def render(self, price_exist, copied_price=None, copied_tax=None):
        template_dir = Path(__file__).resolve().parents[1] / 'app/templates'
        env = Environment(loader=FileSystemLoader(template_dir), autoescape=True)
        copied_order = None if copied_price is None and copied_tax is None else SimpleNamespace(
            article_price=copied_price, tax=copied_tax, rd_date=None, rd_type='', rd_name='')
        html = env.get_template('helpers/article_price_rd_box_v2.html').render(
            price_exist=price_exist, copied_order=copied_order, tax_list=[0, 5, 10, 20, 22], rd_types_list=[])
        return PriceBlock(html)

    def test_copy_with_values_opens_block_and_preserves_values(self):
        for order_has_prices in (False, True):
            for price, tax in ((100.25, 22), (100, 0), (0, 22)):
                with self.subTest(order_has_prices=order_has_prices, price=price, tax=tax):
                    block = self.render(order_has_prices, price, tax)
                    self.assertIn('show', block.panel['class'].split())
                    self.assertEqual(block.toggle['aria-expanded'], 'true')
                    self.assertEqual(float(block.price['value']), price)
                    self.assertEqual(int(block.selected_taxes[-1]), tax)

    def test_unpriced_copy_and_new_position_stay_collapsed(self):
        for price, tax in ((None, None), (0, 0)):
            block = self.render(False, price, tax)
            self.assertNotIn('show', block.panel['class'].split())
            self.assertEqual(block.toggle['aria-expanded'], 'false')

    def test_existing_order_price_mode_still_opens_block(self):
        block = self.render(True)
        self.assertIn('show', block.panel['class'].split())
        self.assertIn('required', block.price)
        self.assertEqual(block.price['min'], '1')


if __name__ == '__main__':
    unittest.main()
