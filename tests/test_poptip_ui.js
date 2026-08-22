const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')

class MockElement {
	constructor(id = '') {
		this.id = id
		this.children = []
		this.parentNode = null
		this.style = {}
		this.attributes = {}
		this.listeners = {}
		this.isConnected = true
		this.classList = {add() {}, remove() {}, toggle() {}}
	}
	get nextSibling() {
		if (!this.parentNode) return null
		const index = this.parentNode.children.indexOf(this)
		return this.parentNode.children[index + 1] || null
	}
	appendChild(child) {
		if (child.parentNode) child.parentNode.children = child.parentNode.children.filter(item => item !== child)
		this.children.push(child)
		child.parentNode = this
		return child
	}
	insertBefore(child, next) {
		if (child.parentNode) child.parentNode.children = child.parentNode.children.filter(item => item !== child)
		const index = next ? this.children.indexOf(next) : -1
		if (index < 0) this.children.push(child)
		else this.children.splice(index, 0, child)
		child.parentNode = this
		return child
	}
	querySelector() { return null }
	setAttribute(name, value) { this.attributes[name] = value }
	getAttribute(name) { return this.attributes[name] ?? null }
	hasAttribute(name) { return Object.hasOwn(this.attributes, name) }
	addEventListener(name, callback) { this.listeners[name] = callback }
	closest() { return null }
	click() {}
	remove() {
		if (this.parentNode) this.parentNode.children = this.parentNode.children.filter(item => item !== this)
		this.parentNode = null
	}
	getBoundingClientRect() { return {left: 10, right: 60, top: 50, bottom: 70, width: 50, height: 20} }
	get offsetHeight() { return 20 }
}

const body = new MockElement('body')
const home = new MockElement('home')
const tip = new MockElement('tip-1')
const sibling = new MockElement('sibling')
const trigger = new MockElement('trigger')
const details = new MockElement('details')
trigger.setAttribute('data-tip-id', 'tip-1')
home.appendChild(tip)
home.appendChild(sibling)

let onReady = null

const sandbox = {
	console,
	window: {dash_clientside: {}},
	dash_clientside: {no_update: null},
	document: {
		body,
		documentElement: {scrollLeft: 0, scrollTop: 0},
		getElementById(id) { return id === 'tip-1' ? tip : null },
		querySelector() { return null },
		querySelectorAll(selector) {
			if (selector === 'span[data-tip-id]') return [trigger]
			if (selector === '.sim-card-details') return [details]
			return []
		},
		createElement() { return new MockElement() },
		addEventListener(name, callback) { if (name === 'DOMContentLoaded') onReady = callback },
	},
	Element: MockElement,
	MutationObserver: class { observe() {} disconnect() {} },
	requestAnimationFrame(callback) { callback() },
	setTimeout,
	clearTimeout,
}
sandbox.window.window = sandbox.window
sandbox.window.innerWidth = 1200
sandbox.window.innerHeight = 800
sandbox.window.pageXOffset = 0
sandbox.window.pageYOffset = 0
vm.createContext(sandbox)
vm.runInContext(fs.readFileSync(path.join(__dirname, '../src/assets/appui.js'), 'utf8'), sandbox)

async function run() {
	onReady()
	assert.equal(trigger.tabIndex, 0, 'metadata popup triggers should support keyboard focus')
	assert.equal(trigger.getAttribute('role'), 'button')
	assert.equal(trigger.getAttribute('aria-haspopup'), 'true')
	assert.deepEqual(Object.keys(trigger.listeners).sort(), ['blur', 'focus', 'mouseenter', 'mouseleave'])
	vm.runInContext('window.dash_clientside.ui.toggleGridInfo(true)', sandbox)
	assert.equal(details.open, true, 'Show Grid Info should open the native card details')
	vm.runInContext('window.dash_clientside.ui.toggleGridInfo(false)', sandbox)
	assert.equal(details.open, false, 'hiding Grid Info should close the native card details')
	vm.runInContext('ui.poptip.show("tip-1", document.body)', sandbox)
	assert.equal(tip.parentNode, body, 'an active popup must escape card paint containment')
	assert.equal(tip.style.display, 'block')
	assert.equal(tip.style.position, 'fixed', 'metadata popups should be clamped to the viewport')

	vm.runInContext('ui.poptip.hide(document.getElementById("tip-1"))', sandbox)
	await new Promise(resolve => setTimeout(resolve, 330))
	assert.equal(tip.parentNode, home, 'a hidden popup must return to its rendered card')
	assert.deepEqual(home.children, [tip, sibling])
	console.log('poptip UI tests passed')
}

run().catch(error => {
	console.error(error)
	process.exitCode = 1
})
