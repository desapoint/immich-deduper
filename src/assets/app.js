window.dash_clientside = window.dash_clientside || {}

//============================================================================
// suppress page-specific callback errors for multi-page apply
// this is unfortunately a known limitation of the Dash multi-page framework
//
// if anyone have better solution, please tell me, thanks :)
//============================================================================
;(function(){
	const pageIds = ['sim-gvSim', 'sim-gvPnd', 'fetch-usr-select']
	const origErr = console.error
	console.error = function(...args){
		const msg = String(args[0]?.message || args[0] || '')
		if (msg.includes('nonexistent object')) {
			const matched = pageIds.find(id => msg.includes(id))
			if (matched) {
				console.debug(`[dash] skipped page-specific callback: ${matched}`)
				return
			}
		}
		if(msg.includes('Callback error updating') || msg.includes('Uncaught (in promise) DOMException: The operation was aborted.')){
			console.debug(`[dash] hot reload...`)
			return
		}
		origErr.apply(console, args)
	}
})()

const R = {
	mk(t, props, ... children){return React.createElement(t, props, ... children)},
}

const fmtDate = (timestamp) =>{
	const dt = new Date(timestamp)
	const yr = dt.getFullYear()
	const mo = String(dt.getMonth() + 1).padStart(2, '0')
	const dy = String(dt.getDate()).padStart(2, '0')
	const hr = String(dt.getHours()).padStart(2, '0')
	const mn = String(dt.getMinutes()).padStart(2, '0')
	const sc = String(dt.getSeconds()).padStart(2, '0')
	return `${yr}${mo}${dy} ${hr}:${mn}:${sc}`
}



// ============================================================================
// getStore( key ) - Get store data by id
//   // string id
//   dsh.getStore( 'store-mdl' )
//   // -> { id: null, cmd: null, ok: false, args: {}, msg: null }
//
//   // pattern matching id (object)
//   dsh.getStore( { type: "pgr-vg-pager-main-store", idx: 0 } )
//   // -> { showInfo: true, avFirstLast: true, ... }
//
// syncStore( key, data ) - Update store data, triggers listening callbacks
//   key: string id of the store
//   data: new data object to set
//
//   // Update pager to page 3 (triggers pager UI update + content reload)
//   const pgr = dsh.getStore( 'vg-pager-main-store' )
//   dsh.syncStore( 'vg-pager-main-store', { ...pgr, idx: 3 } )
//
//   // Update modal store
//   dsh.syncStore( 'store-mdl', { id: 'test', cmd: 'xxx', ok: true } )
// ============================================================================
const dsh = {
	noUpd: window.dash_clientside.no_update,
	syncStore(key, data){
		if (!window.dash_clientside || !window.dash_clientside.set_props) {
			console.error(`[mdlImg] error not found dash client side...`)
			return false
		}

		window.dash_clientside.set_props(key, {data: data}) //use dcc.Store need data property
		return true
	},

	getStore(key){
		const api = window.dash_component_api
		if (!api) return null
		const layout = api.getLayout(key)
		return layout && layout.props && layout.props.data
	},

	syncSte(cnt, selectedIds, stackCoverIds){
		const toIdSet = ids => new Set(Array.from(ids || []).map(Number))
		const selectedSet = toIdSet(selectedIds)
		if (stackCoverIds === undefined) stackCoverIds = window.Ste?.stackCoverIds || []
		const coverSet = toIdSet(stackCoverIds)
		const data = {
			cntTotal: cnt,
			selectedIds: Array.from(selectedSet),
			stackCoverIds: Array.from(coverSet),
		}
		const current = this.getStore('store-state')
		const sameIds = (ids, expected) => {
			if (!Array.isArray(ids) || ids.length !== expected.size) return false
			return ids.every(id => expected.has(Number(id)))
		}
		if (current
			&& Number(current.cntTotal || 0) === Number(data.cntTotal || 0)
			&& sameIds(current.selectedIds, selectedSet)
			&& sameIds(current.stackCoverIds, coverSet)) {
			return false
		}
		return this.syncStore('store-state', data)
	}
}



let latestSystemChecks = null
let systemCheckObserver = null
let systemCheckObserverTimeout = null

function applySystemCheckResults(sc, data){
	if (!sc || !Array.isArray(data)) return
	let expected = 0
	let applied = 0

	for ( const item of data){
		if (item.key === 'ver') continue
		expected++

		const div = sc.querySelector(`.chk-${item.key}`)
		if (!div) continue
		applied++

		const state = div.querySelector('.settings-status-state')
		div.classList.remove('is-valid', 'is-invalid', 'bg-danger', 'text-white', 'divtip')

		if (!item.ok) {
			if (state) {
				state.innerText = 'Issue'
				state.className = 'settings-status-state is-invalid'
			}
			div.classList.add('is-invalid', 'divtip')
			div.setAttribute('data-tooltip', (item.msg || []).join('\n'))
			div.setAttribute('data-check-status', 'invalid')
			div.style.cursor = 'help'
		}
		else {
			if (state) {
				state.innerText = 'Valid'
				state.className = 'settings-status-state is-valid'
			}
			div.classList.add('is-valid')
			div.removeAttribute('data-tooltip')
			div.setAttribute('data-check-status', 'valid')
			div.style.cursor = 'default'
		}
	}

	// Dash may attach the card before all status children exist. Keep retrying on
	// DOM mutations until every result has a corresponding rendered item.
	sc._systemChecks = applied === expected ? data : null
}

