
//------------------------------------------------------------------------
// mdlImg Client State Manager
//------------------------------------------------------------------------
const MdlImg = window.MdlImg = {
	state: {
		mdl: null,
		now: null,
		ste: null
	},

	init(mdl, now, ste){
		this.state.mdl = mdl
		this.state.now = now
		this.state.ste = ste

		if (ste) console.info(`[mdlImg] init ste, cntTotal[ ${ste.cntTotal} ] selected( ${ste.selectedIds.length} )[ ${ste.selectedIds} ]`)
		return this
	},

	setProps(id, props){
		if (typeof dash_clientside.set_props !== 'function') return false
		dash_clientside.set_props(id, props)
		return true
	},

	selectionState(){
		return window.Ste ? {
			cntTotal: Ste.cntTotal,
			selectedIds: Array.from(Ste.selectedIds),
			stackCoverIds: Array.from(Ste.stackCoverIds),
		} : {cntTotal: 0, selectedIds: [], stackCoverIds: []}
	},

	setCurrentAsset(){
		const asset = this.getCurrentAsset()
		window.currentMdlImgAutoId = asset?.autoId || null
	},

	openFromElement(element){
		if (!element?.id) return false
		let trigger
		try { trigger = JSON.parse(element.id) }
		catch (error) { return false }
		if (!['img-pop', 'img-pop-multi'].includes(trigger.type) || !trigger.aid) return false

		const stored = dsh.getStore('store-mdl-img') || {}
		const now = dsh.getStore('store-now') || {}
		const mdl = {
			open: true,
			imgUrl: `/api/img/${trigger.aid}?q=preview`,
			isMulti: trigger.type === 'img-pop-multi',
			curIdx: 0,
			hideHelp: stored.hideHelp ?? true,
			hideInfo: stored.hideInfo ?? true,
			modeH: stored.modeH ?? false,
		}
		if (mdl.isMulti) {
			const assets = now.sim?.assCur || []
			const index = assets.findIndex(asset => Number(asset.autoId) === Number(trigger.aid))
			if (index < 0) return false
			mdl.curIdx = index
		}

		this.init(mdl, now, this.selectionState())
		this.setCurrentAsset()
		this.apply()
		return true
	},

	apply(){
		const mdl = this.state.mdl
		if (!mdl) return false
		this.state.ste = this.selectionState()
		const asset = this.getCurrentAsset()
		this.setProps('img-modal', {is_open: !!mdl.open, className: this.getModeCss(mdl)})
		this.setProps('store-mdl-img', {data: mdl})
		if (!mdl.open) return true

		this.setProps('img-modal-content', {children: this.buildImageContent(mdl)})
		this.setProps('img-modal-status', {children: this.buildAssetStatus(mdl)})
		this.setProps('btn-img-prev', {style: this.getPrevButtonStyle(mdl)})
		this.setProps('btn-img-next', {style: this.getNextButtonStyle(mdl)})
		this.setProps('btn-img-select', {
			style: this.getSelectButtonStyle(mdl),
			children: this.getSelectButtonText(mdl, asset),
			color: this.getSelectButtonColor(mdl, asset),
		})
		this.setProps('img-modal-help', {className: this.getHelpClassName(mdl)})
		this.setProps('btn-img-help', {children: this.getHelpButtonContent()})
		this.setProps('img-modal-info', {className: this.getInfoClassName(mdl)})
		this.setProps('btn-img-info', {children: this.getInfoButtonContent()})
		this.setProps('img-modal-info-content', {children: this.getInfoContent(mdl)})
		this.setProps('btn-img-mode', {children: this.getModeContent(mdl)})
		return true
	},

	close(){
		if (!this.state.mdl) return false
		this.state.mdl = {...this.state.mdl, open: false}
		window.currentMdlImgAutoId = null
		return this.apply()
	},

	persistSettings(){
		const mdl = this.state.mdl
		if (!mdl || typeof fetch !== 'function') return
		fetch('/api/settings/image-preview', {
			method: 'POST',
			headers: {'Content-Type': 'application/json'},
			body: JSON.stringify({auto: !!mdl.modeH, help: !!mdl.hideHelp, info: !!mdl.hideInfo}),
			keepalive: true,
		}).catch(error => console.error('[mdlImg] Failed to save preview settings:', error))
	},

	navigate(direction){
		if (!this.state.mdl || !this.state.mdl.isMulti || !this.state.now?.sim?.assCur)
			return this.noUpdate(7)

		const assets = this.state.now.sim.assCur
		let newIdx = this.state.mdl.curIdx

		if (direction == 'prev' && newIdx > 0) newIdx = newIdx - 1
		else if (direction == 'next' && newIdx < assets.length - 1) newIdx = newIdx + 1
		else return this.noUpdate(7)

		const curAss = assets[newIdx]
		const newMdl = {
			... this.state.mdl,
			curIdx: newIdx,
			imgUrl: `/api/img/${curAss.autoId}?q=preview`
		}
		this.state.mdl = newMdl
		this.setCurrentAsset()

		const htms = this.buildImageContent(newMdl)
		const status = this.buildAssetStatus(newMdl)
		const prevStyle = this.getPrevButtonStyle(newMdl)
		const nextStyle = this.getNextButtonStyle(newMdl)
		const selectText = this.getSelectButtonText(newMdl, curAss)
		const selectColor = this.getSelectButtonColor(newMdl, curAss)

		console.log(`[MdlImg] navigated to idx[${newIdx}] autoId[${curAss.autoId}]`)

		return [newMdl, htms, status, prevStyle, nextStyle, selectText, selectColor]
	},

	navigateLocal(direction){
		const result = this.navigate(direction)
		if (result[0] === dash_clientside.no_update) return false
		return this.apply()
	},

	buildImageContent(mdl){
		const htms = []

		if (mdl.isMulti && this.state.now?.sim?.assCur && mdl.curIdx < this.state.now.sim.assCur.length) {
			const ass = this.state.now.sim.assCur[mdl.curIdx]

			if (ass && ass.vdoId) {
				htms.push(
					R.mk('div', {className: 'livephoto'},
						R.mk('video', {
							src: `/api/livephoto/${ass.autoId}`,
							id: `livephoto-modal-video-${ass.autoId}`,
							autoPlay: true,
							loop: true,
							muted: true,
							controls: false
						}),
						R.mk('div', {className: 'ctrls', id: 'livephoto-controls'},
							R.mk('button', {className: 'play-pause-btn', id: 'livephoto-play-pause'}, 'Pause'),
							R.mk('div', {className: 'progress-bar', id: 'livephoto-progress-bar'},
								R.mk('div', {className: 'progress-fill', id: 'livephoto-progress-fill'})
							),
							R.mk('div', {className: 'time-display', id: 'livephoto-time-display'}, '0:00 / 0:00')
						)
					)
				)
			}
			if (mdl.imgUrl) htms.push(R.mk('img', {src: mdl.imgUrl}))

		}
		else if (mdl.imgUrl) htms.push(R.mk('img', {src: mdl.imgUrl}))

		return htms
	},

	buildAssetStatus(mdl){
		if (!mdl.isMulti || !this.state.now?.sim?.assCur || mdl.curIdx >= this.state.now.sim.assCur.length) return []

		const ass = this.state.now.sim.assCur[mdl.curIdx]
		if (!ass) return []

		return [
			R.mk('span', {className: 'viewer-asset-id'}, `Asset #${ass.autoId}`),
			R.mk('span', {className: 'viewer-position'}, `${mdl.curIdx + 1} of ${this.state.now.sim.assCur.length}`),
			ass.simGIDs?.length
				? R.mk('span', {className: 'viewer-groups'}, `Groups ${ass.simGIDs.join(', ')}`)
				: null
		]
	},

	getPrevButtonStyle(mdl){
		if (!mdl.isMulti || !this.state.now?.sim?.assCur || this.state.now.sim.assCur.length <= 1) return {display: 'none'}

		const disabled = mdl.curIdx <= 0
		return {
			display: 'grid',
			opacity: disabled ? '0.28' : '1',
			pointerEvents: disabled ? 'none' : 'auto'
		}
	},

	getNextButtonStyle(mdl){
		if (!mdl.isMulti || !this.state.now?.sim?.assCur || this.state.now.sim.assCur.length <= 1) return {display: 'none'}

		const disabled = mdl.curIdx >= this.state.now.sim.assCur.length - 1
		return {
			display: 'grid',
			opacity: disabled ? '0.28' : '1',
			pointerEvents: disabled ? 'none' : 'auto'
		}
	},

	getSelectButtonText(mdl, curAss){
		if (!mdl.isMulti || !curAss) return 'Select image'

		const isSelected = this.state.ste?.selectedIds?.includes(curAss.autoId)
		return isSelected ? 'Selected' : 'Select image'
	},

	getSelectButtonColor(mdl, curAss){
		if (!mdl.isMulti || !curAss) return 'primary'

		const isSelected = this.state.ste?.selectedIds?.includes(curAss.autoId)
		return isSelected ? 'success' : 'primary'
	},

	syncSelectState(aid = window.currentMdlImgAutoId){
		if (!aid || !window.Ste) return false
		const button = document.getElementById('btn-img-select')
		if (!button) return false

		const selected = Ste.selectedIds.has(Number(aid))
		const text = selected ? 'Selected' : 'Select image'
		const color = selected ? 'success' : 'primary'
		const changed = button.textContent !== text || !button.classList.contains(`btn-${color}`)
		button.textContent = text
		button.classList.toggle('btn-success', selected)
		button.classList.toggle('btn-primary', !selected)
		if (changed && typeof dash_clientside.set_props === 'function')
			dash_clientside.set_props('btn-img-select', {children: text, color})
		return selected
	},

	toggleCurrentSelection(){
		const aid = Number(window.currentMdlImgAutoId)
		if (!aid || !window.Ste) return false
		Ste.toggle(aid)
		Ste.sync()
		console.log('[mdlImg] Toggled autoId:', aid)
		return true
	},

	noUpdate(cnt){return Array(cnt).fill(dash_clientside.no_update)},

	updMdl(){
		if (!this.state.mdl || !this.state.mdl.open) return this.noUpdate(15)

		const mdl = this.state.mdl
		let asset = this.getCurrentAsset()

		return [
			mdl.open,
			this.buildImageContent(mdl),
			this.buildAssetStatus(mdl),
			this.getPrevButtonStyle(mdl),
			this.getNextButtonStyle(mdl),
			this.getSelectButtonStyle(mdl),
			this.getSelectButtonText(mdl, asset),
			this.getSelectButtonColor(mdl, asset),
			this.getHelpClassName(mdl),
			this.getHelpButtonContent(),
			this.getInfoClassName(mdl),
			this.getInfoButtonContent(),
			this.getInfoContent(mdl),
			this.getModeCss(mdl),
			this.getModeContent(mdl),
		]
	},

	getCurrentAsset(){
		if (!this.state.mdl?.isMulti || !this.state.now?.sim?.assCur) return null

		const idx = this.state.mdl.curIdx
		const assets = this.state.now.sim.assCur
		return (idx >= 0 && idx < assets.length) ? assets[idx] : null
	},

	getSelectButtonStyle(mdl){return mdl.isMulti ? {display: 'inline-flex'} : {display: 'none'}},

	getInfoContent(mdl){
		if (!mdl.isMulti || !this.state.now?.sim?.assCur) return []

		const ass = this.getCurrentAsset()
		if (!ass) return []

		const assetRows = [
			R.mk('tr', {},
				R.mk('td', {}, 'Local ID'),
				R.mk('td', {},
					R.mk('span', {className: 'tag'}, `#${ass.autoId}`),
					R.mk('span', {className: 'tag'}, `@${ass.simGIDs?.join(',') || ''}`)
				)
			),
			R.mk('tr', {},
				R.mk('td', {}, 'Immich ID'),
				R.mk('td', {}, R.mk('span', {className: 'tag sm second'}, ass.id))
			),
			R.mk('tr', {},
				R.mk('td', {}, 'Filename'),
				R.mk('td', {}, ass.originalFileName)
			),
			R.mk('tr', {},
				R.mk('td', {}, 'Path'),
				R.mk('td', {}, ass.originalPath )
			)
		]

		const exifRows = this.buildExifRows(ass)
		const allRows = [... assetRows, ... exifRows]

		return R.mk('table', {className: 'table-sm table-striped', style: {width: '100%'}},
			R.mk('tbody', {}, ... allRows)
		)
	},

	buildExifRows(asset){
		const rows = []

		if (!asset.jsonExif) return rows

		const exifMap = {
			'exifImageWidth': 'Width',
			'exifImageHeight': 'Height',
			'fileSizeInByte': 'File Size',
			'dateTimeOriginal': 'Capture Time',
			'modifyDate': 'Modify Time',
			'make': 'Camera Brand',
			'model': 'Camera Model',
			'lensModel': 'Lens',
			'fNumber': 'Aperture',
			'focalLength': 'Focal Length',
			'exposureTime': 'Exposure Time',
			'iso': 'ISO',
			'orientation': 'Orientation',
			'latitude': 'Latitude',
			'longitude': 'Longitude',
			'city': 'City',
			'state': 'State',
			'country': 'Country',
			'description': 'Description',
			'fps': 'Frame Rate'
		}

		for ( const [key, displayKey] of Object.entries(exifMap) ){
			if (key in asset.jsonExif && asset.jsonExif[key] != null) {
				let value = asset.jsonExif[key]
				let displayValue = value

				if (key == 'fileSizeInByte') displayValue = this.formatFileSize(value)
				else if (key == 'focalLength' && typeof value == 'number') displayValue = `${value} mm`
				else if (key == 'fNumber' && typeof value == 'number') displayValue = `f/${value}`
				else if (value) displayValue = this.formatDate(value)

				if (displayValue) {
					rows.push(
						R.mk('tr', {},
							R.mk('td', {}, displayKey),
							R.mk('td', {}, displayValue)
						)
					)
				}
			}
		}

		return rows
	},

	formatFileSize(value){
		if (typeof value == 'number') {
			if (value > 1024 * 1024) {
				return `${(value / (1024 * 1024)).toFixed(2)} MB`
			}
			else if (value > 1024) {
				return `${(value / 1024).toFixed(2)} KB`
			}
			else {
				return `${value} B`
			}
		}
		return value
	},

	formatDate(value){
		const str = String(value)
		if (str.includes('T') && str.includes('+')) {
			const parts = str.split('T')
			if (parts.length == 2 && parts[1].includes('+')) {
				const timePart = parts[1]
				if (timePart.includes('.') && (timePart.includes('+') || timePart.includes('-'))) {
					const timeParts = timePart.split('.')
					if (timeParts.length == 2) {
						const baseTime = timeParts[0]
						const tzPart = timeParts[1].includes('+') ?
							timeParts[1].split('+')[1] : timeParts[1].split('-')[1]
						const sign = timeParts[1].includes('+') ? '+' : '-'
						const tz = `${baseTime}${sign}${tzPart}`
						return `${parts[0]} ${tz}`
					}
				}
			}
		}
		return str
	},


	getHelpClassName(mdl){
		if (!mdl.isMulti) return 'hide'
		return mdl.hideHelp ? 'help collapsed' : 'help'
	},
	getHelpButtonContent(){
		return [
			R.mk('i', {className: 'bi bi-keyboard'}),
			R.mk('span', {className: 'visually-hidden'}, 'Shortcuts')
		]
	},
	getInfoClassName(mdl){
		if (!mdl.isMulti) return 'hide'
		return mdl.hideInfo ? 'info collapsed' : 'info'
	},
	getInfoButtonContent(){
		return [
			R.mk('i', {className: 'bi bi-info-circle'}),
			R.mk('span', {className: 'visually-hidden'}, 'Details')
		]
	},
	getModeTxt(mdl){return mdl.modeH ? 'Actual size' : 'Fit screen'},
	getModeContent(mdl){
		return [
			R.mk('i', {className: mdl.modeH ? 'bi bi-arrows-angle-expand' : 'bi bi-arrows-fullscreen'}),
			R.mk('span', {className: 'img-viewer-mode-label'}, this.getModeTxt(mdl))
		]
	},
	getModeCss(mdl){return mdl.modeH ?'img-pop auto' : 'img-pop'},

	toggleHelp(){
		if (!this.state.mdl) return this.noUpdate(3)

		const newMdl = {
			... this.state.mdl,
			hideHelp: !this.state.mdl.hideHelp
		}

		const helpCss = this.getHelpClassName(newMdl)
		const helpTxt = this.getHelpButtonContent()
		this.state.mdl = newMdl

		return [newMdl, helpCss, helpTxt]
	},

	toggleInfo(){
		if (!this.state.mdl) return this.noUpdate(3)

		const newMdl = {
			... this.state.mdl,
			hideInfo: !this.state.mdl.hideInfo
		}

		const infoCss = this.getInfoClassName(newMdl)
		const infoTxt = this.getInfoButtonContent()
		this.state.mdl = newMdl

		return [newMdl, infoCss, infoTxt]
	},

	toggleMode(){
		if (!this.state.mdl) return this.noUpdate(3)

		const newMdl = {
			... this.state.mdl,
			modeH: !this.state.mdl.modeH
		}

		let newCss = this.getModeCss(newMdl)
		let newTxt = this.getModeContent(newMdl)
		this.state.mdl = newMdl

		return [newMdl, newCss, newTxt]
	}
}


