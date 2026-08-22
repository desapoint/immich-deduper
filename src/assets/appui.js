const ui = window.ui = {

	mob: {
		waitFor(selector, callback, logPrefix){
			const dst = document.querySelector(selector)
			const log = typeof logPrefix == 'string' && logPrefix.length > 0

			if (!logPrefix) logPrefix = selector

			if (dst) {
				if (log) console.log(`${logPrefix} Found element:`, dst)
				callback(dst)
			}
			else {
				if (log) console.log(`${logPrefix} Element not found, initializing observer for ${selector}`)
				const observer = new MutationObserver(function(){
					const dst = document.querySelector(selector)
					if (dst) {
						if (log) console.log(`${logPrefix} Element found via observer:`, dst)
						observer.disconnect()
						callback(dst)
					}
				})
				observer.observe(document.body, {childList: true, subtree: true})
			}
		},

		waitAll(selector, callback, logPrefix, timeout = 9000){
			const dsts = document.querySelectorAll(selector)
			const log = typeof logPrefix == 'string' && logPrefix.length > 0
			if (!logPrefix) logPrefix = selector

			if (dsts.length > 0) {
				if (log) console.log(`${logPrefix} Found ${dsts.length} elements`)
				callback(dsts)
			}
			else {
				if (log) console.log(`${logPrefix} No elements found, initializing observer`)
				const observer = new MutationObserver(function(){
					const dsts = document.querySelectorAll(selector)
					if (dsts.length > 0) {
						if (log) console.log(`${logPrefix} Found ${dsts.length} elements via observer`)
						clearTimeout(tid)
						observer.disconnect()
						callback(dsts)
					}
				})
				observer.observe(document.body, {childList: true, subtree: true})

				const tid = setTimeout(() =>{
					if (log) console.log(`${logPrefix} Timeout after ${timeout}ms`)
					observer.disconnect()
				}, timeout)
			}
		}

	},

	init(){
		// Force DOM reflow to get accurate element dimensions
		// When an element is first shown (display: block), CSS properties like
		// white-space: nowrap and min-width: fit-content may not be fully applied yet,
		// causing getBoundingClientRect() to return incorrect dimensions on first call
		Element.prototype.refreshSize = function(){
			this.style.visibility = 'hidden'
			this.style.position = 'absolute'
			this.style.left = '0'
			this.style.top = '0'

			this.offsetHeight  // Trigger layout reflow

			this.style.visibility = 'visible'
		}
	},

	poptip: {
		baseZIndex: 1000,
		_hideTimer: null,
		_activeTipId: null,

		delayHide(tipId, delay = 3000){
			clearTimeout(this._hideTimer)
			this._hideTimer = setTimeout(() =>{
				const tipEl = document.getElementById(tipId)
				this.hide(tipEl)
				this._activeTipId = null
			}, delay)
		},

		cancelHide(){
			clearTimeout(this._hideTimer)
		},

		attachToDocument(tipEl){
			if (!tipEl || tipEl.parentNode === document.body) return
			tipEl._poptipHomeParent = tipEl.parentNode
			tipEl._poptipHomeNext = tipEl.nextSibling
			document.body.appendChild(tipEl)
		},

		restoreHome(tipEl){
			if (!tipEl || !tipEl._poptipHomeParent) return
			const parent = tipEl._poptipHomeParent
			const next = tipEl._poptipHomeNext
			if (parent.isConnected !== false) {
				parent.insertBefore(tipEl, next && next.parentNode === parent ? next : null)
			}
			else tipEl.remove()
			tipEl._poptipHomeParent = null
			tipEl._poptipHomeNext = null
		},

		hide(tipEl){
			if (!tipEl) return
			clearTimeout(tipEl._poptipHideTimer)
			tipEl.style.transition = 'opacity 0.3s ease'
			tipEl.style.opacity = '0'
			tipEl._poptipHideTimer = setTimeout(() =>{
				tipEl.style.display = 'none'
				tipEl.style.opacity = '1'
				tipEl.style.transition = ''
				const arrow = tipEl.querySelector('.poptip-arrow')
				if (arrow) arrow.remove()
				this.restoreHome(tipEl)
				tipEl._poptipHideTimer = null
			}, 300)
		},

		show(tipId, triggerEl, forceToggle = false){
			const tipEl = document.getElementById(tipId)
			if (!tipEl) return

			this.cancelHide()
			clearTimeout(tipEl._poptipHideTimer)
			tipEl._poptipHideTimer = null
			tipEl.style.opacity = '1'
			tipEl.style.transition = ''

			if (this._activeTipId && this._activeTipId !== tipId) {
				const prevTip = document.getElementById(this._activeTipId)
				this.hide(prevTip)
			}
			this._activeTipId = tipId

			const isVisible = tipEl.style.display === 'block'
			if (forceToggle && isVisible) {
				this.hide(tipEl)
				this._activeTipId = null
				return
			}

			this.attachToDocument(tipEl)
			tipEl.style.display = 'block'

			requestAnimationFrame(() =>{
				const posInfo = this.position(tipEl, triggerEl)

				const existingArrow = tipEl.querySelector('.poptip-arrow')
				if (existingArrow) existingArrow.remove()

				const arrow = document.createElement('i')
				arrow.className = 'poptip-arrow'

				if (posInfo.direction === 'right') {
					arrow.classList.add('bi', 'bi-caret-left-fill')
					arrow.style.left = '-12px'
					arrow.style.top = '50%'
					arrow.style.transform = 'translateY(-50%)'
				} else if (posInfo.direction === 'top') {
					arrow.classList.add('bi', 'bi-caret-down-fill')
					arrow.style.bottom = '-12px'
					arrow.style.left = '50%'
					arrow.style.transform = 'translateX(-50%)'
				} else if (posInfo.direction === 'bottom') {
					arrow.classList.add('bi', 'bi-caret-up-fill')
					arrow.style.top = '-12px'
					arrow.style.left = '50%'
					arrow.style.transform = 'translateX(-50%)'
				}

				tipEl.appendChild(arrow)
			})

			if (!tipEl._mouseLeaveEventsBound) {
				tipEl.addEventListener('mouseenter', () =>{
					this.cancelHide()
				})
				tipEl.addEventListener('mouseleave', () =>{
					this.hide(tipEl)
					this._activeTipId = null
				})
				tipEl._mouseLeaveEventsBound = true
			}
		},


		position(tipEl, triggerEl){
			tipEl.refreshSize()

			const triggerRect = triggerEl.getBoundingClientRect()
			const tipRect = tipEl.getBoundingClientRect()
			const scrollX = window.pageXOffset || document.documentElement.scrollLeft
			const scrollY = window.pageYOffset || document.documentElement.scrollTop
			const viewWidth = window.innerWidth


			let direction

			if (triggerRect.right + tipRect.width + 25 <= viewWidth) {
				direction = 'right'
				tipEl.style.left = `${triggerRect.right + scrollX + 15}px`
				tipEl.style.top = `${triggerRect.top + scrollY + triggerRect.height / 2}px`
				tipEl.style.transform = 'translateY(-50%)'
			}
			else if (triggerRect.top - tipRect.height - 25 >= 0) {
				direction = 'top'
				tipEl.style.left = `${triggerRect.left + scrollX + triggerRect.width / 2}px`
				tipEl.style.top = `${triggerRect.top + scrollY - 15}px`
				tipEl.style.transform = 'translate(-50%, -100%)'
			}
			else {
				direction = 'bottom'
				tipEl.style.left = `${triggerRect.left + scrollX + triggerRect.width / 2}px`
				tipEl.style.top = `${triggerRect.bottom + scrollY + 15}px`
				tipEl.style.transform = 'translateX(-50%)'
			}

			tipEl.style.position = 'absolute'
			tipEl.style.zIndex = this.baseZIndex++

			// viewport boundary clamp
			tipEl.offsetHeight
			const finalRect = tipEl.getBoundingClientRect()
			const pad = 8
			if (finalRect.right > viewWidth - pad) {
				const ov = finalRect.right - (viewWidth - pad)
				tipEl.style.left = `${parseFloat(tipEl.style.left) - ov}px`
			}
			if (finalRect.left < pad) {
				tipEl.style.left = `${parseFloat(tipEl.style.left) + (pad - finalRect.left)}px`
			}

			return {direction}
		},

	}
}


