#!/usr/bin/env node

const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')


function main() {
	const titleChildren = []
	const headerChildren = []
	const cardChildren = []
	const selectors = []
	let coverUpdates = 0
	let fullCssUpdates = 0
	let buttonUpdates = 0
	const header = {appendChild(child) { headerChildren.push(child) }}
	const title = {
		getAttribute(name) { return name === 'data-group-id' ? '7' : null },
		closest(selector) { return selector === '.sim-group-header' ? header : null },
		appendChild(child) { titleChildren.push(child) },
	}
	const card = {appendChild(child) { cardChildren.push(child) }}

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
			updStackCoverButtons() { coverUpdates++ },
			updAllCss() { fullCssUpdates++; return Promise.resolve(0) },
			updBtns() { buttonUpdates++ },
		},
		dash_clientside: {callback_context: {triggered: []}, no_update: {}},
		ui: {
			mob: {
				waitAll(selector, callback) {
					selectors.push(selector)
					callback([title])
				},
				waitFor() {},
			},
		},
		document: {
			body: {},
			addEventListener() {},
			querySelector() { return null },
			querySelectorAll(selector) {
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

	assert.deepEqual(selectors, ['.gv.fsp > .sim-group-header > .sim-group-title[data-group-id]'])
	assert.equal(titleChildren.length, 1, 'the Auto log badge must be inside the group title')
	assert.equal(titleChildren[0].textContent, 'Auto log')
	assert.equal(headerChildren.length, 1, 'the Auto log popup must be inside the group header')
	assert.equal(cardChildren.length, 0, 'Auto log UI must never be inserted into an image card')

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
	assert.equal(coverUpdates, 1, 'store persistence must refresh only cover controls')
	assert.equal(fullCssUpdates, 0, 'store persistence must not rescan every card')
	assert.equal(buttonUpdates, 0, 'store persistence must not repaint buttons a second time')
}


try {
	main()
}
catch (error) {
	console.error(error)
	process.exitCode = 1
}