//------------------------------------------------------------------------
// mdlImg
//------------------------------------------------------------------------
window.dash_clientside.mdlImg = {
	onStoreToDummy(mdl_data, now_data){
		if (mdl_data && mdl_data.isMulti && now_data && now_data.sim && now_data.sim.assCur) {
			let curIdx = mdl_data.curIdx
			let assets = now_data.sim.assCur

			if (curIdx >= 0 && curIdx < assets.length) {
				let curAsset = assets[curIdx]
				window.currentMdlImgAutoId = curAsset.autoId
				console.log('[mdlImg] Set current autoId for hotkeys:', window.currentMdlImgAutoId)
			}
		}
		else {
			window.currentMdlImgAutoId = null
		}
		return dash_clientside.no_update
	},
	onNavigation(prevClk, nextClk, now, ste, mdl){
		const ctx = dash_clientside.callback_context
		if (!ctx.triggered.length) return dash_clientside.no_update

		MdlImg.init(mdl, now, ste)

		const trigId = ctx.triggered[0].prop_id
		if (trigId.includes('btn-img-prev')) return MdlImg.navigate('prev')
		if (trigId.includes('btn-img-next')) return MdlImg.navigate('next')

		return dash_clientside.no_update
	},

	onUpdMdl(mdl, now, ste){
		MdlImg.init(mdl, now, ste)
		return MdlImg.updMdl()
	},

	onHelpToggle(nclk, mdl){
		if (!nclk) return Array(3).fill(dash_clientside.no_update)

		MdlImg.init(mdl, null, null)
		return MdlImg.toggleHelp()
	},

	onInfoToggle(nclk, mdl){
		if (!nclk) return Array(3).fill(dash_clientside.no_update)

		MdlImg.init(mdl, null, null)
		return MdlImg.toggleInfo()
	},

	onModeToggle(nclk, mdl){
		if (!nclk) return Array(3).fill(dash_clientside.no_update)

		MdlImg.init(mdl, null, null)
		return MdlImg.toggleMode()
	}
}


