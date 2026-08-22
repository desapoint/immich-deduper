#!/usr/bin/env node

const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')


function main() {
	const noUpdate = {}
	const context = {
		dash_clientside: {
			callback_context: {triggered: []},
			no_update: noUpdate,
		},
	}
	context.window = context
	vm.createContext(context)
	vm.runInContext(
		fs.readFileSync(path.join(__dirname, '../src/assets/mod/pager.js'), 'utf8'),
		context,
	)

	const pager = context.window.dash_clientside.pager
	const data = {idx: 2, size: 25, cnt: 80}

	context.dash_clientside.callback_context.triggered = [{value: 50}]
	assert.deepEqual(
		JSON.parse(JSON.stringify(pager.onSizeChange([25, 50], data))),
		{idx: 2, size: 50, cnt: 80},
	)
	context.dash_clientside.callback_context.triggered = [{value: 25}]
	assert.equal(pager.onSizeChange([25, 25], data), noUpdate, 'unchanged page size must not rewrite the store')

	context.dash_clientside.callback_context.triggered = [{
		prop_id: `${JSON.stringify({type: 'pgr-test-nav', action: 'next', idx: 0})}.n_clicks`,
		value: 1,
	}]
	assert.equal(pager.onClick([], [1], data).idx, 3)

	context.dash_clientside.callback_context.triggered = [{
		prop_id: `${JSON.stringify({type: 'pgr-test-page', page: 1, idx: 1})}.n_clicks`,
		value: 1,
	}]
	assert.equal(pager.onClick([1], [], data).idx, 1)

	context.dash_clientside.callback_context.triggered = [{
		prop_id: `${JSON.stringify({type: 'pgr-test-nav', action: 'prev', idx: 0})}.n_clicks`,
		value: 1,
	}]
	assert.equal(
		pager.onClick([], [1], {...data, idx: 1}),
		noUpdate,
		'boundary navigation must not rewrite the pager store',
	)
}


main()
