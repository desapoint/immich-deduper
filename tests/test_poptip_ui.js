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
		this.rect = {left: 10, right: 60, top: 50, bottom: 70, width: 50, height: 20}
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
	getBoundingClientRect() { return this.rect }
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
sandbox.window.testTrigger = trigger
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
	tip.rect = {left: 0, right: 280, top: 0, bottom: 120, width: 280, height: 120}
	vm.runInContext('ui.poptip.show("tip-1", window.testTrigger)', sandbox)
	assert.equal(tip.parentNode, body, 'an active popup must escape card paint containment')
	assert.equal(tip.style.display, 'block')
	assert.equal(tip.style.position, 'fixed', 'metadata popups should be clamped to the viewport')
	assert.equal(tip.style.left, '72px', 'metadata popups should prefer the trigger right side')
	assert.ok(Number(tip.style.zIndex) >= 1200, 'metadata popups should render above sticky headers and batch controls')

	trigger.rect = {left: 1140, right: 1190, top: 300, bottom: 320, width: 50, height: 20}
	const leftDirection = vm.runInContext('ui.poptip.position(document.getElementById("tip-1"), window.testTrigger).direction', sandbox)
	assert.equal(leftDirection, 'left', 'metadata popups should flip left near the viewport right edge')
	assert.equal(tip.style.left, '848px')

	trigger.listeners.mouseleave.call(trigger)
	await new Promise(resolve => setTimeout(resolve, 250))
	assert.equal(tip.style.display, 'block', 'the trigger should provide a 500 ms grace period')
	tip.listeners.mouseenter()
	await new Promise(resolve => setTimeout(resolve, 350))
	assert.equal(tip.style.display, 'block', 'entering the popup should cancel pending dismissal')
	tip.listeners.mouseleave()
	await new Promise(resolve => setTimeout(resolve, 650))
	assert.equal(tip.parentNode, home, 'leaving both trigger and popup should dismiss and restore it')

	assert.deepEqual(home.children, [tip, sibling])
	console.log('poptip UI tests passed')
}

run().catch(error => {
	console.error(error)
	process.exitCode = 1
})
