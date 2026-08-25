#!/usr/bin/env python3

import os
import sys
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from mod import models
from ui import gv


def asset(auto_id: int, group_id: int):
	item = models.Asset(
		autoId=auto_id,
		id=f'asset-{auto_id}',
		ownerId='owner-a',
		originalFileName=f'{auto_id}.jpg',
		originalPath=f'/library/{auto_id}.jpg',
		jsonExif=models.AssetExif(exifImageWidth=100, exifImageHeight=100),
		ex=models.AssetExInfo(),
	)
	item.vw.muodId = group_id
	return item


def props(node):
	return node.to_plotly_json().get('props', {})


class TestSimilarRenderKeys(unittest.TestCase):
	def test_group_container_has_stable_group_key(self):
		container = gv.mkGroupContainer(42, [asset(1, 42), asset(2, 42)])
		self.assertEqual(props(container).get('key'), 'sim-group-42')

	def test_group_card_rows_have_stable_asset_keys(self):
		container = gv.mkGroupContainer(42, [asset(10, 42), asset(11, 42)])
		card_list = container.children[1]
		self.assertEqual(
			[props(row).get('key') for row in card_list.children],
			['sim-asset-10', 'sim-asset-11'],
		)

	def test_group_keys_do_not_depend_on_list_position(self):
		first = gv.mkGrdGrps([asset(1, 10), asset(2, 20), asset(3, 30)])
		second = gv.mkGrdGrps([asset(1, 10), asset(3, 30)])

		self.assertEqual(
			[props(group).get('key') for group in first.children],
			['sim-group-10', 'sim-group-20', 'sim-group-30'],
		)
		self.assertEqual(
			[props(group).get('key') for group in second.children],
			['sim-group-10', 'sim-group-30'],
		)


if __name__ == '__main__':
	unittest.main()
