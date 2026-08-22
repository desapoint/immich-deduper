window.dash_clientside = window.dash_clientside || {}

window.dash_clientside.pager = {
	onSizeChange(sizeValues, pagerData){
		const triggered = dash_clientside.callback_context.triggered?.[0]
		const size = Number.parseInt(triggered?.value, 10)
		if (!pagerData || !Number.isFinite(size) || size <= 0 || size === pagerData.size)
			return dash_clientside.no_update

		const total = Number(pagerData.cnt) || 0
		const totalPages = total > 0 ? Math.ceil(total / size) : 1
		return {
			...pagerData,
			size,
			idx: Math.max(1, Math.min(Number(pagerData.idx) || 1, totalPages)),
		}
	},

	onClick(pageClicks, navClicks, pagerData){
		const triggered = dash_clientside.callback_context.triggered?.[0]
		if (!pagerData || !triggered?.prop_id || !triggered.value)
			return dash_clientside.no_update

		let patternId
		try { patternId = JSON.parse(triggered.prop_id.split('.')[0]) }
		catch (_) { return dash_clientside.no_update }

		const current = Math.max(1, Number(pagerData.idx) || 1)
		const size = Math.max(1, Number(pagerData.size) || 1)
		const total = Number(pagerData.cnt) || 0
		const totalPages = total > 0 ? Math.ceil(total / size) : 1
		let next = current

		if (patternId.page != null) next = Number(patternId.page)
		else if (patternId.action === 'first') next = 1
		else if (patternId.action === 'last') next = totalPages
		else if (patternId.action === 'prev') next = Math.max(1, current - 1)
		else if (patternId.action === 'next') next = Math.min(totalPages, current + 1)
		else return dash_clientside.no_update

		next = Math.max(1, Math.min(next, totalPages))
		return next === current ? dash_clientside.no_update : {...pagerData, idx: next}
	},
}