//========================================================================
// global
//========================================================================
document.addEventListener('DOMContentLoaded', () =>{
	const root = document.body

	function bindEvts(){
		const sps = document.querySelectorAll('span[data-tip-id]')
		sps.forEach(span =>{
			if (span._poptipEventsBound) return

			span.tabIndex = 0
			span.setAttribute('role', 'button')
			span.setAttribute('aria-haspopup', 'true')
			span.addEventListener('mouseenter', function(){
				const tipId = this.getAttribute('data-tip-id')
				ui.poptip.cancelHide()
				ui.poptip.show(tipId, this)
			})
			span.addEventListener('mouseleave', function(){
				const tipId = this.getAttribute('data-tip-id')
				ui.poptip.delayHide(tipId)
			})
			span.addEventListener('focus', function(){
				ui.poptip.cancelHide()
				ui.poptip.show(this.getAttribute('data-tip-id'), this)
			})
			span.addEventListener('blur', function(){
				ui.poptip.delayHide(this.getAttribute('data-tip-id'))
			})

			span._poptipEventsBound = true
		})
	}

	bindEvts()

	const obs = new MutationObserver(muts =>{
		muts.forEach(mutation =>{if (mutation.type == 'childList') bindEvts()})
	})

	obs.observe(root, {childList: true, subtree: true})


	root.addEventListener('click', async (event) =>{
		const dst = event.target

		const span = dst.closest('span[class*="tag"]:not(.no)')
		if (span) {
			if (span.hasAttribute('data-tip-id')) {
				const tipId = span.getAttribute('data-tip-id')
				ui.poptip.show(tipId, span, true)  // forceToggle = true
				return
			}

			const textToCopy = span.textContent

			if (navigator.clipboard && navigator.clipboard.writeText) {
				try{
					await navigator.clipboard.writeText(textToCopy)
					console.log('copy: ' + textToCopy)
					notify(`copy! ${textToCopy}`)
				}
				catch (err){
					console.error('copy failed', err)
				}
			}
			else {
				console.warn('Not support Clipboard API')
				const tempInput = document.createElement('textarea')
				tempInput.value = textToCopy
				document.body.appendChild(tempInput)
				tempInput.select()
				try{
					document.execCommand('copy')

					notify(`copy! ${textToCopy}`)
					console.log('copy!(old) ' + textToCopy)
				}
				catch (err){
					console.error('copy(old) failed', err)
				}
				document.body.removeChild(tempInput)
			}
		}
	})

	root.addEventListener('keydown', event =>{
		if (event.key !== 'Enter' && event.key !== ' ') return
		const copyTarget = event.target.closest('span.sim-card-filename')
		if (!copyTarget) return
		event.preventDefault()
		copyTarget.click()
	})
})

ui.init()

window.dash_clientside.ui = {
	toggleGridInfo(checked){
		document.body.classList.toggle('show-grid-info', checked)
		document.querySelectorAll('.sim-card-details').forEach(details => { details.open = !!checked })
		return dash_clientside.no_update
	}
}

//========================================================================
// showGridInfo toggle
//========================================================================
ui.mob.waitFor('#sets-showGridInfo', cbx =>{
	const inp = cbx.querySelector('input[type="checkbox"]')
	if (!inp) return

	if (inp.checked) document.body.classList.add('show-grid-info')

	inp.addEventListener('change', () =>{
		document.body.classList.toggle('show-grid-info', inp.checked)
		document.querySelectorAll('.sim-card-details').forEach(details => { details.open = inp.checked })
	})
})
