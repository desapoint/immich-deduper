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
			return null
		},
		closest() { return parent },
		querySelector() { return checkbox },
	}
}


async function main() {
	const cards = [card(1, 1, true), card(2, 1, false), card(3, 2, false)]
	const syncs = []
	const context = {
		console,
		setTimeout,
		clearTimeout,
		dsh: {syncSte(cnt, ids) { syncs.push([cnt, Array.from(ids)]) }},
		document: {
			addEventListener() {},
			getElementById() { return null },
			querySelector() { return null },
			querySelectorAll(selector) {
				if (selector === '[id*="card-select"]') return cards
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
	ste.getGroupCards = groupId => cards.filter(item => String(item.groupId) === String(groupId))

	await ste.selectStackStatus(true, 1)
	assert.deepEqual(Array.from(ste.selectedIds), [3, 1], 'group selection must preserve other groups')

	await ste.selectStackStatus(false)
	assert.deepEqual(Array.from(ste.selectedIds), [2, 3], 'global selection must replace the full selection')
	assert.equal(syncs.length, 2)
}


main().catch(error => {
	console.error(error)
	process.exitCode = 1
})
