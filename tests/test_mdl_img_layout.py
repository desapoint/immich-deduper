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
		main = next(node for node in nodes if props(node).get('className') == 'img-viewer-main')
		footer = next(node for node in nodes if props(node).get('className') == 'img-viewer-footer')
		media = next(node for node in nodes if props(node).get('className') == 'img-viewer-media')
		mainIds = {props(node).get('id') for node in walk(main)}
		footerIds = {props(node).get('id') for node in walk(footer)}

		self.assertIn('img-viewer-title', props(next(node for node in nodes if 'img-viewer-title' in str(props(node).get('className', '')))).get('className'))
		self.assertEqual(props(byId[mdlImg.k.btnSelect]).get('children'), 'Select image')
		self.assertEqual(props(byId[mdlImg.k.btnPrev]).get('aria-label'), 'Previous image')
		self.assertEqual(props(byId[mdlImg.k.btnNext]).get('aria-label'), 'Next image')
		self.assertEqual(props(byId[mdlImg.k.btnHelp]).get('title'), 'Show or hide keyboard shortcuts')
		self.assertEqual(props(byId[mdlImg.k.btnInfo]).get('title'), 'Show or hide image details')
		self.assertFalse(props(byId[mdlImg.k.btnMode]).get('outline'))
		self.assertFalse(props(byId[mdlImg.k.btnHelp]).get('outline'))
		self.assertFalse(props(byId[mdlImg.k.btnInfo]).get('outline'))
		self.assertIn('img-viewer-stage', props(byId[mdlImg.k.content]).get('className'))
		self.assertEqual(props(byId[mdlImg.k.status]).get('className'), 'viewer-asset-status')
		self.assertIn('img-viewer-nav', props(byId[mdlImg.k.btnPrev]).get('className'))
		self.assertIn('img-viewer-nav', props(byId[mdlImg.k.btnNext]).get('className'))
		self.assertNotIn('position-fixed', props(byId[mdlImg.k.btnPrev]).get('className'))
		self.assertTrue(any(props(node).get('className') == 'img-viewer-header-actions' for node in nodes))
		self.assertTrue(any(props(node).get('className') == 'img-viewer-header' for node in nodes))
		self.assertTrue(any(props(node).get('className') == 'img-viewer-main' for node in nodes))
		self.assertTrue(any(props(node).get('className') == 'img-viewer-footer' for node in nodes))
		self.assertTrue(any(props(node).get('className') == 'img-viewer-header-action img-viewer-info-action' for node in nodes))
		self.assertTrue(any(props(node).get('className') == 'img-viewer-header-action img-viewer-help-action' for node in nodes))
		self.assertTrue(any(props(node).get('className') == 'img-viewer-content' for node in nodes))
		self.assertEqual(len([node for node in nodes if 'img-viewer-nav-zone' in str(props(node).get('className', ''))]), 2)
		self.assertIn(mdlImg.k.content, {props(node).get('id') for node in walk(media)})
		self.assertIn(mdlImg.k.btnSelect, mainIds)
		self.assertNotIn(mdlImg.k.btnSelect, footerIds)
		self.assertIn(mdlImg.k.status, footerIds)
		self.assertEqual(props(byId[mdlImg.k.imgHelp]).get('className'), 'help hide')
		self.assertEqual(props(byId[mdlImg.k.imgInfo]).get('className'), 'info hide')
		self.assertFalse(props(byId[mdlImg.k.modal]).get('fullscreen', False))


if __name__ == '__main__':
	unittest.main()
