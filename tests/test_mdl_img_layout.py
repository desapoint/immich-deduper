#!/usr/bin/env python3

import os
import sys
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from mod import mdlImg


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


class TestImageViewerLayout(unittest.TestCase):
	def test_viewer_exposes_clear_controls_and_accessible_navigation(self):
		nodes = list(walk(mdlImg.render()))
		byId = {props(node).get('id'): node for node in nodes if isinstance(props(node).get('id'), str)}

		self.assertIn('img-viewer-title', props(next(node for node in nodes if 'img-viewer-title' in str(props(node).get('className', '')))).get('className'))
		self.assertEqual(props(byId[mdlImg.k.btnMode]).get('children'), 'Fit screen')
		self.assertEqual(props(byId[mdlImg.k.btnSelect]).get('children'), 'Select image')
		self.assertEqual(props(byId[mdlImg.k.btnHelp]).get('children'), 'Shortcuts')
		self.assertEqual(props(byId[mdlImg.k.btnInfo]).get('children'), 'Details')
		self.assertEqual(props(byId[mdlImg.k.btnPrev]).get('aria-label'), 'Previous image')
		self.assertEqual(props(byId[mdlImg.k.btnNext]).get('aria-label'), 'Next image')
		self.assertFalse(props(byId[mdlImg.k.btnMode]).get('outline'))
		self.assertFalse(props(byId[mdlImg.k.btnHelp]).get('outline'))
		self.assertFalse(props(byId[mdlImg.k.btnInfo]).get('outline'))
		self.assertIn('img-viewer-stage', props(byId[mdlImg.k.content]).get('className'))
		self.assertIn('img-viewer-nav', props(byId[mdlImg.k.btnPrev]).get('className'))
		self.assertIn('img-viewer-nav', props(byId[mdlImg.k.btnNext]).get('className'))
		self.assertIn('img-viewer-side-host', props(byId[mdlImg.k.floatL]).get('className'))


if __name__ == '__main__':
	unittest.main()
