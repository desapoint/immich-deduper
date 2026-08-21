#!/usr/bin/env python3

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class TestGlobalUiFoundation(unittest.TestCase):
	def test_modern_surface_tokens_are_defined(self):
		base = (ROOT / 'src/scss/base.scss').read_text()
		for token in (
			'--ui-bg:', '--ui-surface:', '--ui-border:', '--ui-text:',
			'--ui-accent:', '--ui-radius:', '--ui-shadow:', '--ui-focus:',
		):
			self.assertIn(token, base)

	def test_global_components_share_the_foundation(self):
		main = (ROOT / 'src/scss/main.scss').read_text()
		for selector in (
			'.navbar {', '.navLnk {', '.body-header {', '.card {',
			'.form-control,', '.btn {', '.pager {', '.notify {', '.tskPanel {',
		):
			self.assertIn(selector, main)

	def test_global_layout_has_tablet_and_phone_rules(self):
		main = (ROOT / 'src/scss/main.scss').read_text()
		self.assertIn('@media (max-width: 1100px)', main)
		self.assertIn('@media (max-width: 767px)', main)
		self.assertIn('grid-template-columns: 1fr;', main)


if __name__ == '__main__':
	unittest.main()
