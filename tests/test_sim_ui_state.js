#!/usr/bin/env node

const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')


async function main() {
	const titleChildren = []
	const headerChildren = []
	const cardChildren = []
	const logChildren = []
	const selectors = []
	let coverUpdates = 0
	let fullCssUpdates = 0
	let buttonUpdates = 0
	let cacheRefreshes = 0
	let renderedCards = []
	let exportGrid = null
	const grid = {}
	const header = {appendChild(child) { headerChildren.push(child) }}
	const title = {
		getAttribute(name) { return name === 'data-group-id' ? '7' : null },
		closest(selector) { return selector === '.sim-group-header' ? header : null },
		appendChild(child) { titleChildren.push(child) },
	}
	const card = {appendChild(child) { cardChildren.push(child) }}
	const logSlot = {
		getAttribute(name) { return name === 'data-group-id' ? '7' : null },
		appendChild(child) { logChildren.push(child) },
		replaceChildren() { logChildren.length = 0 },
	}

	const context = {
		console,
		setTimeout,
		clearTimeout,
		fetch() { return Promise.resolve() },
		notify() {},
		dsh: {syncSte() {}},
		Ste: {
			selectedIds: new Set(),
			stackCoverIds: new Set(),
			extractAssetIdBy() { return null },
			refreshDomCache() { cacheRefreshes++ },
			getCard() { return null },
			updStackCoverButtons() { coverUpdates++ },
			updAllCss() { fullCssUpdates++; return Promise.resolve(0) },
			updBtns() { buttonUpdates++ },
		},
		dash_clientside: {callback_context: {triggered: []}, no_update: {}},
		ui: {
			mob: {
				waitAll(selector, callback) {
					selectors.push(selector)
					callback([logSlot])
				},
				waitFor() {},
			},
		},
		document: {
			body: {},
			addEventListener() {},
			querySelector(selector) {
				if (selector === '.gv.fsp') return exportGrid
				return selector === '#sim-gvSim' && renderedCards.length ? grid : null
			},
			querySelectorAll(selector) {
				if (selector === '#sim-gvSim [id*="card-select"]') return renderedCards
				if (selector === '.sim-group-auto-log') return [logSlot]
				if (selector === '.card') return [card]
				return []
			},
			createElement() {
				return {
					className: '',
					id: '',
					innerHTML: '',
					textContent: '',
					setAttribute(name, value) { this[name] = value },
				}
			},
		},
		MutationObserver: class {
			disconnect() {}
			observe() {}
		},
	}
	context.window = context
	context.window.addEventListener = () => {}

	vm.createContext(context)
	vm.runInContext(
		fs.readFileSync(path.join(__dirname, '../src/assets/mod/sim.js'), 'utf8'),
		context,
	)

	context.window.auslLogs = {
		7: {reason: 'Selected #1', selectedAids: [1], details: []},
	}
	vm.runInContext('updAuslLog()', context)

	assert.deepEqual(selectors, ['.gv.fsp .sim-group-auto-log[data-group-id]'])
	assert.equal(logChildren.length, 1, 'the Auto log must render in its dedicated group slot')
	assert.equal(logChildren[0].className, 'ausl-log')
	assert.match(logChildren[0].innerHTML, /Auto-selection details/)
	assert.equal(titleChildren.length, 0, 'the Auto log must not alter the group title grid')
	assert.equal(headerChildren.length, 0, 'the Auto log must not create a floating header popup')
	assert.equal(cardChildren.length, 0, 'Auto log UI must never be inserted into an image card')

	context.window.auslLogs[7].reason = 'Updated selection #2'
	vm.runInContext('updAuslLog()', context)
	assert.equal(logChildren.length, 1, 'updating Auto Log must replace stale details instead of duplicating them')
	assert.match(logChildren[0].innerHTML, /Updated selection #2/)

	const exportGroup = (groupId, metas) => ({
		classList: {contains(name) { return name === 'sim-group-container' }},
		getAttribute(name) { return name === 'data-group-id' ? String(groupId) : null },
		querySelectorAll(selector) {
			return selector === '.card-meta'
				? metas.map(meta => ({dataset: {meta: JSON.stringify(meta)}}))
				: []
		},
	})
	exportGrid = {
		children: [
			exportGroup(7, [{id: 'a', autoId: 1, originalFileName: 'one.jpg', originalPath: '/one.jpg'}]),
			exportGroup(8, [{id: 'b', autoId: 2, originalFileName: 'two.jpg', originalPath: '/two.jpg'}]),
		],
	}
	const groupedExport = vm.runInContext('groupAssetsByVisualGroups([])', context)
	assert.deepEqual(Array.from(groupedExport, group => group.group), [7, 8])
	assert.deepEqual(Array.from(groupedExport, group => group.assets.length), [1, 1])

	vm.runInContext('_lastAutoSelAssetIds = [1, 2, 3]; _lastAutoSelConfigSig = "same"', context)
	assert.equal(vm.runInContext('isExistingResultUpdate([1, 3], "same")', context), true)
	assert.equal(vm.runInContext('isExistingResultUpdate([1, 2, 3], "same")', context), true)
	assert.equal(vm.runInContext('isExistingResultUpdate([1, 2, 3, 4], "same")', context), false)
	assert.equal(vm.runInContext('isExistingResultUpdate([1, 2], "changed")', context), false)

	context.dash_clientside.callback_context.triggered = [{prop_id: 'store-state.data', value: {}}]
	context.window.dash_clientside.similar.onSimJs(
		null,
		{cntTotal: 3, selectedIds: [1], stackCoverIds: [1]},
		{},
	)
	assert.equal(coverUpdates, 0, 'store persistence must not repaint cover controls a second time')
	assert.equal(fullCssUpdates, 0, 'store persistence must not rescan every card')
	assert.equal(buttonUpdates, 0, 'store persistence must not repaint buttons a second time')

	const renderedCard = {
		getAttribute(name) { return name === 'data-stack-id' ? '' : null },
	}
	renderedCards = [renderedCard]
	context.Ste.extractAssetIdBy = item => item === renderedCard ? 1 : null
	context.window.auslLogs = {}
	context.window.auslReasons = {}
	const coversBeforePatch = coverUpdates
	vm.runInContext('waitForCardsAndUpdate([], [{autoId: 1, ex: {stackId: null}}], false)', context)
	await new Promise(resolve => setTimeout(resolve, 10))

	assert.equal(cacheRefreshes, 1, 'a card patch should refresh the DOM cache exactly once')
	assert.equal(fullCssUpdates, 0, 'an existing-result patch must preserve card state without repainting the whole grid')
	assert.equal(buttonUpdates, 1, 'an existing-result patch should update controls once')
	assert.equal(coverUpdates, coversBeforePatch + 1, 'an existing-result patch should refresh cover controls once')

	const pathRules = vm.runInContext('_pathRules(" /library/clean\\r\\n\\n/screenshots \\n/library/clean")', context)
	assert.deepEqual(Array.from(pathRules), ['/library/clean', '/screenshots'], 'path rules should trim, ignore blanks, and deduplicate')

	const pathSelection = vm.runInContext(`_selectBestAsset([
		{autoId: 1, originalPath: '/library/clean/screenshots/one.jpg', originalFileName: 'one.jpg'},
		{autoId: 2, originalPath: '/library/import/other/two.jpg', originalFileName: 'two.jpg'}
	], {pth: {k: '/library/clean\\n/screenshots', v: 2}})`, context)
	assert.equal(pathSelection.aids[0], 1, 'any matching path rule should select the matching asset')
	assert.equal(pathSelection.allScores[1].score, 20, 'multiple matching path rules should apply the configured weight only once')
}


main().catch(error => {
	console.error(error)
	process.exitCode = 1
})
