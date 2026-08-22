#!/usr/bin/env python3

import os
import sys
import unittest
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from mod import models
from ui import gv


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


def asset(autoId, groupId, *, source=False, stackId=None, primary=False, live=False):
	item = models.Asset(
		autoId=autoId,
		id=f'asset-{autoId}',
		ownerId='owner-a',
		vdoId=f'video-{autoId}' if live else None,
		originalFileName=f'{autoId}.jpg',
		originalPath=f'/library/{autoId}.jpg',
		jsonExif=models.AssetExif(exifImageWidth=100, exifImageHeight=100),
		ex=models.AssetExInfo(
			stackId=stackId,
			stackPrimaryAssetId=f'asset-{autoId}' if primary else None,
			stackAssets=['asset-1', 'asset-2'] if stackId else [],
		),
	)
	item.vw.muodId = groupId
	item.vw.isMain = source
	return item


class TestSimilarUiLayout(unittest.TestCase):
	def test_view_grid_omits_similarity_group_controls(self):
		assets = [asset(1, 7, source=True), asset(2, 7)]

		with patch('ui.cards.db.psql.getUsrName', return_value='Owner'):
			grid = gv.mkGrd(assets, maker=lambda item: gv.cards.mk(item, False))

		nodes = list(walk(grid))
		self.assertFalse(any('sim-group-header' in str(props(node).get('className', '')) for node in nodes))
		self.assertFalse(any(
			isinstance(props(node).get('id'), dict)
			and props(node)['id'].get('type') in {gv.STACK_GROUP_BUTTON, gv.GROUP_ACTION_BUTTON}
			for node in nodes
		))

	def test_group_controls_and_stack_status_have_stable_anchors(self):
		assets = [
			asset(1, 7, source=True, stackId='stack-a', primary=True),
			asset(2, 7, stackId='stack-a'),
		]

		with patch('ui.cards.db.psql.getUsrName', return_value='Owner'):
			grid = gv.mkGrdGrps(assets)

		nodes = list(walk(grid))
		headers = [node for node in nodes if 'sim-group-header' in str(props(node).get('className', ''))]
		titles = [node for node in nodes if props(node).get('className') == 'sim-group-title']
		cardSelects = [node for node in nodes if isinstance(props(node).get('id'), dict) and props(node)['id'].get('type') == 'card-select']
		primaryRows = [node for node in nodes if 'sim-card-header-primary' in str(props(node).get('className', ''))]
		secondaryRows = [node for node in nodes if props(node).get('className') == 'sim-card-header-secondary']
		cardScores = [node for node in nodes if props(node).get('className') == 'sim-card-score']
		stackStatuses = [node for node in nodes if props(node).get('className') == 'sim-stack-status']
		coverButtons = [node for node in nodes if isinstance(props(node).get('id'), dict) and props(node)['id'].get('type') == gv.STACK_COVER_BUTTON]
		autoLogSlots = [node for node in nodes if props(node).get('className') == 'sim-group-auto-log']
		groupContainers = [node for node in nodes if props(node).get('className') == 'sim-group-container']
		cardLists = [node for node in nodes if props(node).get('className') == 'sim-group-card-list']
		deleteGroup = next(
			node for node in nodes
			if isinstance(props(node).get('id'), dict)
			and props(node)['id'].get('type') == gv.GROUP_ACTION_BUTTON
			and props(node)['id'].get('action') == gv.GROUP_DELETE_ALL
		)

		self.assertEqual(len(headers), 1)
		self.assertEqual(len(groupContainers), 1)
		self.assertEqual(len(cardLists), 1)
		self.assertEqual(props(groupContainers[0]).get('data-group-id'), '7')
		self.assertIn('290px', props(cardLists[0]).get('style', {}).get('gridTemplateColumns', ''))
		self.assertEqual(props(titles[0]).get('data-group-id'), '7')
		self.assertEqual([props(node).get('data-group-id') for node in cardSelects], ['7', '7'])
		self.assertEqual([props(node).get('data-stack-id') for node in cardSelects], ['stack-a', 'stack-a'])
		self.assertEqual(len(primaryRows), 2)
		self.assertEqual(len(secondaryRows), 2)
		self.assertEqual(len(cardScores), 2)
		self.assertEqual(len(stackStatuses), 2)
		self.assertEqual(len(coverButtons), 2)
		self.assertEqual(len(autoLogSlots), 1)
		self.assertEqual(props(autoLogSlots[0]).get('data-group-id'), '7')
		self.assertTrue(all(props(button).get('children') == 'Set cover' for button in coverButtons))
		stackCards = [node for node in nodes if 'has-stack' in str(props(node).get('className', ''))]
		self.assertEqual(len(stackCards), 2)
		self.assertTrue(all('--sim-stack-color' in props(card).get('style', {}) for card in stackCards))
		self.assertTrue(any(getattr(node, 'children', None) == 'Source' for node in nodes))
		self.assertTrue(any(getattr(node, 'children', None) == 'Thumbnail' for node in nodes))
		self.assertEqual(props(deleteGroup).get('color'), 'danger')
		self.assertFalse(props(deleteGroup).get('outline', False))

	def test_card_media_defers_offscreen_work(self):
		with patch('ui.cards.db.psql.getUsrName', return_value='Owner'):
			card = gv.cards.mk(asset(1, 7, live=True), stackGroupId=7)

		nodes = list(walk(card))
		videos = [node for node in nodes if props(node).get('className') == 'livephoto']

		self.assertEqual(len(videos), 1)
		self.assertEqual(props(videos[0]).get('preload'), 'metadata')
		self.assertFalse(props(videos[0]).get('autoPlay', False))

	def test_similar_card_has_stable_decision_and_media_zones(self):
		item = asset(1, 7, source=True, stackId='stack-a', primary=True, live=True)
		item.jsonExif.fileSizeInByte = 4096
		item.ex.albs = [models.Album(albumName='Review')]
		item.ex.tags = [models.Tags(value='duplicate')]
		item.ex.facs = [models.AssetFace(name='Person')]

		with patch('ui.cards.db.psql.getUsrName', return_value='Owner'):
			card = gv.cards.mk(item, stackGroupId=7)

		nodes = list(walk(card))
		rootCard = next(node for node in nodes if 'sim-card-five-zone' in str(props(node).get('className', '')))
		decision = next(node for node in nodes if 'sim-card-decision' in str(props(node).get('className', '')))
		selection = next(node for node in nodes if props(node).get('id') == {'type': 'card-select', 'id': 1})
		cover = next(node for node in nodes if props(node).get('id') == {'type': gv.STACK_COVER_BUTTON, 'id': 1, 'group': 7, 'owner': 'owner-a'})
		media = next(node for node in nodes if props(node).get('className') == 'viewer sim-card-media')
		mediaNodes = list(walk(media))

		self.assertIn('has-stack', props(rootCard).get('className', ''))
		self.assertIn('sim-card-header', props(decision).get('className', ''))
		self.assertEqual(props(selection).get('data-group-id'), '7')
		self.assertEqual(props(selection).get('data-stack-id'), 'stack-a')
		self.assertEqual(props(cover).get('children'), 'Set cover')
		self.assertTrue(any(props(node).get('className') == 'view sim-card-media-frame' for node in mediaNodes))
		self.assertTrue(any(props(node).get('className') == 'sim-card-media-badges' for node in mediaNodes))
		self.assertTrue(any(props(node).get('className') == 'sim-card-media-facts' for node in mediaNodes))
		self.assertFalse(any(props(node).get('className') in {'LT', 'RT', 'LB', 'RB'} for node in mediaNodes))
		self.assertFalse(any(props(node).get('data-tip-id') for node in mediaNodes))


if __name__ == '__main__':
	unittest.main()
