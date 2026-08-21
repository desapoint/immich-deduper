#!/usr/bin/env python3

import os
import sys
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import dash

dash.Dash(__name__, use_pages=True, pages_folder='')

from pages import settings


def walk(node):
	if node is None: return
	if isinstance(node, (list, tuple)):
		for child in node: yield from walk(child)
		return
	yield node
	yield from walk(getattr(node, 'children', None))


def props(node):
	if not hasattr(node, 'to_plotly_json'): return {}
	return node.to_plotly_json().get('props', {})


class TestPageLayouts(unittest.TestCase):
	def test_settings_page_has_reassuring_status_hierarchy(self):
		nodes = list(walk(settings.layout()))
		classes = [str(props(node).get('className', '')) for node in nodes]

		self.assertTrue(any('main page-settings' in value for value in classes))
		self.assertTrue(any('settings-intro' == value for value in classes))
		self.assertTrue(any('settings-layout' == value for value in classes))
		self.assertEqual(sum('settings-status-item' in value for value in classes), 7)


if __name__ == '__main__':
	unittest.main()
