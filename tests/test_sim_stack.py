#!/usr/bin/env python3

import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from sim_stack import (
	applyStackMetadata,
	assetsForGroup,
	buildPlan,
	commonStackId,
	fullyStackedGroupAssets,
	orderExistingStackIds,
	removeHandled,
	splitUnselectedByStackMembership,
)
from db import sim as db_sim


def asset(
	autoId: int,
	groupId: int,
	ownerId: str = 'owner-a',
	stackId: str | None = None,
	stackPrimaryAssetId: str | None = None,
):
	return SimpleNamespace(
		autoId=autoId,
		id=f'asset-{autoId}',
		ownerId=ownerId,
		vw=SimpleNamespace(muodId=groupId),
		ex=SimpleNamespace(
			stackId=stackId,
			stackPrimaryAssetId=stackPrimaryAssetId,
			stackAssets=[],
		),
	)


class TestStackPlan(unittest.TestCase):
	def test_global_selection_is_stacked_per_visual_group(self):
		assets = [
			asset(1, 1), asset(2, 1), asset(3, 1),
			asset(4, 2), asset(5, 2),
			asset(6, 3), asset(7, 3),
		]

		plan = buildPlan(assets, [1, 2, 4, 5], multiMode=True)

		self.assertEqual([group.groupId for group in plan.groups], [1, 2])
		self.assertEqual([[a.autoId for a in stack.assets] for stack in plan.stacks], [[1, 2], [4, 5]])
		self.assertEqual([a.autoId for a in plan.others], [3])
		self.assertEqual([a.autoId for a in plan.assets], [1, 2, 3, 4, 5])

	def test_group_action_ignores_selections_in_other_groups(self):
		assets = [asset(1, 1), asset(2, 1), asset(3, 2), asset(4, 2)]

		plan = buildPlan(assets, [1, 2, 3, 4], multiMode=True, targetGroupId=1)

		self.assertEqual(len(plan.groups), 1)
		self.assertEqual([a.autoId for a in plan.selected], [1, 2])

	def test_group_actions_scope_assets_to_the_requested_group(self):
		assets = [asset(1, 1), asset(2, 1), asset(3, 2), asset(4, 2)]

		group = assetsForGroup(assets, multiMode=True, targetGroupId='2')

		self.assertEqual([a.autoId for a in group], [3, 4])

	def test_group_actions_reject_a_stale_group(self):
		with self.assertRaisesRegex(ValueError, 'no longer available'):
			assetsForGroup([asset(1, 1), asset(2, 1)], multiMode=True, targetGroupId=2)

	def test_handled_group_is_removed_without_clearing_other_groups(self):
		assets = [asset(1, 1), asset(2, 1), asset(3, 2), asset(4, 2)]
		remaining, selected = removeHandled(assets, [1, 3, 4], assetsForGroup(assets, True, 1))

		self.assertEqual([a.autoId for a in remaining], [3, 4])
		self.assertEqual(selected, [3, 4])

	def test_existing_stack_of_first_selected_asset_is_reused(self):
		ordered = orderExistingStackIds(
			['asset-1', 'asset-2'],
			{'asset-1': 'stack-b', 'asset-2': 'stack-a'},
			{},
		)

		self.assertEqual(ordered, ['stack-b', 'stack-a'])

	def test_primary_stack_references_are_also_consolidated(self):
		ordered = orderExistingStackIds(
			['asset-1', 'asset-2'],
			{'asset-2': 'stack-c'},
			{'asset-1': ['stack-b', 'stack-a']},
		)

		self.assertEqual(ordered, ['stack-a', 'stack-b', 'stack-c'])

	def test_delete_others_preserves_inherited_stack_members(self):
		unselected = [asset(1, 1), asset(2, 1), asset(3, 1)]

		deletable, protected = splitUnselectedByStackMembership(
			unselected,
			{'asset-2'},
		)

		self.assertEqual([a.autoId for a in deletable], [1, 3])
		self.assertEqual([a.autoId for a in protected], [2])

	def test_new_stack_metadata_marks_members_and_thumbnail(self):
		assets = [asset(1, 1), asset(2, 1), asset(3, 1)]

		applyStackMetadata(assets, [('stack-a', 'asset-2', ['asset-1', 'asset-2'])])

		self.assertEqual(assets[0].ex.stackId, 'stack-a')
		self.assertEqual(assets[1].ex.stackPrimaryAssetId, 'asset-2')
		self.assertIsNone(assets[2].ex.stackId)

	def test_group_is_complete_only_when_every_asset_uses_the_same_stack(self):
		assets = [asset(1, 1, stackId='stack-a'), asset(2, 1, stackId='stack-a')]
		plan = buildPlan(assets, [1, 2], multiMode=True)

		resolved, groupIds = fullyStackedGroupAssets(plan)

		self.assertEqual(commonStackId(assets), 'stack-a')
		self.assertEqual([item.autoId for item in resolved], [1, 2])
		self.assertEqual(groupIds, [1])

	def test_group_with_multiple_stacks_remains_open(self):
		assets = [asset(1, 1, stackId='stack-a'), asset(2, 1, stackId='stack-b')]
		plan = buildPlan(assets, [1, 2], multiMode=True)

		resolved, groupIds = fullyStackedGroupAssets(plan)

		self.assertIsNone(commonStackId(assets))
		self.assertEqual(resolved, [])
		self.assertEqual(groupIds, [])

	def test_search_skips_and_resolves_a_same_stack_only_group(self):
		source = asset(1, 1, stackId='stack-a')
		members = [source, asset(2, 1, stackId='stack-a')]
		group = db_sim.SearchInfo(asset=source, assets=members)

		with (
			patch.object(db_sim.db.vecs, 'findSimiliar', return_value={1: [SimpleNamespace()]}),
			patch.object(db_sim, 'findGroupBy', return_value=group),
			patch.object(db_sim.db.pics, 'setResolveBy') as setResolved,
		):
			result = db_sim.searchBy(source, lambda *_: None, lambda: False, fromUrl=True)

		self.assertEqual(result.groups, [])
		setResolved.assert_called_once_with(members)

	def test_selected_assets_are_partitioned_by_owner(self):
		assets = [
			asset(1, 1, 'owner-a'), asset(2, 1, 'owner-a'),
			asset(3, 1, 'owner-b'), asset(4, 1, 'owner-b'),
		]

		plan = buildPlan(assets, [1, 2, 3, 4], multiMode=True)

		self.assertEqual(len(plan.groups), 1)
		self.assertEqual([stack.ownerId for stack in plan.stacks], ['owner-a', 'owner-b'])
		self.assertEqual([[a.autoId for a in stack.assets] for stack in plan.stacks], [[1, 2], [3, 4]])

	def test_each_owner_needs_two_selected_assets(self):
		assets = [asset(1, 1, 'owner-a'), asset(2, 1, 'owner-b')]

		with self.assertRaisesRegex(ValueError, 'at least two selected images'):
			buildPlan(assets, [1, 2], multiMode=True)

	def test_single_selection_reports_that_stacking_requires_two_images(self):
		with self.assertRaisesRegex(ValueError, 'Stacking requires at least two selected images'):
			buildPlan([asset(1, 1), asset(2, 1)], [1], multiMode=True)

	def test_chosen_cover_becomes_stack_primary(self):
		plan = buildPlan(
			[asset(1, 1), asset(2, 1)],
			[1, 2],
			multiMode=True,
			coverIds=[2],
		)

		self.assertEqual(plan.coverIds, [2])
		self.assertEqual(plan.stacks[0].primary.autoId, 2)

	def test_single_mode_keeps_the_display_as_one_group(self):
		assets = [asset(1, 10), asset(2, 20), asset(3, 30)]

		plan = buildPlan(assets, [1, 2], multiMode=False, targetGroupId=10)

		self.assertEqual([group.groupId for group in plan.groups], [10])
		self.assertEqual([a.autoId for a in plan.others], [3])


if __name__ == '__main__':
	unittest.main()
