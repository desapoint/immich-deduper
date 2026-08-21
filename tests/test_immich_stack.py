#!/usr/bin/env python3

import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import immich
from conf import ks


def asset(assetId: str, ownerId: str = 'owner-a'):
	return SimpleNamespace(id=assetId, ownerId=ownerId)


class StackCursor:
	def __init__(self, selectedRows, stackRows, memberRows):
		self.selectedRows = selectedRows
		self.stackRows = stackRows
		self.memberRows = memberRows
		self.currentRows = []
		self.rowcount = 0
		self.calls = []

	def execute(self, query, params=()):
		query = str(query)
		self.calls.append((query, params))
		normalized = ' '.join(query.lower().split())
		if 'select id, "ownerid", status, "deletedat", "stackid"' in normalized:
			self.currentRows = self.selectedRows
		elif 'select id, "primaryassetid", "ownerid"' in normalized:
			self.currentRows = self.stackRows
		elif 'select id, "ownerid", status, "deletedat"' in normalized:
			self.currentRows = self.memberRows
		elif normalized.startswith('update asset'):
			self.rowcount = len(params[1])
		elif normalized.startswith('delete from stack'):
			self.rowcount = len(params[0])
		elif normalized.startswith('update stack'):
			self.rowcount = 1
		else:
			raise AssertionError(f'Unexpected SQL: {normalized}')

	def fetchall(self):
		return self.currentRows


class TestExistingStackReuse(unittest.TestCase):
	def test_multiple_existing_stacks_are_consolidated_into_first_selected_stack(self):
		active = ks.db.status.active
		cur = StackCursor(
			selectedRows=[
				('asset-1', 'owner-a', active, None, 'stack-b'),
				('asset-2', 'owner-a', active, None, 'stack-a'),
			],
			stackRows=[
				('stack-a', 'asset-2', 'owner-a'),
				('stack-b', 'asset-1', 'owner-a'),
			],
			memberRows=[
				('asset-1', 'owner-a', active, None),
				('asset-b-extra', 'owner-a', active, None),
				('asset-2', 'owner-a', active, None),
				('asset-a-extra', 'owner-a', active, None),
			],
		)

		stackId, memberIds = immich.stackByAssets([asset('asset-1'), asset('asset-2')], cur)

		self.assertEqual(stackId, 'stack-b')
		self.assertEqual(memberIds, ['asset-1', 'asset-2', 'asset-b-extra', 'asset-a-extra'])
		deleteCall = next(call for call in cur.calls if call[0].strip().lower().startswith('delete from stack'))
		self.assertEqual(deleteCall[1], (['stack-a'],))
		updateStackCall = next(call for call in cur.calls if call[0].strip().lower().startswith('update stack'))
		self.assertEqual(updateStackCall[1], ('asset-1', 'stack-b', 'owner-a'))

	def test_missing_referenced_stack_aborts_consolidation(self):
		active = ks.db.status.active
		cur = StackCursor(
			selectedRows=[
				('asset-1', 'owner-a', active, None, 'missing-stack'),
				('asset-2', 'owner-a', active, None, None),
			],
			stackRows=[],
			memberRows=[],
		)

		with self.assertRaisesRegex(RuntimeError, 'reference missing stacks'):
			immich.stackByAssets([asset('asset-1'), asset('asset-2')], cur)

	def test_reused_stack_keeps_its_existing_cover(self):
		active = ks.db.status.active
		cur = StackCursor(
			selectedRows=[
				('asset-1', 'owner-a', active, None, 'stack-a'),
				('asset-2', 'owner-a', active, None, None),
			],
			stackRows=[('stack-a', 'cover-a', 'owner-a')],
			memberRows=[
				('cover-a', 'owner-a', active, None),
				('asset-1', 'owner-a', active, None),
			],
		)

		stackId, memberIds = immich.stackByAssets([asset('asset-1'), asset('asset-2')], cur)

		self.assertEqual(stackId, 'stack-a')
		self.assertEqual(memberIds, ['asset-1', 'asset-2', 'cover-a'])
		updateStackCall = next(call for call in cur.calls if call[0].strip().lower().startswith('update stack'))
		self.assertEqual(updateStackCall[1], ('cover-a', 'stack-a', 'owner-a'))

	def test_explicit_cover_replaces_the_reused_stack_cover(self):
		active = ks.db.status.active
		cur = StackCursor(
			selectedRows=[
				('asset-1', 'owner-a', active, None, 'stack-a'),
				('asset-2', 'owner-a', active, None, None),
			],
			stackRows=[('stack-a', 'cover-a', 'owner-a')],
			memberRows=[
				('cover-a', 'owner-a', active, None),
				('asset-1', 'owner-a', active, None),
			],
		)

		stackId, _ = immich.stackByAssets(
			[asset('asset-1'), asset('asset-2')],
			cur,
			preferredPrimaryId='asset-2',
		)

		self.assertEqual(stackId, 'stack-a')
		updateStackCall = next(call for call in cur.calls if call[0].strip().lower().startswith('update stack'))
		self.assertEqual(updateStackCall[1], ('asset-2', 'stack-a', 'owner-a'))

	def test_existing_stack_skips_api_creation(self):
		assets = [asset('asset-1'), asset('asset-2')]
		with (
			patch.object(immich, '_hasExistingStack', return_value=True),
			patch.object(immich, 'stackByAssets', return_value=('stack-a', ['asset-1', 'asset-2'])),
			patch.object(immich.api, 'stackAssets') as apiCreate,
		):
			result = immich.stackByAssetsPreferApi(assets, object())

		self.assertEqual(result, ('stack-a', 'database', ['asset-1', 'asset-2']))
		apiCreate.assert_not_called()

	def test_fresh_stack_uses_api_first(self):
		assets = [asset('asset-1'), asset('asset-2')]
		with (
			patch.object(immich, '_hasExistingStack', return_value=False),
			patch.object(immich.api, 'stackAssets', return_value='stack-new') as apiCreate,
			patch.object(immich, '_stackMemberIds', return_value=['asset-1', 'asset-2']),
			patch.object(immich, 'stackByAssets') as directCreate,
		):
			result = immich.stackByAssetsPreferApi(assets, object())

		self.assertEqual(result, ('stack-new', 'api', ['asset-1', 'asset-2']))
		apiCreate.assert_called_once_with(['asset-1', 'asset-2'], 'owner-a')
		directCreate.assert_not_called()

	def test_explicit_cover_is_sent_first_to_the_api(self):
		assets = [asset('asset-1'), asset('asset-2')]
		with (
			patch.object(immich, '_hasExistingStack', return_value=False),
			patch.object(immich.api, 'stackAssets', return_value='stack-new') as apiCreate,
			patch.object(immich, '_stackMemberIds', return_value=['asset-1', 'asset-2']),
		):
			immich.stackByAssetsPreferApi(assets, object(), preferredPrimaryId='asset-2')

		apiCreate.assert_called_once_with(['asset-2', 'asset-1'], 'owner-a')


if __name__ == '__main__':
	unittest.main()
