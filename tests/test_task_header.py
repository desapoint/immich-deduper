#!/usr/bin/env python3

import os
import sys
import unittest
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import dash

dash.Dash(__name__, use_pages=True, pages_folder='')

from mod import models, tsk
from mod.mgr import tskSvc
from ui import nav


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


class TestGlobalTaskStatus(unittest.TestCase):
	def test_header_places_task_status_before_settings(self):
		nodes = list(walk(nav.renderHeader()))
		taskIndex = next(i for i, node in enumerate(nodes) if props(node).get('id') == tsk.k.div)
		settingsIndex = next(
			i for i, node in enumerate(nodes)
			if props(node).get('href') == '/' and 'navLnk' in props(node).get('className', '')
		)
		self.assertLess(taskIndex, settingsIndex)
		self.assertEqual(sum(props(node).get('id') == tsk.k.div for node in nodes), 1)
		self.assertTrue(any(props(node).get('className') == 'global-task-status' for node in nodes))

	def test_page_body_no_longer_repeats_task_status(self):
		nodes = list(walk(nav.renderBody([dash.html.Div('Page')], [])))
		self.assertFalse(any(props(node).get('id') == tsk.k.div for node in nodes))

	def test_task_status_has_compact_idle_and_running_states(self):
		nodes = list(walk(tsk.render()))
		panel = next(node for node in nodes if props(node).get('id') == tsk.k.div)
		progress = next(node for node in nodes if props(node).get('id') == tsk.k.prg)
		cancel = next(node for node in nodes if props(node).get('id') == tsk.k.btnCancel)

		self.assertIn('task-status idle', props(panel).get('className', ''))
		self.assertIn('task-status-progress', props(progress).get('className', ''))
		self.assertTrue(props(cancel).get('disabled'))

		idle = tsk.tsk_PanelStatus(models.Tsk().toDict())
		self.assertEqual(idle, ('tskPanel task-status idle', 'Idle', True))

		runningTask = models.Tsk(id='similar', name='Similar', tsn='task-1')
		running = tsk.tsk_PanelStatus(runningTask.toDict())
		self.assertEqual(running, ('tskPanel task-status running', 'Similar', False))

	def test_completion_resets_header_status_and_preserves_toast(self):
		nfy = models.Nfy()
		resultTask = models.Tsk(id='similar', name='Similar', tsn='task-1')
		result = models.ITaskStore(nfy, models.Now(), models.Cnt(), resultTask, models.Ste())
		nfy.success('Similar completed')
		message = models.Gws.mk(
			'complete', tsn='task-1', ste=models.TskStatus.COMPLETED, msg='Similar completed'
		).toDict()

		with (
			patch.object(tskSvc, 'getResultBy', return_value=result),
			patch.object(models.Cnt, 'mkNewCnt', return_value=models.Cnt()),
		):
			outputs = tsk.tsk_OnData(message, resultTask.toDict())

		self.assertIsNone(outputs[3]['id'])
		self.assertIsNone(outputs[3]['name'])
		self.assertIsNone(outputs[3]['tsn'])
		self.assertEqual(outputs[1]['msgs'][-1]['type'], 'success')
		self.assertEqual(len(outputs[1]['msgs']), 1)
		self.assertEqual(tsk.tsk_OnStatus({'typ': 'complete'}, outputs[3]), True)

	def test_completion_adds_toast_when_task_did_not_create_one(self):
		resultTask = models.Tsk(id='fetch', name='Reset assets', tsn='task-2')
		result = models.ITaskStore(models.Nfy(), models.Now(), models.Cnt(), resultTask, models.Ste())
		message = models.Gws.mk(
			'complete', tsn='task-2', ste=models.TskStatus.COMPLETED, msg='Reset assets completed'
		).toDict()

		with (
			patch.object(tskSvc, 'getResultBy', return_value=result),
			patch.object(models.Cnt, 'mkNewCnt', return_value=models.Cnt()),
		):
			outputs = tsk.tsk_OnData(message, resultTask.toDict())

		self.assertEqual(outputs[1]['msgs'][-1]['message'], 'Reset assets completed')
		self.assertEqual(outputs[1]['msgs'][-1]['type'], 'success')

	def test_failed_completion_uses_existing_task_error_toast(self):
		resultTask = models.Tsk(id='vector', name='Repair index', tsn='task-3')
		result = models.ITaskStore(models.Nfy(), models.Now(), models.Cnt(), resultTask, models.Ste())
		result.nfy.error('Repair failed: unavailable')
		message = models.Gws.mk(
			'complete', tsn='task-3', ste=models.TskStatus.FAILED, msg='Error: Repair failed: unavailable'
		).toDict()

		with (
			patch.object(tskSvc, 'getResultBy', return_value=result),
			patch.object(models.Cnt, 'mkNewCnt', return_value=models.Cnt()),
		):
			outputs = tsk.tsk_OnData(message, resultTask.toDict())

		self.assertEqual(len(outputs[1]['msgs']), 1)
		self.assertEqual(outputs[1]['msgs'][0]['type'], 'danger')


if __name__ == '__main__':
	unittest.main()
