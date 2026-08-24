#!/usr/bin/env node

const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')


function box(id, timeout = 5000) {
	return {
		nodeType: 1,
		dataset: {msgId: id, msgTimeout: String(timeout)},
		matches(selector) { return selector === '.box' },
		querySelectorAll() { return [] },
	}
}


function main() {
	const timers = []
	const syncs = []
	const initial = box('initial', 100)
	let initialScans = 0
	let readyHandler = null
	let mutationHandler = null
	const container = {
		querySelectorAll(selector) {
			assert.equal(selector, '.box')
			initialScans++
			return [initial]
		},
	}
	const context = {
		console,
		setTimeout(callback, timeout) {
			timers.push({callback, timeout})
			return timers.length
		},
		dsh: {
			noUpd: {},
			syncStore(id, data) { syncs.push({id, data}) },
		},
		document: {
			addEventListener(name, callback) {
				if (name === 'DOMContentLoaded') readyHandler = callback
			},
		},
		ui: {mob: {waitFor(selector, callback) {
			assert.equal(selector, '#div-notify')
			callback(container)
		}}},
		MutationObserver: class {
			constructor(callback) { mutationHandler = callback }
			observe(target, options) {
				assert.equal(target, container)
				assert.equal(options.childList, true)
				assert.equal(options.subtree, true)
			}
		},
	}
	context.window = context
	context.window.dash_clientside = {}
	vm.createContext(context)
	vm.runInContext(
		fs.readFileSync(path.join(__dirname, '../src/assets/mod/nfy.js'), 'utf8'),
		context,
	)

	vm.runInContext("Nfy.info('one'); Nfy.success('two')", context)
	assert.equal(timers.length, 1, 'a notification burst must schedule one store flush')
	timers.shift().callback()
	assert.equal(syncs.length, 1)
	assert.equal(syncs[0].id, 'hidden-add-trigger')
	assert.equal(syncs[0].data.length, 2)

	readyHandler()
	assert.equal(initialScans, 1, 'existing notifications should be scanned once at initialization')
	assert.equal(timers.length, 1, 'the existing notification should receive one removal timer')

	const direct = box('direct', 200)
	const nested = box('nested', 300)
	const wrapper = {
		nodeType: 1,
		matches() { return false },
		querySelectorAll(selector) { return selector === '.box' ? [nested] : [] },
	}
	mutationHandler([{addedNodes: [direct, wrapper]}])
	assert.equal(initialScans, 1, 'new notifications must not rescan existing toast nodes')
	assert.deepEqual(timers.map(timer => timer.timeout), [100, 200, 300])

	mutationHandler([{addedNodes: [direct]}])
	assert.equal(timers.length, 3, 'an already scheduled notification must not receive another timer')
}


try { main() }
catch (error) {
	console.error(error)
	process.exitCode = 1
}
