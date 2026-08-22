
const Ste = window.Ste = {
	cntTotal: 0,
	selectedIds: new Set(),
	stackCoverIds: new Set(),
	_lastSyncHash: null,
	_domCache: null,

	invalidateDomCache()
	{
		this._domCache = null
	},

	refreshDomCache()
	{
		const cards = Array.from( document.querySelectorAll( '[id*="card-select"]' ) )
		const byAid = new Map()
		const groups = new Map()
		const stackedGroups = new Set()
		const unstackedGroups = new Set()

		cards.forEach( card => {
			const aid = this.extractAssetIdBy( card )
			if ( !aid ) return
			const groupId = String( card.getAttribute( 'data-group-id' ) || '' )
			const stacked = card.getAttribute( 'data-stacked' ) === 'true'
			byAid.set( aid, {card, groupId, stacked} )
			if ( groupId ) {
				if ( !groups.has( groupId ) ) groups.set( groupId, [] )
				groups.get( groupId ).push( card )
				stacked ? stackedGroups.add( groupId ) : unstackedGroups.add( groupId )
			}
		} )

		const mainIds = Array.from( document.querySelectorAll( '.sim.main [id*="card-select"]' ) )
			.map( card => this.extractAssetIdBy( card ) )
			.filter( aid => aid )
		const coverButtons = Array.from( document.querySelectorAll( '[id*=\'"type":"sim-stack-cover"\']' ) )
		const groupStackButtons = new Map()
		const groupActionButtons = new Map()

		document.querySelectorAll( '[id*=\'"type":"sim-stack-group"\']' ).forEach( button => {
			try { groupStackButtons.set( String( JSON.parse( button.id ).id ), button ) }
			catch ( e ) { console.error( '[Ste] Invalid group stack button id:', e ) }
		} )
		document.querySelectorAll( '[id*=\'"type":"sim-group-action"\']' ).forEach( button => {
			try {
				const patternId = JSON.parse( button.id )
				const groupId = String( patternId.id )
				if ( !groupActionButtons.has( groupId ) ) groupActionButtons.set( groupId, [] )
				groupActionButtons.get( groupId ).push( {button, action: patternId.action} )
			}
			catch ( e ) { console.error( '[Ste] Invalid group action button id:', e ) }
		} )

		this._domCache = {
			cards, byAid, groups, mainIds, coverButtons,
			stackedGroups, unstackedGroups, groupStackButtons, groupActionButtons,
		}
		return this._domCache
	},

	getDomCache()
	{
		return this._domCache || this.refreshDomCache()
	},

	getCard( aid )
	{
		return this.getDomCache().byAid.get( Number( aid ) )?.card || null
	},

	isTaskRunning()
	{
		const task = typeof dsh !== 'undefined' && typeof dsh.getStore === 'function'
			? dsh.getStore( 'store-tsk' )
			: null
		return !!( task?.id && task?.cmd )
	},

	init( cnt )
	{
		this.invalidateDomCache()
		this.cntTotal = cnt
		this.selectedIds.clear()
		this.stackCoverIds.clear()
		console.log( `[Ste] Initialized with ${ cnt } assets, selected[ ${ this.selectedIds.size } ]` )

		dsh.syncSte( this.cntTotal, this.selectedIds )
	},

	initSilent( cnt )
	{
		this.invalidateDomCache()
		this.cntTotal = cnt
		this.selectedIds.clear()
		this.stackCoverIds.clear()
		console.log( `[Ste] Silent init with ${ cnt } assets, selected[ ${ this.selectedIds.size } ]` )
	},

	toggle( aid, card = null )
	{
		if ( !card ) card = this.getCard( aid )
		const groupId = card?.getAttribute( 'data-group-id' ) || null
		const clearedCover = this.stackCoverIds.has( aid )
		if ( this.selectedIds.has( aid ) )
		{
			this.selectedIds.delete( aid )
			this.stackCoverIds.delete( aid )
		}
		else this.selectedIds.add( aid )

		this.updCss( aid, card )
		if ( clearedCover ) this.updStackCoverButtons( groupId )
		this.updBtns( groupId )
	},

	async updCss( aid, card = null )
	{
		// console.log( `[Ste] updCss called for aid: ${aid} (type: ${typeof aid})` )

		if ( !card ) card = this.getCard( aid ) || await getCardById( aid )
		if ( !card )
		{
			console.error( `[Ste] No cards found for ${ aid }` )

			const allCards = document.querySelectorAll( `[id*='"type":"card-select"']` )
			console.log( `[Ste] Available cards:` )
			allCards.forEach( ( c, idx ) => {
				try
				{
					const idAttr = JSON.parse( c.id )
					console.log( `[Ste] Card[${ idx }] id[${ idAttr.id }] (type: ${ typeof idAttr.id }), type=${ idAttr.type }` )
				}
				catch ( e )
				{
					console.log( `[Ste] Card ${ idx }: parse error for ${ c.id }` )
				}
			} )
			return false
		}

		const par = card.closest( '.card' )
		const cbx = card.querySelector( 'input[type="checkbox"]' )
		const isSelected = this.selectedIds.has( aid )

		// console.log( `[Ste] updCss ${aid}: isSelected[${isSelected}], parentCard[${!!par}], checkbox[${!!cbx}]` )

		if ( !par ) console.error( `[updCss] not found aid[${ aid }] card` )

		if ( par )
		{
			par.classList[ isSelected ? 'add' : 'remove' ]( 'checked' )
			// console.log( `[Ste:updCss] Updated card ${aid} visual state: ${isSelected ? 'checked' : 'unchecked'}` )
		}

		if ( cbx ) {
			cbx.checked = isSelected
			// console.info( `[updCss] aid[${aid}] cbx.checked[${isSelected}]` )
		}
		return isSelected && !!cbx
	},

	updBtns( groupId = null )
	{
		const cntSel = this.selectedIds.size
		const cntAll = this.cntTotal
		const cntDiff = Math.max(0, cntAll - cntSel)
		const cache = this.getDomCache()
		const isTaskRunning = this.isTaskRunning()

		const btnRm = document.getElementById( 'sim-btn-RmSel' )
		const btnRS = document.getElementById( 'sim-btn-OkSel' )
		const btnAllSelect = document.getElementById( 'sim-btn-AllSelect' )
		const btnAllCancel = document.getElementById( 'sim-btn-AllCancel' )
		const btnSelMns = document.getElementById( 'sim-btn-SelectMns' )
		const btnSelStacked = document.getElementById( 'sim-btn-SelectStacked' )
		const btnSelUnstacked = document.getElementById( 'sim-btn-SelectUnstacked' )
		const btnStack = document.getElementById( 'sim-btn-Stack' )
		const txtCntSel = document.getElementById( 'sim-txt-cnt-sel' )
		const selectedGroups = new Set()
		this.selectedIds.forEach( aid => {
			const selectedGroupId = cache.byAid.get( Number( aid ) )?.groupId
			if ( selectedGroupId ) selectedGroups.add( selectedGroupId )
		} )

		if ( btnRm ) {
			btnRm.textContent = 'Delete selected'
			btnRm.title = `Delete ${ cntSel } selected images and keep ${ cntDiff } others`
			btnRm.disabled = isTaskRunning || cntSel == 0
		}
		if ( btnRS ) {
			btnRS.textContent = 'Keep selected'
			btnRS.title = `Keep ${ cntSel } selected images and delete ${ cntDiff } others`
			btnRS.disabled = isTaskRunning || cntSel == 0
		}
		if ( txtCntSel ) txtCntSel.textContent = `${ cntSel }/${ cntAll } selected`
		if ( btnStack ) btnStack.disabled = isTaskRunning || cntSel == 0

		if ( btnAllSelect ) btnAllSelect.disabled = isTaskRunning || cntSel >= cntAll || cntAll == 0
		if ( btnAllCancel ) btnAllCancel.disabled = isTaskRunning || cntSel == 0
		if ( btnSelStacked ) btnSelStacked.disabled = isTaskRunning || cache.stackedGroups.size === 0
		if ( btnSelUnstacked ) btnSelUnstacked.disabled = isTaskRunning || cache.unstackedGroups.size === 0

		const groupIds = groupId == null ? Array.from( cache.groups.keys() ) : [String( groupId )]
		groupIds.forEach( currentGroupId => {
			const stackSelect = document.getElementById( `sel-grp-stacked-${ currentGroupId }` )
			const unstackSelect = document.getElementById( `sel-grp-unstacked-${ currentGroupId }` )
			if ( stackSelect ) stackSelect.disabled = isTaskRunning || !cache.stackedGroups.has( currentGroupId )
			if ( unstackSelect ) unstackSelect.disabled = isTaskRunning || !cache.unstackedGroups.has( currentGroupId )

			const hasSelection = selectedGroups.has( currentGroupId )
			const stackButton = cache.groupStackButtons.get( currentGroupId )
			if ( stackButton ) stackButton.disabled = isTaskRunning || !hasSelection
			;( cache.groupActionButtons.get( currentGroupId ) || [] ).forEach( item => {
				if ( ['keep-selected', 'delete-selected'].includes( item.action ) ) item.button.disabled = isTaskRunning || !hasSelection
			} )
		} )
		if ( btnSelMns )
		{
			btnSelMns.disabled = isTaskRunning || cntAll == 0
			this.updBtnMns()
		}
	},

	async selectAll()
	{
		const cards = this.getDomCache().cards
		cards.forEach( card => {
			const assetId = this.extractAssetIdBy( card )
			if ( assetId ) this.selectedIds.add( assetId )
		} )
		await this.updAllCss()
		this.updBtns()
		console.log( `[Ste] Selected all ${ this.selectedIds.size } assets` )
		dsh.syncSte( this.cntTotal, this.selectedIds )
	},

	getMainIds()
	{
		return this.getDomCache().mainIds
	},

	isAllMainsSel()
	{
		const ids = this.getMainIds()
		return ids.length > 0 && ids.every( aid => this.selectedIds.has( aid ) )
	},

	async toggleMains()
	{
		const ids = this.getMainIds()
		const allSel = this.isAllMainsSel()
		ids.forEach( aid => { allSel ? this.selectedIds.delete( aid ) : this.selectedIds.add( aid ) } )
		this.updBtns()
		await this.updAllCss()
		console.log( `[Ste] ${ allSel ? 'Deselected' : 'Selected' } ${ ids.length } main assets` )
		dsh.syncSte( this.cntTotal, this.selectedIds )
	},

	updBtnMns()
	{
		const btn = document.getElementById( 'sim-btn-SelectMns' )
		if ( !btn ) return
		const allSel = this.isAllMainsSel()
		btn.classList.toggle( 'active', allSel )
		btn.setAttribute( 'aria-pressed', String( allSel ) )
	},

	async clearAll()
	{
		this.selectedIds.clear()
		this.stackCoverIds.clear()
		await this.updAllCss()
		this.updStackCoverButtons()
		this.updBtns()
		console.log( `[Ste] Cleared all selections` )
		dsh.syncSte( this.cntTotal, this.selectedIds )
	},

	async updAllCss()
	{
		const cards = this.getDomCache().cards
		// console.log( `[Ste] updAllCss cards[ ${ cards.length } ]` )
		const proms = []
		cards.forEach( card => {
			const assetId = this.extractAssetIdBy( card )
			if ( assetId ) proms.push( this.updCss( assetId, card ) )
		} )
		const results = await Promise.all( proms )
		return results.filter( r => r === true ).length
	},

	extractAssetIdBy( elem )
	{
		try
		{
			const idStr = elem.getAttribute( 'id' )
			if ( idStr && idStr.includes( 'card-select' ) )
			{
				const match = idStr.match( /"id":(\d+)/ )
				return match ? parseInt( match[ 1 ] ) : null // Return number instead of string
			}
		}
		catch ( e )
		{ console.error( '[Ste] Error extracting asset ID:', e ) }
		return null
	},

	getGroupCards( groupId )
	{
		return this.getDomCache().groups.get( String( groupId ) ) || []
	},

	getStackStatusCards( isStacked, groupId = null )
	{
		const cards = groupId == null
			? this.getDomCache().cards
			: this.getGroupCards( groupId )
		const expected = isStacked ? 'true' : 'false'
		return cards.filter( card => card.getAttribute( 'data-stacked' ) === expected )
	},

	async selectStackStatus( isStacked, groupId = null )
	{
		const scopeCards = groupId == null
			? this.getDomCache().cards
			: this.getGroupCards( groupId )
		const matchingCards = this.getStackStatusCards( isStacked, groupId )
		if ( matchingCards.length == 0 ) return

		scopeCards.forEach( card => {
			const assetId = this.extractAssetIdBy( card )
			if ( assetId ) {
				this.selectedIds.delete( assetId )
				this.stackCoverIds.delete( assetId )
			}
		} )
		matchingCards.forEach( card => {
			const assetId = this.extractAssetIdBy( card )
			if ( assetId ) this.selectedIds.add( assetId )
		} )

		await this.updAllCss()
		this.updStackCoverButtons( groupId )
		this.updBtns( groupId )
		console.log( `[Ste] Selected ${ matchingCards.length } ${ isStacked ? 'stacked' : 'non-stacked' } items${ groupId == null ? '' : ` in group ${ groupId }` }` )
		dsh.syncSte( this.cntTotal, this.selectedIds )
	},

	updStackCoverButtons( groupId = null, ownerId = null )
	{
		const buttons = this.getDomCache().coverButtons
		buttons.forEach( button => {
			try
			{
				const patternId = JSON.parse( button.id )
				if ( groupId != null && String( patternId.group ) !== String( groupId ) ) return
				if ( ownerId != null && patternId.owner !== ownerId ) return

				const chosen = this.stackCoverIds.has( patternId.id )
				button.textContent = chosen ? 'Cover choice' : 'Set cover'
				button.classList.toggle( 'active', chosen )
				button.classList.toggle( 'btn-info', chosen )
				button.classList.toggle( 'btn-outline-info', !chosen )
				button.setAttribute( 'aria-pressed', String( chosen ) )
			}
			catch ( e ) { console.error( '[Ste] Invalid stack cover button id:', e ) }
		} )
	},

	setStackCover( aid, groupId, ownerId, card = null )
	{
		const wasChosen = this.stackCoverIds.has( aid )
		const buttons = this.getDomCache().coverButtons
		buttons.forEach( button => {
			try
			{
				const patternId = JSON.parse( button.id )
				if ( String( patternId.group ) === String( groupId ) && patternId.owner === ownerId )
					this.stackCoverIds.delete( patternId.id )
			}
			catch ( e ) { console.error( '[Ste] Invalid stack cover button id:', e ) }
		} )

		if ( !wasChosen )
		{
			this.stackCoverIds.add( aid )
			this.selectedIds.add( aid )
			this.updCss( aid, card )
		}
		this.updStackCoverButtons( groupId, ownerId )
		this.updBtns( groupId )
	},

	selectGroup( groupId )
	{
		const grps = this.getGroupCards( groupId )

		grps.forEach( card => {
			const assetId = this.extractAssetIdBy( card )
			if ( assetId )
			{
				this.selectedIds.add( assetId )
				this.updCss( assetId, card )
			}
		} )

		this.updBtns( groupId )
		dsh.syncSte( this.cntTotal, this.selectedIds )
	},

	clearGroup( groupId )
	{
		const cards = this.getGroupCards( groupId )

		cards.forEach( card => {
			const assetId = this.extractAssetIdBy( card )
			if ( assetId )
			{
				this.selectedIds.delete( assetId )
				this.stackCoverIds.delete( assetId )
				this.updCss( assetId, card )
			}
		} )

		this.updStackCoverButtons( groupId )
		this.updBtns( groupId )
		dsh.syncSte( this.cntTotal, this.selectedIds )
	},
}

