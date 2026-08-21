
const Ste = window.Ste = {
	cntTotal: 0,
	selectedIds: new Set(),
	stackCoverIds: new Set(),
	_lastSyncHash: null,

	init( cnt )
	{
		this.cntTotal = cnt
		this.selectedIds.clear()
		this.stackCoverIds.clear()
		console.log( `[Ste] Initialized with ${ cnt } assets, selected[ ${ this.selectedIds.size } ]` )

		dsh.syncSte( this.cntTotal, this.selectedIds )
	},

	initSilent( cnt )
	{
		this.cntTotal = cnt
		this.selectedIds.clear()
		this.stackCoverIds.clear()
		console.log( `[Ste] Silent init with ${ cnt } assets, selected[ ${ this.selectedIds.size } ]` )
	},

	toggle( aid )
	{
		if ( this.selectedIds.has( aid ) )
		{
			this.selectedIds.delete( aid )
			this.stackCoverIds.delete( aid )
		}
		else this.selectedIds.add( aid )

		console.log( `[Ste] Toggled ${ aid }, selected count: ${ this.selectedIds.size }` )

		this.updCss( aid )
		this.updBtns()
	},

	async updCss( aid, card = null )
	{
		// console.log( `[Ste] updCss called for aid: ${aid} (type: ${typeof aid})` )

		if ( !card ) card = await getCardById( aid )
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

	updBtns()
	{
		const cntSel = this.selectedIds.size
		const cntAll = this.cntTotal
		const cntDiff = Math.max(0, cntAll - cntSel)

		const btnRm = document.getElementById( 'sim-btn-RmSel' )
		const btnRS = document.getElementById( 'sim-btn-OkSel' )
		const btnAllSelect = document.getElementById( 'sim-btn-AllSelect' )
		const btnAllCancel = document.getElementById( 'sim-btn-AllCancel' )
		const btnSelMns = document.getElementById( 'sim-btn-SelectMns' )
		const btnSelStacked = document.getElementById( 'sim-btn-SelectStacked' )
		const btnSelUnstacked = document.getElementById( 'sim-btn-SelectUnstacked' )
		const btnStack = document.getElementById( 'sim-btn-Stack' )
		const txtCntSel = document.getElementById( 'sim-txt-cnt-sel' )
		const cards = Array.from( document.querySelectorAll( '[id*="card-select"]' ) )
		const selectedGroups = new Set()
		const stackedGroups = new Set()
		const unstackedGroups = new Set()

		cards.forEach( card => {
			const groupId = card.getAttribute( 'data-group-id' )
			const assetId = this.extractAssetIdBy( card )
			if ( groupId != null && assetId && this.selectedIds.has( assetId ) ) selectedGroups.add( String( groupId ) )
			if ( groupId != null && card.getAttribute( 'data-stacked' ) === 'true' ) stackedGroups.add( String( groupId ) )
			if ( groupId != null && card.getAttribute( 'data-stacked' ) === 'false' ) unstackedGroups.add( String( groupId ) )
		} )

		if ( btnRm ) {
			btnRm.textContent = 'Delete selected'
			btnRm.title = `Delete ${ cntSel } selected images and keep ${ cntDiff } others`
			btnRm.disabled = cntSel == 0
		}
		if ( btnRS ) {
			btnRS.textContent = 'Keep selected'
			btnRS.title = `Keep ${ cntSel } selected images and delete ${ cntDiff } others`
			btnRS.disabled = cntSel == 0
		}
		if ( txtCntSel ) txtCntSel.textContent = `${ cntSel }/${ cntAll } selected`
		if ( btnStack ) btnStack.disabled = cntSel == 0

		if ( btnAllSelect ) btnAllSelect.disabled = ( cntSel >= cntAll || cntAll == 0 )
		if ( btnAllCancel ) btnAllCancel.disabled = ( cntSel == 0 )
		if ( btnSelStacked ) btnSelStacked.disabled = !cards.some( card => card.getAttribute( 'data-stacked' ) === 'true' )
		if ( btnSelUnstacked ) btnSelUnstacked.disabled = !cards.some( card => card.getAttribute( 'data-stacked' ) === 'false' )
		document.querySelectorAll( '[id^="sel-grp-stacked-"]' ).forEach( btn => {
			const groupId = btn.id.replace( 'sel-grp-stacked-', '' )
			btn.disabled = !stackedGroups.has( String( groupId ) )
		} )
		document.querySelectorAll( '[id^="sel-grp-unstacked-"]' ).forEach( btn => {
			const groupId = btn.id.replace( 'sel-grp-unstacked-', '' )
			btn.disabled = !unstackedGroups.has( String( groupId ) )
		} )
		document.querySelectorAll( '[id*=\'"type":"sim-stack-group"\']' ).forEach( btn => {
			try { btn.disabled = !selectedGroups.has( String( JSON.parse( btn.id ).id ) ) }
			catch ( e ) { console.error( '[Ste] Invalid group stack button id:', e ) }
		} )
		document.querySelectorAll( '[id*=\'"type":"sim-group-action"\']' ).forEach( btn => {
			try {
				const patternId = JSON.parse( btn.id )
				if ( ['keep-selected', 'delete-selected'].includes( patternId.action ) )
					btn.disabled = !selectedGroups.has( String( patternId.id ) )
			}
			catch ( e ) { console.error( '[Ste] Invalid group action button id:', e ) }
		} )
		if ( btnSelMns )
		{
			btnSelMns.disabled = ( cntAll == 0 )
			this.updBtnMns()
		}

		console.log( `[Ste] updBtns - selected[ ${ cntSel } / ${ cntAll } ]` )
	},

	async selectAll()
	{
		const cards = document.querySelectorAll( '[id*="card-select"]' )
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
		const cards = document.querySelectorAll( '.sim.main [id*="card-select"]' )
		const ids = []
		cards.forEach( card => {
			const aid = this.extractAssetIdBy( card )
			if ( aid ) ids.push( aid )
		} )
		return ids
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
		this.updBtns()
		console.log( `[Ste] Cleared all selections` )
		dsh.syncSte( this.cntTotal, this.selectedIds )
	},

	async updAllCss()
	{
		const cards = document.querySelectorAll( '[id*="card-select"]' )
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
		return Array.from( document.querySelectorAll( '[id*="card-select"][data-group-id]' ) )
			.filter( card => String( card.getAttribute( 'data-group-id' ) ) === String( groupId ) )
	},

	getStackStatusCards( isStacked, groupId = null )
	{
		const cards = groupId == null
			? Array.from( document.querySelectorAll( '[id*="card-select"]' ) )
			: this.getGroupCards( groupId )
		const expected = isStacked ? 'true' : 'false'
		return cards.filter( card => card.getAttribute( 'data-stacked' ) === expected )
	},

	async selectStackStatus( isStacked, groupId = null )
	{
		const scopeCards = groupId == null
			? Array.from( document.querySelectorAll( '[id*="card-select"]' ) )
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
		this.updBtns()
		console.log( `[Ste] Selected ${ matchingCards.length } ${ isStacked ? 'stacked' : 'non-stacked' } items${ groupId == null ? '' : ` in group ${ groupId }` }` )
		dsh.syncSte( this.cntTotal, this.selectedIds )
	},

	setStackCover( aid, groupId, ownerId )
	{
		const buttons = document.querySelectorAll( '[id*=\'"type":"sim-stack-cover"\']' )
		buttons.forEach( button => {
			try
			{
				const patternId = JSON.parse( button.id )
				if ( String( patternId.group ) === String( groupId ) && patternId.owner === ownerId )
					this.stackCoverIds.delete( patternId.id )
			}
			catch ( e ) { console.error( '[Ste] Invalid stack cover button id:', e ) }
		} )

		this.stackCoverIds.add( aid )
		this.selectedIds.add( aid )
		this.updCss( aid )
		this.updBtns()
		console.log( `[Ste] Stack cover set to ${ aid } for group ${ groupId }, owner ${ ownerId }` )
	},

	selectGroup( groupId )
	{
		const grps = this.getGroupCards( groupId )
		let cnt = 0

		grps.forEach( card => {
			const assetId = this.extractAssetIdBy( card )
			if ( assetId )
			{
				this.selectedIds.add( assetId )
				this.updCss( assetId, card )
				cnt++
			}
		} )

		this.updBtns()
		console.log( `[Ste] Selected ${ cnt } items in group ${ groupId }` )
		dsh.syncSte( this.cntTotal, this.selectedIds )
	},

	clearGroup( groupId )
	{
		const cards = this.getGroupCards( groupId )
		let deselectedCount = 0

		cards.forEach( card => {
			const assetId = this.extractAssetIdBy( card )
			if ( assetId )
			{
				this.selectedIds.delete( assetId )
				this.stackCoverIds.delete( assetId )
				this.updCss( assetId, card )
				deselectedCount++
			}
		} )

		this.updBtns()
		console.log( `[Ste] Deselected ${ deselectedCount } items in group ${ groupId }` )
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
