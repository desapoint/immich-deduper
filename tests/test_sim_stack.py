#!/usr/bin/env python3

import os
import sys
import unittest
from types import SimpleNamespace

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from sim_stack import buildPlan


def asset(autoId: int, groupId: int, ownerId: str = 'owner-a'):
	return SimpleNamespace(
		autoId=autoId,
		id=f'asset-{autoId}',
		ownerId=ownerId,
		vw=SimpleNamespace(muodId=groupId),
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

		with self.assertRaisesRegex(ValueError, 'at least two selected assets'):
			buildPlan(assets, [1, 2], multiMode=True)

	def test_single_mode_keeps_the_display_as_one_group(self):
		assets = [asset(1, 10), asset(2, 20), asset(3, 30)]

		plan = buildPlan(assets, [1, 2], multiMode=False, targetGroupId=10)

		self.assertEqual([group.groupId for group in plan.groups], [10])
		self.assertEqual([a.autoId for a in plan.others], [3])


if __name__ == '__main__':
	unittest.main()