document.addEventListener( 'DOMContentLoaded', function(){

	//------------------------------------------------
	document.addEventListener( 'click', function( event ){

		const ste = Ste

		//------------------------------------------------------
		// acts: cbx select status
		//------------------------------------------------------
		if ( event.target.id == 'sim-btn-AllSelect' )
		{
			event.preventDefault()
			if ( ste ) ste.selectAll()
		}
		if ( event.target.id == 'sim-btn-AllCancel' )
		{
			event.preventDefault()
			if ( ste ) ste.clearAll()
		}
		if ( event.target.id == 'sim-btn-SelectMns' )
		{
			event.preventDefault()
			if ( ste ) ste.toggleMains()
		}
		if ( event.target.id == 'sim-btn-SelectStacked' )
		{
			event.preventDefault()
			if ( ste ) ste.selectStackStatus( true )
		}
		if ( event.target.id == 'sim-btn-SelectUnstacked' )
		{
			event.preventDefault()
			if ( ste ) ste.selectStackStatus( false )
		}
		if ( event.target.id == 'sim-btn-ExportIds' || event.target.id == 'view-btn-ExportIds' )
		{
			event.preventDefault()
			if (typeof exportIdsToCSV === 'function') {
				exportIdsToCSV()
			} else {
				console.error('[Export] exportIdsToCSV function not found!')
			}
		}

		//------------------------------------------------------
		// acts: disable buttons on direct task execution
		//------------------------------------------------------
		const btnMap = {
			'sim-btn-fnd': null,
			'sim-btn-RmSel': 'sim-cbx-NChk-RmSel',
			'sim-btn-OkSel': 'sim-cbx-NChk-OkSel',
			'sim-btn-OkAll': 'sim-cbx-NChk-OkAll',
			'sim-btn-RmAll': 'sim-cbx-NChk-RmAll',
		}
		if (btnMap.hasOwnProperty(event.target.id)) {
			const cbxId = btnMap[event.target.id]
			const shouldDisable = !cbxId || document.getElementById(cbxId)?.checked
			if (shouldDisable) {
				Object.keys(btnMap).forEach(id => {
					const btn = document.getElementById(id)
					if (btn) btn.disabled = true
				})
			}
		}

		//------------------------------------------------------
		// group selection
		//------------------------------------------------------
		if ( event.target.id && event.target.id.startsWith( 'cbx-sel-grp-all-' ) )
		{
			event.preventDefault()
			const groupId = event.target.id.replace( 'cbx-sel-grp-all-', '' )
			if ( ste ) ste.selectGroup( groupId )
		}
		if ( event.target.id && event.target.id.startsWith( 'cbx-sel-grp-non-' ) )
		{
			event.preventDefault()
			const groupId = event.target.id.replace( 'cbx-sel-grp-non-', '' )
			if ( ste ) ste.clearGroup( groupId )
		}
		if ( event.target.id && event.target.id.startsWith( 'sel-grp-stacked-' ) )
		{
			event.preventDefault()
			const groupId = event.target.id.replace( 'sel-grp-stacked-', '' )
			if ( ste ) ste.selectStackStatus( true, groupId )
		}
		if ( event.target.id && event.target.id.startsWith( 'sel-grp-unstacked-' ) )
		{
			event.preventDefault()
			const groupId = event.target.id.replace( 'sel-grp-unstacked-', '' )
			if ( ste ) ste.selectStackStatus( false, groupId )
		}

		//------------------------------------------------------
		//
		//------------------------------------------------------

	} )

} )
