#!/usr/bin/env python3

import os
import sys
import unittest
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import dash

dash.Dash(__name__, use_pages=True, pages_folder='')

from pages import fetch, not_found_404, settings, vector, view


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
	def test_maintenance_actions_use_solid_button_styles(self):
		with (
			patch.object(fetch.db.psql, 'fetchUsers', return_value=[]),
			patch.object(vector.cardSets.db.psql, 'fetchUsers', return_value=[]),
		):
			fetchNodes = list(walk(fetch.layout()))
			vectorNodes = list(walk(vector.layout()))

		fetchReset = next(node for node in fetchNodes if props(node).get('id') == fetch.k.btnReset)
		vectorRepair = next(node for node in vectorNodes if props(node).get('id') == vector.K.btnRepairIdx)
		vectorClear = next(node for node in vectorNodes if props(node).get('id') == vector.K.btnClear)
		self.assertFalse(props(fetchReset).get('outline', False))
		self.assertFalse(props(vectorRepair).get('outline', False))
		self.assertFalse(props(vectorClear).get('outline', False))

	def test_settings_page_has_reassuring_status_hierarchy(self):
		nodes = list(walk(settings.layout()))
		classes = [str(props(node).get('className', '')) for node in nodes]

		self.assertTrue(any('main page-settings' in value for value in classes))
		self.assertTrue(any('settings-intro' == value for value in classes))
		self.assertTrue(any('settings-layout' == value for value in classes))
		self.assertEqual(sum('settings-status-item' in value for value in classes), 7)

	def test_fetch_page_explains_sync_and_separates_actions(self):
		nodes = list(walk(fetch.layout()))
		classes = [str(props(node).get('className', '')) for node in nodes]

		self.assertTrue(any('main page-fetch' in value for value in classes))
		self.assertTrue(any('fetch-intro' == value for value in classes))
		self.assertEqual(sum('fetch-sync-note' == value for value in classes), 4)
		self.assertEqual(sum('fetch-action-unit' in value for value in classes), 3)
		self.assertTrue(any('fetch-action-danger' in value for value in classes))

	def test_vector_page_presents_pipeline_and_action_risk(self):
		nodes = list(walk(vector.layout()))
		classes = [str(props(node).get('className', '')) for node in nodes]

		self.assertTrue(any('main page-vector' in value for value in classes))
		self.assertTrue(any('vector-intro' == value for value in classes))
		self.assertEqual(sum('vector-step' == value for value in classes), 4)
		self.assertEqual(sum('vector-action-unit' in value for value in classes), 3)
		self.assertTrue(any('vector-action-danger' in value for value in classes))
		self.assertTrue(any('vector-repair-note' == value for value in classes))

	def test_view_page_groups_filters_and_results_clearly(self):
		with patch.object(view.db.pics, 'count', return_value=24):
			nodes = list(walk(view.layout()))
		classes = [str(props(node).get('className', '')) for node in nodes]

		self.assertTrue(any('main page-view' in value for value in classes))
		self.assertTrue(any('view-intro' == value for value in classes))
		self.assertEqual(sum('view-filter-field' in value for value in classes), 4)
		self.assertTrue(any('view-trait-filters' == value for value in classes))
		self.assertTrue(any('view-results-shell' == value for value in classes))

		filename = next(node for node in nodes if props(node).get('id') == view.k.schKeyword)
		path = next(node for node in nodes if props(node).get('id') == view.k.schPath)
		self.assertTrue(props(filename).get('debounce'))
		self.assertTrue(props(path).get('debounce'))

	def test_not_found_page_reassures_and_offers_recovery_paths(self):
		nodes = list(walk(not_found_404.layout()))
		classes = [str(props(node).get('className', '')) for node in nodes]
		hrefs = [props(node).get('href') for node in nodes if props(node).get('href')]

		self.assertTrue(any('main page-not-found' in value for value in classes))
		self.assertTrue(any('not-found-state' == value for value in classes))
		self.assertIn('/', hrefs)
		self.assertIn(f'/{not_found_404.ks.pg.view}', hrefs)


if __name__ == '__main__':
	unittest.main()
