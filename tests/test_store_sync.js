#!/usr/bin/env node

const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')


let currentState = {cntTotal: 3, selectedIds: [1, 2], stackCoverIds: [2]}
const writes = []
const sandbox = {
	console,
	window: {
		dash_clientside: {
			set_props(id, props) {
				writes.push({id, data: props.data})
				if (id === 'store-state') currentState = props.data
			},
		},
		dash_component_api: {
			getLayout(id) {
				return id === 'store-state' ? {props: {data: currentState}} : null
			},
		},
	},
	document: {
		body: {},
		addEventListener() {},
		querySelector() { return null },
	},
	MutationObserver: class {
		observe() {}
	},
	React: {createElement() {}},
	setTimeout,
	clearTimeout,
}
sandbox.window.window = sandbox.window
vm.createContext(sandbox)
vm.runInContext(fs.readFileSync(path.join(__dirname, '../src/assets/app.js'), 'utf8'), sandbox)

const unchanged = vm.runInContext('dsh.syncSte(3, [2, 1], [2])', sandbox)
assert.equal(unchanged, false, 'the same selection must not write the store again')
assert.equal(writes.length, 0)

const changed = vm.runInContext('dsh.syncSte(3, [1, 3], [3])', sandbox)
assert.equal(changed, true)
assert.equal(writes.length, 1)
assert.equal(writes[0].id, 'store-state')
assert.equal(
	JSON.stringify(writes[0].data),
	JSON.stringify({cntTotal: 3, selectedIds: [1, 3], stackCoverIds: [3]}),
)

const repeated = vm.runInContext('dsh.syncSte(3, new Set([3, 1]), new Set([3]))', sandbox)
assert.equal(repeated, false, 'sets with the same IDs must also be deduplicated')
assert.equal(writes.length, 1)

console.log('store sync tests passed')
