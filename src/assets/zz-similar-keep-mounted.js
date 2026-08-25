/* Keep the Similar current-review tree visible while Dash toggles loading state.
 *
 * dbc.Spinner and Dash may update inline styles on wrapper elements while the
 * callback targeting #sim-gvSim is running. CSS alone is easy to miss when the
 * actual hidden node is an ancestor introduced by a component wrapper, so this
 * keeps the current tree mounted by correcting those inline visibility changes.
 */
(() => {
	let observer = null
	let frame = null

	function keepMounted() {
		frame = null
		const grid = document.getElementById('sim-gvSim')
		if (!grid) return

		let node = grid
		const tab = grid.closest('.tab-pane')
		while (node && node !== tab) {
			const style = window.getComputedStyle(node)
			if (style.visibility === 'hidden') {
				node.style.setProperty('visibility', 'visible', 'important')
			}
			if (style.display === 'none' && node !== grid) {
				// Do not unhide inactive Bootstrap tabs; only wrappers inside the
				// currently active tab are eligible.
				if (!node.classList.contains('tab-pane')) {
					node.style.setProperty('display', 'block', 'important')
				}
			}
			node = node.parentElement
		}
	}

	function schedule() {
		if (frame != null) return
		frame = requestAnimationFrame(keepMounted)
	}

	function install() {
		const grid = document.getElementById('sim-gvSim')
		if (!grid) return false

		keepMounted()
		observer?.disconnect()
		observer = new MutationObserver(schedule)

		let root = grid.parentElement
		while (root?.parentElement && !root.classList.contains('tab-pane')) {
			root = root.parentElement
		}
		observer.observe(root || grid.parentElement || grid, {
			subtree: true,
			attributes: true,
			attributeFilter: ['style', 'class'],
		})
		return true
	}

	if (install()) return

	let attempts = 0
	const timer = setInterval(() => {
		attempts += 1
		if (install() || attempts >= 100) clearInterval(timer)
	}, 50)
})()
