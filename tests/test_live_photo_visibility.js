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
	let intervalCount = 0
	const listeners = new Map()
	const modalListeners = new Map()
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
	const modalImage = {style: {}}
	const progressFill = {style: {}}
	const timeDisplay = {textContent: ''}
	const modal = {
		querySelector(selector) {
			if (selector === 'img') return modalImage
			if (selector === '#livephoto-progress-fill') return progressFill
			if (selector === '#livephoto-time-display') return timeDisplay
			return null
		},
	}
	const modalVideo = {
		tagName: 'VIDEO',
		dataset: {},
		style: {},
		duration: 10,
		currentTime: 2,
		addEventListener(name, callback) { modalListeners.set(name, callback) },
		closest(selector) { return selector === '#img-modal' ? modal : null },
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
		setInterval() { intervalCount++ },
		document: {
			readyState: 'complete',
			body: {},
			addEventListener() {},
			querySelectorAll(selector) {
				if (selector === 'video.livephoto') return [video]
				if (selector === '#img-modal .livephoto video') return [modalVideo]
				return []
			},
			querySelector() { return null },
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
	assert.equal(intervalCount, 0, 'idle pages must not poll modal progress every 100 ms')
	assert.ok(modalListeners.has('timeupdate'), 'modal progress should follow media events')
	modalListeners.get('timeupdate')()
	assert.equal(progressFill.style.width, '20%')
	assert.equal(timeDisplay.textContent, '0:02 / 0:10')
}


main()
