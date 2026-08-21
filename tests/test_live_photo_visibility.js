#!/usr/bin/env node

const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')


function main() {
	let intersectionCallback = null
	let observed = null
	let plays = 0
	let pauses = 0
	const listeners = new Map()
	const badge = {innerText: '', classList: {add() {}, remove() {}}}
	const viewer = {querySelector() { return badge }}
	const video = {
		tagName: 'VIDEO',
		dataset: {},
		style: {},
		addEventListener(name, callback) { listeners.set(name, callback) },
		closest(selector) { return selector === '.viewer' ? viewer : null },
		play() { plays++; return Promise.resolve() },
		pause() { pauses++ },
	}

	class IntersectionObserver {
		constructor(callback, options) {
			intersectionCallback = callback
			assert.equal(options.rootMargin, '160px 0px')
		}
		observe(target) { observed = target }
	}

	class MutationObserver {
		observe() {}
	}

	const context = {
		console,
		IntersectionObserver,
		MutationObserver,
		setInterval() {},
		document: {
			readyState: 'complete',
			body: {},
			addEventListener() {},
			querySelectorAll(selector) {
				if (selector === '.livephoto') return [video]
				return []
			},
		},
	}
	context.window = context
	vm.createContext(context)
	vm.runInContext(
		fs.readFileSync(path.join(__dirname, '../src/assets/mod/livePhoto.js'), 'utf8'),
		context,
	)

	assert.equal(observed, video, 'grid Live Photos should be visibility-observed')
	assert.equal(plays, 0, 'an offscreen Live Photo must not autoplay at render time')
	intersectionCallback([{target: video, isIntersecting: true}])
	assert.equal(plays, 1, 'a near-visible Live Photo should start playing')
	intersectionCallback([{target: video, isIntersecting: false}])
	assert.equal(pauses, 1, 'an offscreen Live Photo should pause')
	assert.ok(listeners.has('error'), 'existing playback error handling should remain active')
}


main()
