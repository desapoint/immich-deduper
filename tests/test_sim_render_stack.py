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
	def test_render_state_callback_is_registered(self):
		testApp.layout = dash.html.Div()
		testApp._setup_server()
		self.assertTrue(any('sim-render-state.data' in key for key in testApp.callback_map))

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
			[['props', 'children', 1], ['props', 'children', 2]],
		)

	def test_removed_group_deletes_only_its_existing_rows(self):
		oldAssets = [asset(1, 1), asset(2, 1), asset(3, 2), asset(4, 2)]
		newAssets = [asset(3, 2), asset(4, 2)]
		oldState = similar._similarRenderState(oldAssets, True)
		newState = similar._similarRenderState(newAssets, True)

		gridPatch = similar._patchMultiGrid(oldState, newState, newAssets)
		operations = gridPatch.to_plotly_json()['operations']
		self.assertEqual([operation['operation'] for operation in operations], ['Delete', 'Delete', 'Delete'])
		self.assertEqual(
			[operation['location'] for operation in operations],
			[['props', 'children', 2], ['props', 'children', 1], ['props', 'children', 0]],
		)

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


if __name__ == '__main__':
	unittest.main()
