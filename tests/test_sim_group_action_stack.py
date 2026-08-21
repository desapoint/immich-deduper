#!/usr/bin/env python3

import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import dash

dash.Dash(__name__, use_pages=True, pages_folder='')

from mod import models
from pages import similar


def asset(autoId: int, groupId: int):
	item = models.Asset(
		autoId=autoId,
		id=f'asset-{autoId}',
		ownerId='owner-a',
		ex=models.AssetExInfo(),
	)
	item.vw.muodId = groupId
	return item


def store(assets, currentSelectedIds, targetGroupId=1, **args):
	taskArgs = {'targetGroupId': targetGroupId, **args}
	return models.ITaskStore(
		nfy=models.Nfy(),
		now=models.Now(sim=models.PgSim(assCur=list(assets))),
		cnt=models.Cnt(),
		tsk=models.Tsk(args=taskArgs),
		ste=models.Ste(cntTotal=len(assets), selectedIds=list(currentSelectedIds)),
	)


TEST_DTO = SimpleNamespace(
	muod=SimpleNamespace(on=True),
	mrg=SimpleNamespace(on=False),
	autoNext=False,
)


class TestManualGroupResolution(unittest.TestCase):
	def test_group_delete_selected_keeps_survivors_open(self):
		assets = [asset(1, 1), asset(2, 1), asset(3, 2)]
		sto = store(assets, [1])

		with (
			patch.object(similar.db, 'dto', TEST_DTO),
			patch.object(similar.psql, 'mkConn'),
			patch.object(similar.immich, 'trashByAssets'),
			patch.object(similar.db.pics, 'deleteBy'),
			patch.object(similar.db.pics, 'setResolveBy') as setResolved,
		):
			similar.sim_SelectedDelete(lambda *_: None, sto)

		self.assertEqual([item.autoId for item in sto.now.sim.assCur], [2, 3])
		setResolved.assert_not_called()

	def test_group_keep_selected_keeps_survivors_open(self):
		assets = [asset(1, 1), asset(2, 1), asset(3, 2)]
		sto = store(assets, [1])

		with (
			patch.object(similar.db, 'dto', TEST_DTO),
			patch.object(similar.psql, 'mkConn'),
			patch.object(similar.immich, 'trashByAssets'),
			patch.object(similar.db.pics, 'deleteBy'),
			patch.object(similar.db.pics, 'setResolveBy') as setResolved,
		):
			similar.sim_SelectedResolve(lambda *_: None, sto)

		self.assertEqual([item.autoId for item in sto.now.sim.assCur], [1, 3])
		setResolved.assert_not_called()

	def test_group_stack_stays_open_when_all_images_share_the_new_stack(self):
		assets = [asset(1, 1), asset(2, 1), asset(3, 2)]
		sto = store(
			assets,
			[1, 2],
			selectedIds=[1, 2],
			coverIds=[],
			deleteOthers=False,
		)

		with (
			patch.object(similar.db, 'dto', TEST_DTO),
			patch.object(similar.psql, 'mkConn'),
			patch.object(
				similar.immich,
				'stackByAssetsPreferApi',
				return_value=('stack-a', 'api', ['asset-1', 'asset-2'], 'asset-1'),
			),
			patch.object(similar.db.pics, 'setResolveBy') as setResolved,
		):
			similar.sim_StackSelected(lambda *_: None, sto)

		self.assertEqual([item.autoId for item in sto.now.sim.assCur], [1, 2, 3])
		self.assertEqual(sto.ste.selectedIds, [])
		self.assertEqual([item.ex.stackId for item in sto.now.sim.assCur[:2]], ['stack-a', 'stack-a'])
		setResolved.assert_not_called()

	def test_group_stack_with_delete_remaining_keeps_stack_open(self):
		assets = [asset(1, 1), asset(2, 1), asset(3, 1), asset(4, 2)]
		sto = store(
			assets,
			[1, 2],
			selectedIds=[1, 2],
			coverIds=[],
			deleteOthers=True,
		)

		with (
			patch.object(similar.db, 'dto', TEST_DTO),
			patch.object(similar.psql, 'mkConn'),
			patch.object(
				similar.immich,
				'stackByAssetsPreferApi',
				return_value=('stack-a', 'api', ['asset-1', 'asset-2'], 'asset-1'),
			),
			patch.object(similar.immich, 'trashByAssets'),
			patch.object(similar.db.pics, 'deleteBy') as deleteBy,
			patch.object(similar.db.pics, 'setResolveBy') as setResolved,
		):
			similar.sim_StackSelected(lambda *_: None, sto)

		self.assertEqual([item.autoId for item in sto.now.sim.assCur], [1, 2, 4])
		self.assertEqual([item.autoId for item in deleteBy.call_args.args[0]], [3])
		setResolved.assert_not_called()

	def test_mark_resolved_removes_only_the_requested_group(self):
		assets = [asset(1, 1), asset(2, 1), asset(3, 2)]
		sto = store(assets, [])

		with (
			patch.object(similar.db, 'dto', TEST_DTO),
			patch.object(similar.db.pics, 'setResolveBy') as setResolved,
		):
			similar.sim_AllResolve(lambda *_: None, sto)

		self.assertEqual([item.autoId for item in sto.now.sim.assCur], [3])
		setResolved.assert_called_once()
		self.assertEqual([item.autoId for item in setResolved.call_args.args[0]], [1, 2])


if __name__ == '__main__':
	unittest.main()
