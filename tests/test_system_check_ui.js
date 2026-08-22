const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')

function classList(initial = []) {
	const values = new Set(initial)
	return {
		add(...names) { names.forEach(name => values.add(name)) },
		remove(...names) { names.forEach(name => values.delete(name)) },
		contains(name) { return values.has(name) },
	}
}

function statusItem() {
	const icon = {className: 'bi bi-server'}
	const state = {innerText: 'Checking', className: 'settings-status-state'}
	const attributes = {}
	return {
		icon,
		state,
		attributes,
		classList: classList(),
		style: {},
		querySelector(selector) {
			if (selector === 'i') return icon
			if (selector === '.settings-status-state') return state
			return null
		},
		setAttribute(name, value) { attributes[name] = value },
		removeAttribute(name) { delete attributes[name] },
	}
}

const dataItem = statusItem()
const pathItem = statusItem()
const statusCard = {
	querySelector(selector) {
		if (selector === '.chk-data') return dataItem
		if (selector === '.chk-path') return pathItem
		return null
	},
}

let currentCard = null
let observerCallback = null
const sandbox = {
	console,
	window: {dash_clientside: {}},
	document: {
		body: {},
		addEventListener() {},
		querySelector(selector) {
			return selector === '.card-system-cfgs' ? currentCard : null
		},
	},
	MutationObserver: class {
		constructor(callback) { observerCallback = callback }
		observe() {}
	},
	React: {createElement() {}},
	setTimeout,
	clearTimeout,
}
sandbox.window.window = sandbox.window
vm.createContext(sandbox)
vm.runInContext(fs.readFileSync(path.join(__dirname, '../src/assets/app.js'), 'utf8'), sandbox)

vm.runInContext(`syncSystemCheckResults([
	{key: 'data', ok: true, msg: ['accessible']},
	{key: 'path', ok: false, msg: ['not mounted']}
])`, sandbox)
assert.equal(currentCard, null, 'the first response may arrive before Dash mounts Settings')

currentCard = statusCard
observerCallback()

assert.equal(dataItem.state.innerText, 'Valid')
assert.equal(dataItem.attributes['data-check-status'], 'valid')
assert.equal(dataItem.classList.contains('is-valid'), true)
assert.match(dataItem.icon.className, /check-circle-fill/)

assert.equal(pathItem.state.innerText, 'Issue')
assert.equal(pathItem.attributes['data-check-status'], 'invalid')
assert.equal(pathItem.attributes['data-tooltip'], 'not mounted')
assert.equal(pathItem.classList.contains('is-invalid'), true)
assert.match(pathItem.icon.className, /x-circle-fill/)

console.log('system check UI tests passed')
