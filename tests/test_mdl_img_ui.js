#!/usr/bin/env node

const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')


function findByClass(node, className) {
	if (!node || typeof node !== 'object') return null
	if (node.props?.className === className) return node
	for (const child of node.children || []) {
		const found = findByClass(child, className)
		if (found) return found
	}
	return null
}


function main() {
	const context = {
		console,
		document: {addEventListener() {}, querySelector() { return null }},
		dash_clientside: {no_update: {}, callback_context: {triggered: []}},
		R: {
			mk(type, props, ...children) { return {type, props, children: children.filter(child => child != null)} },
		},
	}
	context.window = context
	vm.createContext(context)
	vm.runInContext(
		fs.readFileSync(path.join(__dirname, '../src/assets/mod/mdlImg.js'), 'utf8'),
		context,
	)

	const assets = [
		{autoId: 11, simGIDs: [2], originalFileName: 'one.jpg', originalPath: '/one.jpg'},
		{autoId: 12, simGIDs: [2], originalFileName: 'two.jpg', originalPath: '/two.jpg'},
	]
	const mdl = {open: true, isMulti: true, curIdx: 0, modeH: true, imgUrl: '/api/img/11'}
	const now = {sim: {assCur: assets}}
	const ste = {cntTotal: 2, selectedIds: [11], stackCoverIds: []}
	const viewer = context.window.MdlImg.init(mdl, now, ste)

	assert.equal(viewer.getSelectButtonText(mdl, assets[0]), 'Selected')
	assert.equal(viewer.getSelectButtonText(mdl, assets[1]), 'Select image')
	assert.equal(viewer.getModeTxt(mdl), 'Actual size')
	assert.equal(viewer.getPrevButtonStyle(mdl).display, 'grid')
	assert.equal(viewer.getPrevButtonStyle(mdl).pointerEvents, 'none')
	assert.equal(viewer.getNextButtonStyle(mdl).display, 'grid')
	assert.equal(viewer.getNextButtonStyle(mdl).pointerEvents, 'auto')
	assert.equal(viewer.getSelectButtonStyle(mdl).display, 'inline-flex')

	const content = viewer.buildImageContent(mdl)
	const status = content.map(node => findByClass(node, 'viewer-asset-status')).find(Boolean)
	assert.ok(status, 'multi-image content should expose a stable asset status bar')
	assert.equal(status.children[0].children[0], 'Asset #11')
	assert.equal(status.children[1].children[0], '1 of 2')

	const toggled = viewer.toggleMode()
	assert.equal(toggled[0].modeH, false)
	assert.equal(toggled[2], 'Fit screen')

	viewer.init({open: false}, now, ste)
	assert.equal(viewer.updMdl().length, 14, 'a closed viewer must return one no-update value per callback output')
}


main()
