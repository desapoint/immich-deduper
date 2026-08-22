#!/usr/bin/env python3

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EMOJI = re.compile(r'[\U0001F000-\U0001FAFF\u2300-\u23FF\u2600-\u27BF\u2B00-\u2BFF\uFE0F]')


class TestUiText(unittest.TestCase):
	def test_application_source_has_no_emoji_glyphs(self):
		matches = []
		for suffix in ('*.py', '*.js'):
			for source in (ROOT / 'src').rglob(suffix):
				for lineNumber, line in enumerate(source.read_text(encoding='utf-8').splitlines(), start=1):
					if EMOJI.search(line): matches.append(f'{source.relative_to(ROOT)}:{lineNumber}')

		self.assertEqual(matches, [], f'Emoji glyphs remain in application source: {matches}')


if __name__ == '__main__':
	unittest.main()
