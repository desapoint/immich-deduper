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
from ui import gv


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
	def button_states(self, assets, selectedIds=(), *, cnt=None, task=None, groupButtons=None, groupActions=None, coverButtons=None, triggeredId='store-now'):
		with (
			patch.object(similar, 'ctx', SimpleNamespace(triggered_id=triggeredId)),
			patch.object(similar.db, 'dto', TEST_DTO),
			patch.object(similar.db.pics, 'countHasSimIds', return_value=0),
		):
			return similar.sim_UpdateButtons(
				models.Now(sim=models.PgSim(assCur=list(assets))).toDict(),
				(cnt or models.Cnt()).toDict(),
				(task or models.Tsk()).toDict(),
				models.Ste(cntTotal=len(assets), selectedIds=list(selectedIds)).toDict(),
				groupButtons or [], groupActions or [], coverButtons or [],
			)

	def test_group_action_confirmation_offers_mark_resolved(self):
		assets = [asset(1, 1), asset(2, 1), asset(3, 2)]
		now = models.Now(sim=models.PgSim(assCur=assets))
		ste = models.Ste(cntTotal=3, selectedIds=[1])
		trigger = {'type': gv.GROUP_ACTION_BUTTON, 'action': gv.GROUP_KEEP_SELECTED, 'id': 1}

		with (
			patch.object(similar, 'ctx', SimpleNamespace(triggered=[{'value': [1]}])),
			patch.object(similar, 'getTrgId', return_value=trigger),
			patch.object(similar.db, 'dto', TEST_DTO),
		):
			result = similar.sim_RunModal(
				0, 0, 0, 0, 0, 0, 0, 0, [], [1],
				now.toDict(), models.Cnt().toDict(), models.Mdl().toDict(), models.Tsk().toDict(),
				models.Nfy().toDict(), ste.toDict(),
				False, False, False, False, False, [], [],
			)

		modal = models.Mdl.fromDic(result[2])
		self.assertTrue(modal.args['allowMarkResolved'])
		self.assertEqual(modal.args['targetGroupId'], 1)

	def test_selection_state_reconciles_group_buttons_without_being_a_callback_input(self):
		assets = [asset(1, 1), asset(2, 1), asset(3, 2)]
		now = models.Now(sim=models.PgSim(assCur=assets))
		ste = models.Ste(cntTotal=3, selectedIds=[1])
		groupButtons = [{'type': gv.STACK_GROUP_BUTTON, 'id': 1}, {'type': gv.STACK_GROUP_BUTTON, 'id': 2}]
		groupActions = [
			{'type': gv.GROUP_ACTION_BUTTON, 'action': gv.GROUP_KEEP_SELECTED, 'id': 1},
			{'type': gv.GROUP_ACTION_BUTTON, 'action': gv.GROUP_KEEP_SELECTED, 'id': 2},
			{'type': gv.GROUP_ACTION_BUTTON, 'action': gv.GROUP_MARK_RESOLVED, 'id': 2},
		]

		with (
			patch.object(similar.db, 'dto', TEST_DTO),
			patch.object(similar.db.pics, 'countHasSimIds', return_value=0),
		):
			result = similar.sim_UpdateButtons(
				now.toDict(), models.Cnt().toDict(), models.Tsk().toDict(), ste.toDict(),
				groupButtons, groupActions, [],
			)

		self.assertEqual(len(result), 14)
		self.assertEqual(result[5:9], (False, False, False, False))
		self.assertEqual(result[9], [False, True])
		self.assertEqual(result[10], [False, True, False])
		self.assertEqual(result[11:14], ([], [], []))

	def test_action_buttons_follow_empty_partial_and_running_states(self):
		assets = [asset(1, 1), asset(2, 1), asset(3, 2)]
		groupButtons = [
			{'type': gv.STACK_GROUP_BUTTON, 'id': 1},
			{'type': gv.STACK_GROUP_BUTTON, 'id': 2},
		]
		groupActions = [
			{'type': gv.GROUP_ACTION_BUTTON, 'action': gv.GROUP_KEEP_SELECTED, 'id': 1},
			{'type': gv.GROUP_ACTION_BUTTON, 'action': gv.GROUP_DELETE_SELECTED, 'id': 2},
			{'type': gv.GROUP_ACTION_BUTTON, 'action': gv.GROUP_MARK_RESOLVED, 'id': 2},
		]
		coverButtons = [
			{'type': gv.STACK_COVER_BUTTON, 'id': 1, 'group': 1, 'owner': 'owner-a'},
		]

		empty = self.button_states(
			assets, groupButtons=groupButtons, groupActions=groupActions, coverButtons=coverButtons,
		)
		self.assertEqual(empty[3:9], (False, False, True, True, True, False))
		self.assertEqual(empty[9], [True, True])
		self.assertEqual(empty[10], [True, True, False])
		self.assertEqual(empty[11:14], ([True], ['Set cover'], [False]))

		partial = self.button_states(
			assets, [1], groupButtons=groupButtons, groupActions=groupActions, coverButtons=coverButtons,
		)
		self.assertEqual(partial[3:9], (False, False, False, False, False, False))
		self.assertEqual(partial[9], [False, True])
		self.assertEqual(partial[10], [False, True, False])

		running = self.button_states(
			assets, [1], task=models.Tsk(id='task-1', cmd='running'),
			groupButtons=groupButtons, groupActions=groupActions, coverButtons=coverButtons,
		)
		self.assertEqual(running[3:8], (True, True, True, True, True))
		self.assertEqual(running[9], [True, True])
		self.assertEqual(running[10], [True, True, True])
		self.assertEqual(running[13], [True])

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

	def test_group_delete_selected_can_resolve_survivors_in_one_action(self):
		assets = [asset(1, 1), asset(2, 1), asset(3, 2)]
		sto = store(assets, [1], markResolved=True)

		with (
			patch.object(similar.db, 'dto', TEST_DTO),
			patch.object(similar.psql, 'mkConn'),
			patch.object(similar.immich, 'trashByAssets'),
			patch.object(similar.db.pics, 'deleteBy'),
			patch.object(similar.db.pics, 'setResolveBy') as setResolved,
		):
			similar.sim_SelectedDelete(lambda *_: None, sto)

		self.assertEqual([item.autoId for item in sto.now.sim.assCur], [3])
		self.assertEqual([item.autoId for item in setResolved.call_args.args[0]], [2])

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

	def test_group_keep_selected_can_resolve_kept_images_in_one_action(self):
		assets = [asset(1, 1), asset(2, 1), asset(3, 2)]
		sto = store(assets, [1], markResolved=True)

		with (
			patch.object(similar.db, 'dto', TEST_DTO),
			patch.object(similar.psql, 'mkConn'),
			patch.object(similar.immich, 'trashByAssets'),
			patch.object(similar.db.pics, 'deleteBy'),
			patch.object(similar.db.pics, 'setResolveBy') as setResolved,
		):
			similar.sim_SelectedResolve(lambda *_: None, sto)

		self.assertEqual([item.autoId for item in sto.now.sim.assCur], [3])
		self.assertEqual([item.autoId for item in setResolved.call_args.args[0]], [1])

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

	def test_group_stack_can_resolve_the_group_in_one_action(self):
		assets = [asset(1, 1), asset(2, 1), asset(3, 2)]
		sto = store(
			assets,
			[1, 2],
			selectedIds=[1, 2],
			coverIds=[],
			deleteOthers=False,
			markResolved=True,
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

		self.assertEqual([item.autoId for item in sto.now.sim.assCur], [3])
		self.assertEqual([item.autoId for item in setResolved.call_args.args[0]], [1, 2])

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
