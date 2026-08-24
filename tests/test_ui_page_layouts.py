#!/usr/bin/env python3

import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import dash

dash.Dash(__name__, use_pages=True, pages_folder='')

from pages import fetch, not_found_404, settings, vector, view
import db.sets as dbsets
from dto import DtoSets
from mod import models
from ui import cardSets, pager


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
	def test_pager_controls_share_one_compact_control_height(self):
		nodes = list(walk(pager.createPager(
			pgId='layout-test', page=2, size=25, total=80,
		)))
		classes = [str(props(node).get('className', '')) for node in nodes]

		self.assertTrue(any('pager-shell' in value for value in classes))
		self.assertTrue(any(value == 'pager' for value in classes))
		self.assertTrue(any(value == 'pager-info' for value in classes))
		self.assertTrue(any(value == 'pager-size' for value in classes))
		sizer = next(
			node for node in nodes
			if props(node).get('id') == {'type': 'pgr-layout-test-sizer', 'idx': 0}
		)
		self.assertEqual(props(sizer).get('value'), 25)
		self.assertTrue(any(getattr(node, 'children', None) == ' / page' for node in nodes))

	def test_threshold_and_worker_controls_share_slider_markup(self):
		thresholdNodes = list(walk(cardSets.renderThreshold()))
		workerNodes = list(walk(cardSets.renderCpuSettings()))
		threshold = next(node for node in thresholdNodes if props(node).get('id') == cardSets.k.id(cardSets.k.threshold))
		worker = next(node for node in workerNodes if props(node).get('id') == cardSets.k.id(cardSets.k.cpuWorkers))

		self.assertEqual(props(threshold).get('className'), 'ui-slider')
		self.assertEqual(props(worker).get('className'), 'ui-slider')
		self.assertEqual(props(threshold).get('included'), False)
		self.assertEqual(props(worker).get('included'), False)
		self.assertEqual(props(threshold).get('tooltip'), props(worker).get('tooltip'))

	def test_text_settings_debounce_persistence_until_typing_pauses(self):
		nodes = list(walk(cardSets.renderCard()))
		pathFilter = next(node for node in nodes if props(node).get('id') == cardSets.k.id(cardSets.k.pathFilter))
		excludeName = next(node for node in nodes if props(node).get('id') == cardSets.k.excl('filNam'))

		self.assertEqual(props(pathFilter).get('debounce'), 750)
		self.assertEqual(props(excludeName).get('debounce'), 750)

	def test_search_settings_skip_unchanged_persistence_and_outputs(self):
		class Tracked(SimpleNamespace):
			def __init__(self, **values):
				object.__setattr__(self, 'writes', [])
				for name, value in values.items(): object.__setattr__(self, name, value)

			def __setattr__(self, name, value):
				if name != 'writes': self.writes.append(name)
				object.__setattr__(self, name, value)

		muod = Tracked(on=False, sz=10)
		gpsk = Tracked(eqDt=False, eqW=False, eqH=False, eqFsz=False)
		dto = Tracked(
			thMin=0.93, autoNext=True, showGridInfo=True, rtree=False,
			rtreeMax=200, pathFilter='', muod=muod, gpsk=gpsk,
		)
		with (
			patch.object(cardSets.db, 'dto', dto),
			patch.object(cardSets, 'getTrgId', return_value=cardSets.k.threshold),
		):
			result = cardSets.settings_OnUpd(
				0.93, True, True, False, 200, '', False, 10,
				False, False, False, False, {},
			)

		self.assertEqual(dto.writes, [])
		self.assertEqual(muod.writes, [])
		self.assertEqual(gpsk.writes, [])
		self.assertTrue(all(value is cardSets.noUpd for value in result))

	def test_search_settings_keep_mutually_exclusive_controls_in_sync(self):
		class Tracked(SimpleNamespace):
			def __init__(self, **values):
				object.__setattr__(self, 'writes', [])
				for name, value in values.items(): object.__setattr__(self, name, value)

			def __setattr__(self, name, value):
				if name != 'writes': self.writes.append((name, value))
				object.__setattr__(self, name, value)

		muod = Tracked(on=True, sz=10)
		gpsk = Tracked(eqDt=False, eqW=False, eqH=False, eqFsz=False)
		dto = Tracked(
			thMin=0.93, autoNext=True, showGridInfo=True, rtree=False,
			rtreeMax=200, pathFilter='', muod=muod, gpsk=gpsk,
		)
		with (
			patch.object(cardSets.db, 'dto', dto),
			patch.object(cardSets, 'getTrgId', return_value=cardSets.k.simRtree),
		):
			result = cardSets.settings_OnUpd(
				0.93, True, True, True, 200, '', True, 10,
				False, False, False, False, {},
			)

		self.assertFalse(muod.on)
		self.assertTrue(dto.rtree)
		self.assertIs(result[0], cardSets.noUpd)
		self.assertTrue(result[1])
		self.assertFalse(result[2])
		self.assertIs(result[3], cardSets.noUpd)

	def test_wildcard_settings_persist_only_the_changed_field(self):
		dto = DtoSets()
		saved = []

		def useDefaults(_key, defaultValue=None): return defaultValue
		def trackSave(key, value):
			saved.append((key, value))
			return True

		with (
			patch.object(dbsets, 'get', side_effect=useDefaults),
			patch.object(dbsets, 'save', side_effect=trackSave),
			patch.object(cardSets.db, 'dto', dto),
			patch.object(cardSets.db.psql, 'getSchema', return_value=SimpleNamespace(hasAssetDeviceId=True)),
		):
			with patch.object(cardSets, 'ctx', SimpleNamespace(inputs_list=[[
				{'id': {'type': 'ausl', 'field': 'on'}, 'value': True},
				{'id': {'type': 'ausl', 'field': 'earlier'}, 'value': 3},
				{'id': {'type': 'ausl', 'field': 'usrPri'}, 'value': ''},
				{'id': {'type': 'ausl', 'field': 'usrWgt'}, 'value': 0},
				{'id': {'type': 'ausl', 'field': 'pthVal'}, 'value': ''},
				{'id': {'type': 'ausl', 'field': 'pthWgt'}, 'value': 0},
				{'id': {'type': 'ausl', 'field': 'devPri'}, 'value': ''},
				{'id': {'type': 'ausl', 'field': 'devWgt'}, 'value': 0},
			]])):
				cardSets.ausl_OnUpd([True, 3, '', 0, '', 0, '', 0])
			self.assertEqual([key for key, _ in saved], ['ausl'])

			saved.clear()
			with patch.object(cardSets, 'ctx', SimpleNamespace(inputs_list=[[
				{'id': {'type': 'excl', 'field': 'on'}, 'value': True},
				{'id': {'type': 'excl', 'field': 'fndLes'}, 'value': 2},
			]])):
				cardSets.excl_OnUpd([True, 2])
			self.assertEqual([key for key, _ in saved], ['excl'])

			saved.clear()
			with patch.object(cardSets, 'ctx', SimpleNamespace(inputs_list=[[
				{'id': {'type': 'mrg', 'field': 'on'}, 'value': False},
				{'id': {'type': 'mrg', 'field': 'albums'}, 'value': True},
			]])):
				cardSets.mrg_OnUpd([False, True])
			self.assertEqual([key for key, _ in saved], ['mrg'])

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
		self.assertEqual(sum('settings-status-state' == value for value in classes), 7)
		statusItems = [node for node in nodes if 'settings-status-item' in str(props(node).get('className', ''))]
		self.assertTrue(all(props(node).get('data-check-status') == 'pending' for node in statusItems))

	def test_fetch_page_explains_sync_and_separates_actions(self):
		nodes = list(walk(fetch.layout()))
		classes = [str(props(node).get('className', '')) for node in nodes]

		self.assertTrue(any('main page-fetch' in value for value in classes))
		self.assertTrue(any('fetch-intro' == value for value in classes))
		self.assertEqual(sum('fetch-sync-note' == value for value in classes), 4)
		self.assertEqual(sum('fetch-action-unit' in value for value in classes), 3)
		self.assertTrue(any('fetch-action-danger' in value for value in classes))
		self.assertTrue(any('fetch-library-grid' == value for value in classes))
		self.assertTrue(any('fetch-library-main' == value for value in classes))
		self.assertTrue(any('fetch-library-mapping' == value for value in classes))

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

	def test_view_filter_transition_updates_pager_before_loading_grid(self):
		pagerData = models.Pager(idx=3, size=25, cnt=100).toDict()
		with (
			patch.object(view.db.pics, 'countFiltered', return_value=12),
			patch.object(view, 'getTrgId', return_value=view.k.schKeyword),
		):
			filtered = models.Pager.fromDic(view.vw_OnOptChg('', 'all', False, 'cat', '', False, False, {}, pagerData))
		self.assertEqual(filtered.idx, 1)
		self.assertEqual(filtered.cnt, 12)

		with (
			patch.object(view.db.pics, 'countFiltered', return_value=60),
			patch.object(view, 'getTrgId', return_value=view.ks.sto.cnt),
		):
			refreshed = models.Pager.fromDic(view.vw_OnOptChg('', 'all', False, '', '', False, False, {}, pagerData))
		self.assertEqual(refreshed.idx, 3)
		self.assertEqual(refreshed.cnt, 60)

	def test_view_delete_uses_compact_action_descriptor(self):
		result = view.vw_OnDel(
			{'id': {'type': 'asset-del', 'aid': 42}, 'nonce': 1},
			models.Tsk().toDict(),
		)
		modal = models.Mdl.fromDic(result)
		self.assertEqual(modal.args['aid'], 42)

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
