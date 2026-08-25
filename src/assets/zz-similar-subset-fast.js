/* Fast path for Similar group removals.
 *
 * A completed group changes store-now.sim.assCur to a strict subset of the
 * previous asset set. The normal onSimJs path waits for every card, rebuilds
 * Ste's complete DOM cache, and reconciles buttons/tooltips/logs across all
 * surviving groups. None of that is required when the only visual change is
 * removing an already-completed group: Dash's keyed Patch owns the DOM change.
 *
 * Keep the lightweight selection counters in sync, invalidate (do not rebuild)
 * the DOM cache, prune stale auto-selection metadata, and leave the surviving
 * group DOM untouched.
 */
(() => {
	let previousAssetIds = null
	let previousConfigSig = null

	const assetIds = nowData => (nowData?.sim?.assCur || [])
		.map(asset => Number.parseInt(asset.autoId, 10))
		.filter(Number.isFinite)
		.sort((a, b) => a - b)

	const isStrictSubset = (current, previous) => {
		if (!previous || current.length >= previous.length) return false
		const previousSet = new Set(previous)
		return current.every(id => previousSet.has(id))
	}

	function pruneAutoSelectionState(nowData) {
		const assets = nowData?.sim?.assCur || []
		const liveAssetIds = new Set(assets.map(asset => String(asset.autoId)))
		const liveGroupIds = new Set(
			assets.map(asset => String(asset.vw?.muodId ?? asset.autoId))
		)

		for (const aid of Object.keys(window.auslReasons || {})) {
			if (!liveAssetIds.has(String(aid))) delete window.auslReasons[aid]
		}
		for (const gid of Object.keys(window.auslLogs || {})) {
			if (!liveGroupIds.has(String(gid))) delete window.auslLogs[gid]
		}
	}

	function syncLightweightSelectionState(count) {
		if (!window.Ste) return
		const storeState = window.dsh?.getStore?.('store-state')

		Ste.cntTotal = count
		if (storeState) {
			Ste.selectedIds = new Set(storeState.selectedIds || [])
			Ste.stackCoverIds = new Set(storeState.stackCoverIds || [])
		}

		// The removed group's elements are gone, so any cached element references
		// are stale. Invalidate lazily rather than immediately scanning every card.
		Ste.invalidateDomCache?.()

		const selectedCount = Ste.selectedIds?.size || 0
		const label = document.getElementById('sim-txt-cnt-sel')
		if (label) label.textContent = `${selectedCount}/${count} selected`
	}

	function install() {
		const similar = window.dash_clientside?.similar
		const original = similar?.onSimJs
		if (!original) return false
		if (original.__subsetRemovalFastPath) return true

		function onSimJsFast(nowData, setsData) {
			const currentIds = assetIds(nowData)
			const configSig = JSON.stringify(setsData?.ausl || {})
			const removalOnly =
				configSig === previousConfigSig &&
				isStrictSubset(currentIds, previousAssetIds)

			previousAssetIds = currentIds
			previousConfigSig = configSig

			if (!removalOnly) return original.apply(this, arguments)

			// Pure removal: do not wait for cards or touch surviving card DOM.
			pruneAutoSelectionState(nowData)
			syncLightweightSelectionState(currentIds.length)
			return window.dash_clientside.no_update
		}

		onSimJsFast.__subsetRemovalFastPath = true
		onSimJsFast.__original = original
		similar.onSimJs = onSimJsFast
		return true
	}

	if (install()) return

	let attempts = 0
	const timer = window.setInterval(() => {
		attempts += 1
		if (install() || attempts >= 100) window.clearInterval(timer)
	}, 50)
})()