document.addEventListener('click', function(ev){
	const target = ev.target
	const image = target.closest?.('[id*=\'"type":"img-pop\']')
	if (image && MdlImg.openFromElement(image)) {
		ev.preventDefault()
		ev.stopPropagation()
		return
	}

	const action = target.closest?.('#btn-img-select, #btn-img-prev, #btn-img-next, #btn-img-help, #btn-img-info, #btn-img-mode, #img-modal .btn-close')
	if (!action) return
	ev.preventDefault()
	ev.stopPropagation()

	if (action.id === 'btn-img-select') MdlImg.toggleCurrentSelection()
	else if (action.id === 'btn-img-prev') MdlImg.navigateLocal('prev')
	else if (action.id === 'btn-img-next') MdlImg.navigateLocal('next')
	else if (action.id === 'btn-img-help') { MdlImg.toggleHelp(); MdlImg.apply(); MdlImg.persistSettings() }
	else if (action.id === 'btn-img-info') { MdlImg.toggleInfo(); MdlImg.apply(); MdlImg.persistSettings() }
	else if (action.id === 'btn-img-mode') { MdlImg.toggleMode(); MdlImg.apply(); MdlImg.persistSettings() }
	else MdlImg.close()
})


document.addEventListener('keydown', function(ev){
	const div = document.querySelector('#img-modal')

	if (!div || !div.parentElement.classList.contains('show')) return
	if (ev.key == 'ArrowLeft' || ev.key == 'h') {
		ev.preventDefault()
		const btn = document.querySelector('#btn-img-prev')
		if (btn && btn.style.pointerEvents != 'none') btn.click()
	}
	else if (ev.key == 'ArrowRight' || ev.key == 'l') {
		ev.preventDefault()
		const btn = document.querySelector('#btn-img-next')
		if (btn && btn.style.pointerEvents != 'none') btn.click()
	}
	else if (ev.key == ' ') {
		ev.preventDefault()
		MdlImg.toggleCurrentSelection()
	}
	else if (ev.key == 'Escape' || ev.key == 'q') {
		ev.preventDefault()
		const btn = div.querySelector('.btn-close')
		if (btn) btn.click()
	}
	else if (ev.key == 'm') {
		ev.preventDefault()
		const btn = div.querySelector('#btn-img-mode')
		if (btn) btn.click()
	}
	else if (ev.key == 'i') {
		ev.preventDefault()
		const btn = div.querySelector('#btn-img-info')
		if (btn) btn.click()
	}

	else if (ev.key == '?') {
		ev.preventDefault()
		const btn = div.querySelector('#btn-img-help')
		if (btn) btn.click()
	}
})
