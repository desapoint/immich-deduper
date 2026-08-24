#!/usr/bin/env node

const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')


function card(autoId, groupId, stacked) {
	const parent = {classList: {add() {}, remove() {}}}
	const checkbox = {checked: false}
	return {
		autoId,
		groupId,
		id: JSON.stringify({type: 'card-select', id: autoId}),
		getAttribute(name) {
			if (name === 'id') return this.id
			if (name === 'data-stacked') return stacked ? 'true' : 'false'
			if (name === 'data-group-id') return String(groupId)
			return null
		},
		closest() { return parent },
		querySelector() { return checkbox },
	}
}


function coverButton(autoId, groupId, ownerId, onIdRead = null) {
	const classes = new Set(['btn-outline-info'])
	const patternId = JSON.stringify({type: 'sim-stack-cover', id: autoId, group: groupId, owner: ownerId})
	return {
		get id() { if (onIdRead) onIdRead(); return patternId },
		textContent: 'Set cover',
		attributes: {},
		classes,
		classList: {
			toggle(name, enabled) { enabled ? classes.add(name) : classes.delete(name) },
			contains(name) { return classes.has(name) },
		},
		setAttribute(name, value) { this.attributes[name] = value },
		closest() { return {querySelector() { return null }} },
	}
}


function actionButton(type, groupId, action = null) {
	return {
		id: JSON.stringify({type, ...(action ? {action} : {}), id: groupId}),
		disabled: true,
	}
}


