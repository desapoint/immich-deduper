#!/usr/bin/env python3

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class TestGlobalUiFoundation(unittest.TestCase):
	def test_modern_surface_tokens_are_defined(self):
		base = (ROOT / 'src/scss/base.scss').read_text()
		for token in (
			'--ui-bg:', '--ui-surface:', '--ui-border:', '--ui-text:',
			'--ui-accent:', '--ui-radius:', '--ui-shadow:', '--ui-focus:',
		):
			self.assertIn(token, base)

	def test_global_components_share_the_foundation(self):
		main = (ROOT / 'src/scss/main.scss').read_text()
		for selector in (
			'.navbar {', '.navLnk {', '.body-header {', '.card {',
			'.form-control,', '.btn {', '.pager {', '.notify {', '.tskPanel {',
		):
			self.assertIn(selector, main)

	def test_global_layout_has_tablet_and_phone_rules(self):
		main = (ROOT / 'src/scss/main.scss').read_text()
		self.assertIn('@media (max-width: 1100px)', main)
		self.assertIn('@media (max-width: 767px)', main)
		self.assertIn('grid-template-columns: 1fr;', main)

	def test_restrained_controls_remain_visibly_interactive(self):
		main = (ROOT / 'src/scss/main.scss').read_text()
		self.assertIn('background-image: var(--bs-form-check-bg-image) !important;', main)
		self.assertIn('// Restrained application styling', main)
		self.assertIn('opacity: 0.68;', main)

	def test_shared_settings_fields_expand_in_responsive_grids(self):
		main = (ROOT / 'src/scss/main.scss').read_text()
		self.assertIn('// Shared settings grids', main)
		self.assertIn('.auto-select-criteria-grid {', main)
		self.assertIn('grid-template-columns: repeat(2, minmax(0, 1fr));', main)
		self.assertIn('max-width: none !important;', main)
		self.assertIn('.auto-select-field {', main)
		self.assertIn('grid-template-columns: minmax(0, 1fr) clamp(7rem, 36%, 9rem);', main)
		self.assertIn('.auto-select-path-criterion {', main)
		self.assertIn('grid-column: 1 / -1;', main)
		self.assertIn('resize: vertical;', main)

	def test_similar_empty_state_is_compact_and_neutral(self):
		main = (ROOT / 'src/scss/main.scss').read_text()
		self.assertIn('.sim-empty-state {', main)
		self.assertIn('border: 1px dashed var(--ui-border-strong);', main)

	def test_task_progress_and_toasts_stay_in_the_global_header_layer(self):
		main = (ROOT / 'src/scss/main.scss').read_text()
		base = (ROOT / 'src/scss/main.base.scss').read_text()
		self.assertIn('.global-task-status {', main)
		self.assertIn('&.running {', main)
		self.assertIn('&.idle {', main)
		self.assertIn('z-index: 1090;', main)
		self.assertIn('@include bgNfy("success");', base)

	def test_auto_selection_log_has_a_stable_inline_region(self):
		comp = (ROOT / 'src/scss/comp.scss').read_text()
		self.assertIn('.sim-group-auto-log {', comp)
		self.assertIn('&-summary {', comp)
		self.assertIn('&-panel {', comp)
		self.assertNotIn('.ausl-log-poptip', comp)

	def test_similar_controls_and_groups_have_stable_layout_boundaries(self):
		main = (ROOT / 'src/scss/main.scss').read_text()
		base = (ROOT / 'src/scss/main.base.scss').read_text()
		comp = (ROOT / 'src/scss/comp.scss').read_text()
		self.assertIn('position: sticky;', main)
		self.assertIn('top: 4rem;', main)
		self.assertIn('.sim-group-container {', comp)
		self.assertIn('.sim-group-card-list {', comp)
		self.assertNotIn('&.floating {', base)


if __name__ == '__main__':
	unittest.main()