function syncSystemCheckResults(data){
	latestSystemChecks = data
	watchSystemCheckResults()
}

function stopSystemCheckObserver(){
	if (systemCheckObserver) systemCheckObserver.disconnect()
	systemCheckObserver = null
	if (systemCheckObserverTimeout) clearTimeout(systemCheckObserverTimeout)
	systemCheckObserverTimeout = null
}

function watchSystemCheckResults(){
	if (!Array.isArray(latestSystemChecks)) return
	if (window.location?.pathname !== '/') {
		stopSystemCheckObserver()
		return
	}

	const applyCurrent = () =>{
		const sc = document.querySelector('.card-system-cfgs')
		if (sc && sc._systemChecks !== latestSystemChecks) applySystemCheckResults(sc, latestSystemChecks)
		if (sc?._systemChecks === latestSystemChecks) {
			stopSystemCheckObserver()
			return true
		}
		return false
	}
	const applyAdded = mutations =>{
		if (!mutations) {
			return applyCurrent()
		}

		const cards = new Set()
		mutations.forEach(mutation => mutation.addedNodes?.forEach(node => {
			if (node.nodeType !== 1) return
			const card = node.matches?.('.card-system-cfgs')
				? node
				: node.closest?.('.card-system-cfgs') || node.querySelector?.('.card-system-cfgs')
			if (card) cards.add(card)
		}))
		cards.forEach(card => {
			if (card._systemChecks !== latestSystemChecks) applySystemCheckResults(card, latestSystemChecks)
		})
		if (Array.from(cards).some(card => card._systemChecks === latestSystemChecks)) stopSystemCheckObserver()
	}

	if (applyCurrent()) return
	if (!systemCheckObserver) {
		systemCheckObserver = new MutationObserver(applyAdded)
		systemCheckObserver.observe(document.body, {childList: true, subtree: true})
		systemCheckObserverTimeout = setTimeout(stopSystemCheckObserver, 5000)
	}
}

function onFetchedChk(loading, data){
	console.info(`[load] check data: ${JSON.stringify(data)}`)

	let errK = false
	let verItem = null
	for (const item of data) {
		if (item.key === 'ver') verItem = item
		else if (!item.ok && !errK) errK = item.key
	}
	syncSystemCheckResults(data)

	ui.mob.waitFor('#span-sys-chk', sp =>{


		TskWS.init(
			() =>{
				if (!sp) {Nfy.error(`[chk] span-sys-chk not exist?`); return}
				if (!errK) {
					sp.innerText = `ok`
					sp.classList.add('info')
				}
				else {
					sp.innerText = `Failed: ${errK}`
					sp.classList.add('red')
				}

				if (verItem && !verItem.ok) {
					let msg = verItem.msg.join('\n')
					let isNewVer = msg.includes('New version')

					if (isNewVer) {
						Nfy.warn(msg, 10000)
					} else {
						notify.load(msg, 'warn').run(30000)
					}

					sp.innerText = verItem.msg[0]
					sp.classList.remove('info',`second`)
					sp.classList.add('warn')
				} else if (verItem) sp.innerText = `ver:${verItem.msg[0]}`


				if (!errK) {
					loading.close()

					dsh.syncStore('store-sys', {ok: true})
					Nfy.info(`system check ok!`)
					return
				}

				loading.close()
				notify.erro(`system check failed`)
				Nfy.error(`[system] check ${errK} failed, please check your environment - ${fmtDate(Date.now())}`)

			},
			(msg) =>{
				if (!sp) {Nfy.error(`[chk] span-sys-chk not exist?`); return}
				sp.innerText = msg ? `Failed: ${msg}` : `Failed`
				sp.classList.add('red')
				loading.closeNo(`system check failed, ${msg}`)
			}
		)
	})

}

document.addEventListener('DOMContentLoaded', function(){
	document.addEventListener('click', event =>{
		const link = event.target.closest?.('a[href]')
		if (!link) return
		try {
			const target = new URL(link.href, window.location.href)
			if (target.origin === window.location.origin && target.pathname === '/') {
				setTimeout(watchSystemCheckResults, 0)
			}
		}
		catch (error) {}
	})
	window.addEventListener('popstate', () => setTimeout(watchSystemCheckResults, 0))

	ui.mob.waitFor('#div-notify', cbx =>{

		let ld = notify.load('Please wait, system checking...').run()
		fetch('/api/chk').then(rep => rep.json())
			.then(data =>onFetchedChk(ld, data))
			.catch(error =>notify(`[wst] Failed to get System Check Status, ${error}`, 'warn'))
	})

})
