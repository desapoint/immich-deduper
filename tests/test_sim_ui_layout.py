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

	def test_similar_card_has_identity_metadata_and_collapsed_details(self):
		item = asset(4, 8, stackId='stack-b', primary=True)
		item.originalFileName = 'holiday-original-name.jpg'
		item.originalPath = '/external/archive/holiday-stored-name.jpg'
		item.deviceId = 'camera-import'
		item.libId = 'external-library'
		item.type = 'IMAGE'
		item.localDateTime = '2025-07-08T09:10:11'
		item.fileCreatedAt = '2025-07-08T09:11:12Z'
		item.fileModifiedAt = '2025-07-09T10:12:13Z'
		item.isFavorite = 1
		item.jsonExif.dateTimeOriginal = '2025-07-08T09:10:11'
		item.jsonExif.fileSizeInByte = 8192
		item.ex.rating = 4
		item.ex.albs = [models.Album(albumName='Trips')]
		item.ex.tags = [models.Tags(value='beach')]
		item.ex.facs = [models.AssetFace(name='Person')]
		item.ex.description = 'A useful description'
		item.ex.latitude = 45.5
		item.ex.longitude = -73.6

		with patch('ui.cards.db.psql.getUsrName', return_value='Owner Name'):
			card = gv.cards.mk(item, stackGroupId=8)

		nodes = list(walk(card))
		identity = next(node for node in nodes if props(node).get('className') == 'sim-card-identity')
		metadata = next(node for node in nodes if props(node).get('className') == 'sim-card-metadata')
		details = next(node for node in nodes if props(node).get('className') == 'sim-card-details')
		detailRows = [node for node in nodes if props(node).get('className') == 'sim-card-detail-row']
		metaItems = [node for node in walk(metadata) if 'sim-card-meta-item' in str(props(node).get('className', ''))]

		self.assertTrue(any(props(node).get('className') == 'tag sim-card-filename' for node in walk(identity)))
		self.assertTrue(any(getattr(node, 'children', None) == 'holiday-original-name.jpg' for node in walk(identity)))
		self.assertTrue(any(node == 'Owner Name' or getattr(node, 'children', None) == 'Owner Name' for node in walk(identity)))
		self.assertGreaterEqual(len(metaItems), 7)
		self.assertEqual(props(details).get('open'), bool(gv.cards.db.dto.showGridInfo))
		self.assertGreaterEqual(len(detailRows), 10)
		self.assertTrue(any(getattr(node, 'children', None) == 'Full path' for node in nodes))
		self.assertTrue(any(getattr(node, 'children', None) == '/external/archive/holiday-stored-name.jpg' for node in nodes))
		self.assertFalse(any(props(node).get('className') == 'grid grid-info' for node in nodes))

	def test_view_card_retains_legacy_information_layout(self):
		with patch('ui.cards.db.psql.getUsrName', return_value='Owner'):
			card = gv.cards.mk(asset(1, 7), False)

		nodes = list(walk(card))
		self.assertTrue(any(props(node).get('class_name') == 'grid grid-info' for node in nodes))
		self.assertTrue(any(props(node).get('className') == 'tagbox' for node in nodes))
		self.assertFalse(any(props(node).get('className') == 'sim-card-details' for node in nodes))


if __name__ == '__main__':
	unittest.main()
