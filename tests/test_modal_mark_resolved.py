#!/usr/bin/env python3

import os
import sys
import unittest
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from conf import ks
from mod import mdl, models


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


class TestModalMarkResolved(unittest.TestCase):
	def test_modal_renders_combined_confirmation_button(self):
		nodes = list(walk(mdl.render()))
		button = next(node for node in nodes if props(node).get('id') == mdl.k.btnOkResolve)

		self.assertEqual(props(button).get('children'), 'Confirm & mark resolved')
		self.assertEqual(props(button).get('style'), {'display': 'none'})

	def test_status_shows_combined_confirmation_only_when_allowed(self):
		gws = models.Gws(dtc=1).toDict()
		nfy = models.Nfy().toDict()
		allowed = models.Mdl(id=str(ks.pg.similar), args={'allowMarkResolved': True}).toDict()
		normal = models.Mdl(id=str(ks.pg.similar)).toDict()

		self.assertEqual(mdl.mdl_Status(allowed, nfy, gws)[2], {})
		self.assertEqual(mdl.mdl_Status(normal, nfy, gws)[2], {'display': 'none'})

	def test_combined_confirmation_creates_a_mark_resolved_task(self):
		model = models.Mdl(
			id=ks.pg.similar,
			cmd=ks.cmd.sim.selOk,
			args={'targetGroupId': 7, 'allowMarkResolved': True},
		)

		with patch.object(mdl, 'getTrgId', return_value=mdl.k.btnOkResolve):
			result = mdl.mdl_OnClick(0, 1, 0, model.toDict(), models.Nfy().toDict())

		task = models.Tsk.fromDic(result[2])
		self.assertEqual(task.args['targetGroupId'], 7)
		self.assertTrue(task.args['markResolved'])
		self.assertNotIn('allowMarkResolved', task.args)

	def test_normal_confirmation_keeps_the_group_open(self):
		model = models.Mdl(
			id=ks.pg.similar,
			cmd=ks.cmd.sim.selOk,
			args={'targetGroupId': 7, 'allowMarkResolved': True},
		)

		with patch.object(mdl, 'getTrgId', return_value=mdl.k.btnOk):
			result = mdl.mdl_OnClick(1, 0, 0, model.toDict(), models.Nfy().toDict())

		task = models.Tsk.fromDic(result[2])
		self.assertNotIn('markResolved', task.args)
		self.assertNotIn('allowMarkResolved', task.args)


if __name__ == '__main__':
	unittest.main()
