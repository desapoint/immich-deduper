#!/usr/bin/env python3

import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import dash

testApp = dash.Dash(__name__, use_pages=True, pages_folder='', suppress_callback_exceptions=True)

from mod import models
from pages import similar


def asset(autoId, groupId, stackId=None):
	item = models.Asset(
		autoId=autoId,
		id=f'asset-{autoId}',
		ownerId='owner-a',
		originalFileName=f'{autoId}.jpg',
		originalPath=f'/library/{autoId}.jpg',
		jsonExif=models.AssetExif(exifImageWidth=100, exifImageHeight=100),
		ex=models.AssetExInfo(
			stackId=stackId,
			stackPrimaryAssetId=f'asset-{autoId}' if stackId else None,
			stackAssets=[f'asset-{autoId}'] if stackId else [],
		),
	)
	item.vw.muodId = groupId
	item.vw.isMain = autoId in {1, 3}
	return item


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


class TestSimilarPartialRendering(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		for page in dash.page_registry.values():
			module = sys.modules.get(page['module'])
			if module is not None and hasattr(module, 'layout'):
				page['layout'] = module.layout
		testApp.layout = dash.html.Div()
		testApp._setup_server()
		cls.client = testApp.server.test_client()

	def test_similar_page_has_guided_review_hierarchy(self):
		with (
			patch.object(similar.immich, 'isMergeAvailable', return_value=(True, None)),
			patch.object(similar.cardSets.db.psql, 'fetchUsers', return_value=[]),
		):
			nodes = list(walk(similar.layout()))

		classes = [str(props(node).get('className', '')) for node in nodes]
		self.assertTrue(any('main page-similar' in value for value in classes))
		self.assertTrue(any(value == 'similar-intro' for value in classes))
		self.assertTrue(any(value == 'similar-config-grid' for value in classes))
		self.assertEqual(sum(value == 'similar-search-action' or value.startswith('similar-search-action ') for value in classes), 3)
		self.assertTrue(any('similar-workspace' in value for value in classes))
		clearButton = next(node for node in nodes if props(node).get('id') == similar.k.btnClear)
		resetButton = next(node for node in nodes if props(node).get('id') == similar.k.btnReset)
		self.assertFalse(props(clearButton).get('outline', False))
		self.assertFalse(props(resetButton).get('outline', False))

	def test_render_state_callback_is_registered(self):
		self.assertTrue(any('sim-render-state.data' in key for key in testApp.callback_map))

	def test_empty_similar_store_updates_do_not_return_http_500(self):
		key = next(key for key in testApp.callback_map if 'sim-btn-fnd.disabled' in key)
		callback = testApp.callback_map[key]
		now = models.Now(sim=models.PgSim(
			pagerPnd=models.Pager(idx=1, size=25, cnt=0),
			activeTab=similar.k.tabCur,
		)).toDict()
		outputs = [output.to_dict() for output in callback['output'][:9]] + [[], [], [], [], []]
		payload = {
			'output': key,
			'outputs': outputs,
			'changedPropIds': ['store-now.data'],
			'inputs': [
				{'id': 'store-now', 'property': 'data', 'value': now},
				{'id': 'store-state', 'property': 'data', 'value': models.Ste().toDict()},
				{'id': 'store-count', 'property': 'data', 'value': models.Cnt().toDict()},
				{'id': 'store-tsk', 'property': 'data', 'value': models.Tsk().toDict()},
			],
			'state': [
				{'id': callback['state'][0]['id'], 'property': 'id', 'value': []},
				{'id': callback['state'][1]['id'], 'property': 'id', 'value': []},
				{'id': callback['state'][2]['id'], 'property': 'id', 'value': []},
			],
		}

		with patch.object(similar.db.pics, 'countHasSimIds', return_value=0):
			response = self.client.post('/_dash-update-component', json=payload)

		self.assertEqual(response.status_code, 200, response.get_data(as_text=True))

	def test_unchanged_store_update_does_not_replace_grid(self):
		assets = [asset(1, 1), asset(2, 1), asset(3, 2), asset(4, 2)]
		now = models.Now(sim=models.PgSim(assCur=assets))
		renderState = similar._similarRenderState(assets, True)
		dto = SimpleNamespace(muod=SimpleNamespace(on=True))

		with (
			patch.object(similar, 'getTrgId', return_value='store-now'),
			patch.object(similar.db, 'dto', dto),
			patch.object(similar.db.pics, 'getPagedPending', return_value=[]),
		):
			result = similar.sim_Load(now.toDict(), models.Cnt().toDict(), renderState)

		self.assertEqual(len(result), 8)
		self.assertIs(result[0], similar.noUpd)
		self.assertIs(result[7], similar.noUpd)

	def test_pending_tab_renders_cached_assets_immediately(self):
		pending = [asset(7, 1)]
		now = models.Now(sim=models.PgSim(
			assPend=pending,
			pagerPnd=models.Pager(idx=1, size=25, cnt=1),
			activeTab=similar.k.tabCur,
		))

		with patch.object(similar.db.pics, 'getPagedPending') as getPending:
			nowData, grid = similar.sim_OnTabChange(similar.k.tabPnd, now.toDict())

		getPending.assert_not_called()
		self.assertEqual(models.Now.fromDic(nowData).sim.activeTab, similar.k.tabPnd)
		self.assertTrue(any(
			props(node).get('id') == {'type': 'img-pop', 'aid': 7}
			for node in walk(grid)
		))

	def test_pending_tab_fetches_and_renders_missing_page(self):
		pending = [asset(8, 1)]
		now = models.Now(sim=models.PgSim(
			pagerPnd=models.Pager(idx=2, size=15, cnt=20),
			activeTab=similar.k.tabCur,
		))

		with patch.object(similar.db.pics, 'getPagedPending', return_value=pending) as getPending:
			nowData, grid = similar.sim_OnTabChange(similar.k.tabPnd, now.toDict())

		getPending.assert_called_once_with(page=2, size=15)
		updated = models.Now.fromDic(nowData)
		self.assertEqual(updated.sim.activeTab, similar.k.tabPnd)
		self.assertEqual([item.autoId for item in updated.sim.assPend], [8])
		self.assertTrue(any(
			props(node).get('id') == {'type': 'img-pop', 'aid': 8}
			for node in walk(grid)
		))

	def test_empty_grouped_results_use_compact_status(self):
		now = models.Now(sim=models.PgSim(assCur=[]))
		dto = SimpleNamespace(muod=SimpleNamespace(on=True))

		with (
			patch.object(similar, 'getTrgId', return_value='store-now'),
			patch.object(similar.db, 'dto', dto),
			patch.object(similar.db.pics, 'getPagedPending', return_value=[]),
		):
			result = similar.sim_Load(now.toDict(), models.Cnt().toDict(), None)

		nodes = list(walk(result[0]))
		emptyState = next(node for node in nodes if props(node).get('className') == 'sim-empty-state')
		self.assertEqual(props(emptyState).get('role'), 'status')
		self.assertTrue(any(getattr(node, 'children', None) == 'No grouped results found' for node in nodes))

	def test_stack_metadata_patches_only_changed_group_cards(self):
		oldAssets = [asset(1, 1), asset(2, 1), asset(3, 2), asset(4, 2)]
		newAssets = [asset(1, 1, 'stack-a'), asset(2, 1, 'stack-a'), asset(3, 2), asset(4, 2)]
		oldState = similar._similarRenderState(oldAssets, True)
		newState = similar._similarRenderState(newAssets, True)

		with patch('ui.cards.db.psql.getUsrName', return_value='Owner'):
			gridPatch = similar._patchMultiGrid(oldState, newState, newAssets)

		operations = gridPatch.to_plotly_json()['operations']
		self.assertEqual([operation['operation'] for operation in operations], ['Assign', 'Assign'])
		self.assertEqual(
			[operation['location'] for operation in operations],
			[
				['props', 'children', 0, 'props', 'children', 1, 'props', 'children', 0],
				['props', 'children', 0, 'props', 'children', 1, 'props', 'children', 1],
			],
		)

	def test_removed_group_deletes_only_its_existing_rows(self):
		oldAssets = [asset(1, 1), asset(2, 1), asset(3, 2), asset(4, 2)]
		newAssets = [asset(3, 2), asset(4, 2)]
		oldState = similar._similarRenderState(oldAssets, True)
		newState = similar._similarRenderState(newAssets, True)

		gridPatch = similar._patchMultiGrid(oldState, newState, newAssets)
		operations = gridPatch.to_plotly_json()['operations']
		self.assertEqual([operation['operation'] for operation in operations], ['Delete'])
		self.assertEqual(
			[operation['location'] for operation in operations],
			[['props', 'children', 0]],
		)

	def test_changed_group_membership_replaces_only_that_group_container(self):
		oldAssets = [asset(1, 1), asset(2, 1), asset(3, 2), asset(4, 2)]
		newAssets = [asset(1, 1), asset(3, 2), asset(4, 2)]
		oldState = similar._similarRenderState(oldAssets, True)
		newState = similar._similarRenderState(newAssets, True)

		with patch('ui.cards.db.psql.getUsrName', return_value='Owner'):
			gridPatch = similar._patchMultiGrid(oldState, newState, newAssets)

		operations = gridPatch.to_plotly_json()['operations']
		self.assertEqual([operation['operation'] for operation in operations], ['Assign'])
		self.assertEqual([operation['location'] for operation in operations], [['props', 'children', 0]])

	def test_global_controls_share_group_control_structure(self):
		with (
			patch.object(similar.immich, 'isMergeAvailable', return_value=(True, None)),
			patch.object(similar.cardSets.db.psql, 'fetchUsers', return_value=[]),
		):
			nodes = list(walk(similar.layout()))
		selection = next(node for node in nodes if 'sim-global-selection' in str(props(node).get('className', '')))
		actions = next(node for node in nodes if 'sim-global-actions' in str(props(node).get('className', '')))
		selectionNodes = list(walk(selection))
		actionNodes = list(walk(actions))

		selectionButtons = [
			node for node in selectionNodes
			if props(node).get('id') in {
				similar.k.btnAllSelect,
				similar.k.btnAllCancel,
				similar.k.btnSelectMns,
				similar.k.btnSelectStacked,
				similar.k.btnSelectUnstacked,
			}
		]
		self.assertEqual(len(selectionButtons), 5)
		self.assertTrue(all(props(button).get('size') == 'sm' for button in selectionButtons))
		self.assertTrue(all('txt-sm' in props(button).get('className', '') for button in selectionButtons))
		sources = next(button for button in selectionButtons if props(button).get('id') == similar.k.btnSelectMns)
		self.assertEqual(props(sources).get('children'), 'Sources')

		self.assertIn('sim-controls', props(selection).get('className', ''))
		self.assertIn('sim-controls', props(actions).get('className', ''))
		self.assertFalse(any('sim-action-unit' in str(props(node).get('className', '')) for node in actionNodes))
		self.assertTrue(any('sim-confirm-menu' in str(props(node).get('className', '')) for node in actionNodes))

	def test_auto_selection_uses_responsive_field_grid(self):
		with patch.object(similar.cardSets.db.psql, 'fetchUsers', return_value=[]):
			nodes = list(walk(similar.cardSets.renderAutoSelect()))

		classes = [str(props(node).get('className', '')) for node in nodes]
		self.assertTrue(any('auto-select-card' in value for value in classes))
		self.assertTrue(any('auto-select-options' == value for value in classes))
		self.assertTrue(any('auto-select-criteria-grid' == value for value in classes))
		self.assertEqual(sum(value.startswith('icriteria') for value in classes), 11)
		self.assertEqual(sum(value == 'auto-select-field' for value in classes), 22)
		self.assertEqual(sum('auto-select-field-wide' in value for value in classes), 1)

		pathInput = next(
			node for node in nodes
			if isinstance(props(node).get('id'), dict) and props(node)['id'].get('field') == 'pthVal'
		)
		self.assertEqual(type(pathInput).__name__, 'Textarea')
		self.assertEqual(props(pathInput).get('rows'), 3)
		self.assertIn('auto-select-path-input', props(pathInput).get('className', ''))
		self.assertNotIn('maxWidth', props(pathInput).get('style', {}))


if __name__ == '__main__':
	unittest.main()