async function main() {
	const cards = [card(1, 1, true), card(2, 1, false), card(3, 2, false)]
	let offGroupCoverReads = 0
	const coverButtons = [
		coverButton(1, 1, 'owner-a'),
		coverButton(2, 1, 'owner-a'),
		coverButton(3, 2, 'owner-b', () => { offGroupCoverReads++ }),
	]
	const syncs = []
	const actionSyncs = []
	const sourceClasses = new Set()
	let selectorScans = 0
	let currentTask = null
	const setPropsCalls = []
	const groupStackButton = actionButton('sim-stack-group', 1)
	const groupKeepButton = actionButton('sim-group-action', 1, 'keep-selected')
	const sourceButton = {
		attributes: {},
		disabled: false,
		classList: {toggle(name, enabled) { enabled ? sourceClasses.add(name) : sourceClasses.delete(name) }},
		setAttribute(name, value) { this.attributes[name] = value },
	}
	const removeButton = {disabled: false, textContent: '', title: ''}
	const keepButton = {disabled: false, textContent: '', title: ''}
	const stackButton = {id: 'sim-btn-Stack', disabled: true}
	const buttons = {
		'sim-btn-SelectMns': sourceButton,
		'sim-btn-RmSel': removeButton,
		'sim-btn-OkSel': keepButton,
		'sim-btn-Stack': stackButton,
	}
	const context = {
		console,
		setTimeout,
		clearTimeout,
		dash_clientside: {
			set_props(id, props) { setPropsCalls.push({id, props}) },
		},
		dsh: {
			getStore(id) { return id === 'store-tsk' ? currentTask : null },
			syncSte(cnt, ids, covers) { syncs.push([cnt, Array.from(ids), Array.from(covers || [])]) },
			syncStore(id, data) { actionSyncs.push({id, data}); return true },
		},
		document: {
			addEventListener() {},
			getElementById(id) { return buttons[id] || null },
			querySelector() { return null },
			querySelectorAll(selector) {
				selectorScans++
				if (selector === '.sim.main [id*="card-select"]') return [cards[0], cards[2]]
				if (selector.includes('"type":"sim-stack-cover"')) return coverButtons
				if (selector.includes('"type":"sim-stack-group"')) return [groupStackButton]
				if (selector.includes('"type":"sim-group-action"')) return [groupKeepButton]
				if (selector.startsWith('[id*="card-select"]')) return cards
				return []
			},
		},
		getCardById(autoId) {
			return Promise.resolve(cards.find(item => item.autoId === autoId) || null)
		},
	}
	context.window = context
	vm.createContext(context)
	vm.runInContext(
		fs.readFileSync(path.join(__dirname, '../src/assets/mod/ste.js'), 'utf8'),
		context,
	)

	const ste = context.window.Ste
	ste.cntTotal = cards.length
	ste.selectedIds = new Set([3])
	const cssUpdates = []
	const originalUpdCss = ste.updCss.bind(ste)
	ste.updCss = async (aid, selectedCard) => {
		cssUpdates.push(aid)
		return originalUpdCss(aid, selectedCard)
	}

	await ste.selectStackStatus(true, 1)
	assert.deepEqual(Array.from(ste.selectedIds), [3, 1], 'group selection must preserve other groups')
	assert.deepEqual(cssUpdates.sort((a, b) => a - b), [1, 2], 'group selection must repaint only that group')
	assert.ok(
		setPropsCalls.some(call => call.id === 'sim-btn-Stack' && call.props.disabled === false),
		'enabling the global stack action must update its Dash component prop',
	)
	assert.ok(
		setPropsCalls.some(call => call.id?.type === 'sim-stack-group' && call.id.id === 1 && call.props.disabled === false),
		'enabling a group stack action must update its pattern-matching Dash component prop',
	)
	assert.ok(
		setPropsCalls.some(call => call.id?.type === 'sim-group-action' && call.id.id === 1 && call.props.disabled === false),
		'enabling another selection-dependent group action must update its Dash component prop',
	)

	cssUpdates.length = 0
	await ste.selectStackStatus(false)
	assert.deepEqual(Array.from(ste.selectedIds), [2, 3], 'global selection must replace the full selection')
	assert.deepEqual(cssUpdates.sort((a, b) => a - b), [1, 2, 3], 'global selection should repaint all cards')
	assert.equal(syncs.length, 2)

	ste.selectedIds = new Set([1, 3])
	ste.updBtnMns()
	assert.equal(sourceClasses.has('active'), true, 'Sources must show its active state immediately')
	assert.equal(sourceButton.attributes['aria-pressed'], 'true')
	ste.selectedIds.delete(3)
	ste.updBtnMns()
	assert.equal(sourceClasses.has('active'), false)
	assert.equal(sourceButton.attributes['aria-pressed'], 'false')

	ste.selectedIds = new Set([1])
	currentTask = {id: 'task-1', cmd: 'running'}
	ste.updBtns(1)
	assert.equal(removeButton.disabled, true, 'local selection updates must not re-enable actions during a task')
	assert.equal(keepButton.disabled, true)
	assert.equal(stackButton.disabled, true)
	assert.equal(sourceButton.disabled, true)
	currentTask = null
	ste.updBtns(1)
	assert.equal(removeButton.disabled, false, 'selection actions should recover locally after the task gate clears')
	assert.equal(keepButton.disabled, false)
	assert.equal(stackButton.disabled, false)

	const scansAfterCache = selectorScans
	ste.toggle(2, cards[1])
	assert.equal(selectorScans, scansAfterCache, 'a card toggle must reuse the DOM cache instead of rescanning the grid')

	offGroupCoverReads = 0
	ste.setStackCover(1, 1, 'owner-a')
	assert.equal(offGroupCoverReads, 0, 'a cover change must not parse buttons from another group')
	assert.deepEqual(Array.from(ste.stackCoverIds), [1])
	assert.equal(ste.selectedIds.has(1), true, 'choosing a cover must select its asset')
	assert.equal(coverButtons[0].textContent, 'Cover choice')
	assert.equal(coverButtons[0].classes.has('btn-info'), true)
	assert.equal(coverButtons[0].classes.has('btn-outline-info'), false)
	assert.equal(coverButtons[0].attributes['aria-pressed'], 'true')
	assert.ok(
		setPropsCalls.some(call => call.id?.type === 'sim-stack-cover'
			&& call.id.id === 1
			&& call.props.children === 'Cover choice'
			&& call.props.outline === false),
		'cover choice must update the Dash component props so React cannot revert it',
	)

	ste.setStackCover(1, 1, 'owner-a')
	assert.deepEqual(Array.from(ste.stackCoverIds), [], 'clicking the active cover must clear it')
	assert.equal(ste.selectedIds.has(1), true, 'clearing a cover must not clear image selection')
	assert.equal(coverButtons[0].textContent, 'Set cover')
	assert.equal(coverButtons[0].classes.has('btn-info'), false)
	assert.equal(coverButtons[0].classes.has('btn-outline-info'), true)
	assert.equal(coverButtons[0].attributes['aria-pressed'], 'false')

	const syncCount = syncs.length
	assert.equal(ste.handleCardSelect(cards[1]), true)
	assert.equal(syncs.length, syncCount + 1, 'a delegated card click must persist its local state once')
	assert.equal(ste.handleStackCover(coverButtons[0]), true)
	assert.deepEqual(syncs.at(-1)[2], [1], 'a delegated cover click must persist the chosen cover')

	assert.equal(ste.dispatchAction({id: 'sim-btn-Stack', disabled: false}), true)
	assert.equal(actionSyncs.at(-1).id, 'sim-action-trigger')
	assert.equal(actionSyncs.at(-1).data.id, 'sim-btn-Stack')
	assert.equal(ste.dispatchAction(groupStackButton), true)
	assert.equal(actionSyncs.at(-1).data.id.type, 'sim-stack-group')
	assert.equal(actionSyncs.at(-1).data.id.id, 1)
	assert.ok(actionSyncs.at(-1).data.nonce > actionSyncs.at(-2).data.nonce)
	assert.equal(ste.dispatchAction({id: JSON.stringify({type: 'asset-del', aid: 2})}, 'view-action-trigger'), true)
	assert.equal(actionSyncs.at(-1).id, 'view-action-trigger')
	assert.equal(actionSyncs.at(-1).data.id.aid, 2)
}


main().catch(error => {
	console.error(error)
	process.exitCode = 1
})
