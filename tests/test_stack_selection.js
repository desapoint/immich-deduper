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


function coverButton(autoId, groupId, ownerId) {
	const classes = new Set(['btn-outline-info'])
	return {
		id: JSON.stringify({type: 'sim-stack-cover', id: autoId, group: groupId, owner: ownerId}),
		textContent: 'Set cover',
		attributes: {},
		classes,
		classList: {toggle(name, enabled) { enabled ? classes.add(name) : classes.delete(name) }},
		setAttribute(name, value) { this.attributes[name] = value },
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
	const coverButtons = [coverButton(1, 1, 'owner-a'), coverButton(2, 1, 'owner-a')]
	const syncs = []
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
			syncSte(cnt, ids) { syncs.push([cnt, Array.from(ids)]) },
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

	await ste.selectStackStatus(true, 1)
	assert.deepEqual(Array.from(ste.selectedIds), [3, 1], 'group selection must preserve other groups')
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

	await ste.selectStackStatus(false)
	assert.deepEqual(Array.from(ste.selectedIds), [2, 3], 'global selection must replace the full selection')
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

	ste.setStackCover(1, 1, 'owner-a')
	assert.deepEqual(Array.from(ste.stackCoverIds), [1])
	assert.equal(ste.selectedIds.has(1), true, 'choosing a cover must select its asset')
	assert.equal(coverButtons[0].textContent, 'Cover choice')
	assert.equal(coverButtons[0].classes.has('btn-info'), true)
	assert.equal(coverButtons[0].classes.has('btn-outline-info'), false)
	assert.equal(coverButtons[0].attributes['aria-pressed'], 'true')

	ste.setStackCover(1, 1, 'owner-a')
	assert.deepEqual(Array.from(ste.stackCoverIds), [], 'clicking the active cover must clear it')
	assert.equal(ste.selectedIds.has(1), true, 'clearing a cover must not clear image selection')
	assert.equal(coverButtons[0].textContent, 'Set cover')
	assert.equal(coverButtons[0].classes.has('btn-info'), false)
	assert.equal(coverButtons[0].classes.has('btn-outline-info'), true)
	assert.equal(coverButtons[0].attributes['aria-pressed'], 'false')
}


main().catch(error => {
	console.error(error)
	process.exitCode = 1
})
