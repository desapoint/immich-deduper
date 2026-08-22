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
		this.isConnected = true
		this.classList = {add() {}, remove() {}}
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
	addEventListener() {}
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
home.appendChild(tip)
home.appendChild(sibling)

const sandbox = {
	console,
	window: {dash_clientside: {}},
	dash_clientside: {no_update: null},
	document: {
		body,
		documentElement: {scrollLeft: 0, scrollTop: 0},
		getElementById(id) { return id === 'tip-1' ? tip : null },
		querySelector() { return null },
		querySelectorAll() { return [] },
		createElement() { return new MockElement() },
		addEventListener() {},
	},
	Element: MockElement,
	MutationObserver: class { observe() {} disconnect() {} },
	requestAnimationFrame(callback) { callback() },
	setTimeout,
	clearTimeout,
}
sandbox.window.window = sandbox.window
sandbox.window.innerWidth = 1200
sandbox.window.pageXOffset = 0
sandbox.window.pageYOffset = 0
vm.createContext(sandbox)
vm.runInContext(fs.readFileSync(path.join(__dirname, '../src/assets/appui.js'), 'utf8'), sandbox)

async function run() {
	vm.runInContext('ui.poptip.show("tip-1", document.body)', sandbox)
	assert.equal(tip.parentNode, body, 'an active popup must escape card paint containment')
	assert.equal(tip.style.display, 'block')

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
