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
	const selectClasses = new Set(['btn-primary'])
	const selectButton = {
		textContent: 'Select image',
		classList: {
			contains(name) { return selectClasses.has(name) },
			toggle(name, enabled) { enabled ? selectClasses.add(name) : selectClasses.delete(name) },
		},
	}
	const setPropsCalls = []
	const toggles = []
	let syncs = 0
	const context = {
		console,
		document: {
			addEventListener() {},
			getElementById(id) { return id === 'btn-img-select' ? selectButton : null },
			querySelector() { return null },
		},
		dash_clientside: {
			no_update: {},
			callback_context: {triggered: []},
			set_props(id, props) { setPropsCalls.push({id, props}) },
		},
		Ste: {
			selectedIds: new Set([11]),
			toggle(aid) {
				toggles.push(aid)
				this.selectedIds.has(aid) ? this.selectedIds.delete(aid) : this.selectedIds.add(aid)
			},
			sync() { syncs++; context.window.MdlImg.syncSelectState() },
		},
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
	context.window.currentMdlImgAutoId = 11
	assert.equal(viewer.syncSelectState(), true)
	assert.equal(selectButton.textContent, 'Selected')
	assert.equal(selectClasses.has('btn-success'), true)
	assert.equal(setPropsCalls.at(-1).id, 'btn-img-select')
	assert.equal(setPropsCalls.at(-1).props.children, 'Selected')
	assert.equal(setPropsCalls.at(-1).props.color, 'success')
	assert.equal(viewer.toggleCurrentSelection(), true)
	assert.deepEqual(toggles, [11])
	assert.equal(syncs, 1)
	assert.equal(selectButton.textContent, 'Select image')

	const content = viewer.buildImageContent(mdl)
	assert.equal(content.map(node => findByClass(node, 'viewer-asset-status')).find(Boolean), undefined)
	const status = viewer.buildAssetStatus(mdl)
	assert.equal(status[0].children[0], 'Asset #11')
	assert.equal(status[1].children[0], '1 of 2')
	assert.equal(viewer.getInfoButtonContent()[0].props.className, 'bi bi-info-circle')
	assert.equal(viewer.getHelpButtonContent()[0].props.className, 'bi bi-keyboard')

	const toggled = viewer.toggleMode()
	assert.equal(toggled[0].modeH, false)
	assert.equal(toggled[2][1].children[0], 'Fit screen')

	viewer.init({open: false}, now, ste)
	assert.equal(viewer.updMdl().length, 15, 'a closed viewer must return one no-update value per callback output')
}


main()
