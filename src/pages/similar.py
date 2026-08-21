from enum import auto
import hashlib
import json
import traceback
from typing import Optional
import time

from dash.html import Option

import immich
import db
from db import psql
from conf import ks, co
from dsh import dash, htm, dcc, dbc, inp, out, ste, getTrgId, noUpd, ctx, ALL
from dsh import cbk, ccbk, cbkFn
from util import log
from mod import mapFns, models, tskSvc
import sim_stack
from mod.models import Mdl, Now, Cnt, Nfy, Pager, Tsk, Ste, PgSim

from ui import pager, cardSets, gv

lg = log.get(__name__)


def _mkMrgMsg(keepAssets):
	mrgOk, mrgErr = immich.isMergeAvailable()
	if not mrgOk:
		return [
			htm.Br(), htm.Br(),
			htm.Span("Metadata Merge Unavailable", className="text-danger fw-bold"), htm.Br(),
			f"Error: {mrgErr}", htm.Br(),
			"Please contact raz for support.",
		]

	mrgAttrs = []
	m = db.dto.mrg
	if m.albums: mrgAttrs.append("Albums")
	if m.favs: mrgAttrs.append("Favorites")
	if m.tags: mrgAttrs.append("Tags")
	if m.rating: mrgAttrs.append("Rating")
	if m.desc: mrgAttrs.append("Description")
	if m.loc: mrgAttrs.append("Location")
	if m.vis: mrgAttrs.append("Visibility")
	keepAids = [f"#{a.autoId}" for a in keepAssets]
	return [
		htm.Br(), htm.Br(),
		htm.Span("Metadata Merge Enabled", className="text-warning fw-bold"), htm.Br(),
		f"Attributes: {', '.join(mrgAttrs)}", htm.Br(),
		f"Merge to: {', '.join(keepAids)}",
	]

# Debug flag for verbose logging
DEBUG = False


def _assetRenderSignature(asset: models.Asset) -> str:
	payload = json.dumps(asset.toDict(), sort_keys=True, separators=(',', ':'), default=str)
	return hashlib.sha1(payload.encode('utf-8')).hexdigest()


def _similarRenderState(assets: list[models.Asset], multiMode: bool) -> dict:
	groups = sim_stack.groupAssets(assets, multiMode)
	return {
		'multi': multiMode,
		'count': len(assets),
		'groups': [
			{
				'id': groupId,
				'assets': [
					{'id': asset.autoId, 'signature': _assetRenderSignature(asset)}
					for asset in groupAssets
				],
			}
			for groupId, groupAssets in sorted(groups.items())
		],
	}


def _patchMultiGrid(oldState: dict, newState: dict, assets: list[models.Asset]):
	if not oldState or not oldState.get('multi') or not newState.get('multi'): return None
	if not oldState.get('groups') or not newState.get('groups'): return None
	if (oldState.get('count', 0) <= 4) != (newState.get('count', 0) <= 4): return None

	oldGroups = oldState['groups']
	newGroups = newState['groups']
	oldGroupIds = [str(group['id']) for group in oldGroups]
	newGroupIds = [str(group['id']) for group in newGroups]
	newGroupSet = set(newGroupIds)
	if newGroupIds != [groupId for groupId in oldGroupIds if groupId in newGroupSet]: return None

	groupedAssets = {
		str(groupId): (groupId, groupAssets)
		for groupId, groupAssets in sim_stack.groupAssets(assets, True).items()
	}
	newGroupsById = {str(group['id']): group for group in newGroups}
	style = {'flex': '1 1 250px'} if len(assets) <= 4 else {}

	starts = []
	start = 0
	for group in oldGroups:
		starts.append((start, group))
		start += 1 + len(group['assets'])

	patch = dash.Patch()
	rows = patch['props']['children']
	changed = False

	for start, oldGroup in reversed(starts):
		groupId = str(oldGroup['id'])
		newGroup = newGroupsById.get(groupId)
		oldAssetIds = [str(asset['id']) for asset in oldGroup['assets']]
		newAssetIds = [str(asset['id']) for asset in newGroup['assets']] if newGroup else []

		if newGroup and oldAssetIds == newAssetIds:
			assetsById = {str(asset.autoId): asset for asset in groupedAssets[groupId][1]}
			for offset, (oldAsset, newAsset) in enumerate(zip(oldGroup['assets'], newGroup['assets']), start=1):
				if oldAsset['signature'] == newAsset['signature']: continue
				rows[start + offset] = gv.mkCardRow(
					assetsById[str(newAsset['id'])],
					groupedAssets[groupId][0],
					style,
				)
				changed = True
			continue

		for rowIndex in range(start + len(oldGroup['assets']), start - 1, -1):
			del rows[rowIndex]
		changed = True

		if newGroup:
			actualGroupId, groupAssets = groupedAssets[groupId]
			for offset, row in enumerate(gv.mkGroupRows(actualGroupId, groupAssets, style)):
				rows.insert(start + offset, row)

	return patch if changed else None

dash.register_page(
	__name__,
	path=f'/{ks.pg.similar}',
	path_template=f'/{ks.pg.similar}/<autoId>',
	title=f"{ks.title}: " + ks.pg.similar.name,
)


class k:
	assUrl = 'sim-AssFromUrl'

	txtCntRs = 'sim-txt-cnt-records'
	txtCntOk = 'sim-txt-cnt-ok'
	txtCntNo = 'sim-txt-cnt-no'
	txtCntSel = 'sim-txt-cnt-sel'

	btnAllSelect = 'sim-btn-AllSelect'
	btnAllCancel = 'sim-btn-AllCancel'
	btnExportIds = 'sim-btn-ExportIds'
	btnSelectMns = 'sim-btn-SelectMns'
	btnSelectStacked = 'sim-btn-SelectStacked'
	btnSelectUnstacked = 'sim-btn-SelectUnstacked'

	btnFind = "sim-btn-fnd"
	btnClear = "sim-btn-clear"
	btnReset = "sim-btn-reset"
	btnRmSel = "sim-btn-RmSel"
	btnOkSel = "sim-btn-OkSel"
	btnStack = "sim-btn-Stack"
	btnOkAll = "sim-btn-OkAll"
	btnRmAll = "sim-btn-RmAll"
	cbxNChkOkAll = "sim-cbx-NChk-OkAll"
	cbxNChkRmSel = "sim-cbx-NChk-RmSel"
	cbxNChkOkSel = "sim-cbx-NChk-OkSel"
	cbxNChkRmAll = "sim-cbx-NChk-RmAll"
	cbxStackDelete = "sim-cbx-StackDelete"


	tabs = 'sim-tabs'
	tabCur = "tab-current"
	tabPnd = "tab-pend"
	pagerPnd = "sim-pager-pnd"

	gvSim = "sim-gvSim"
	gvPnd = 'sim-gvPnd'
	renderState = 'sim-render-state'

	@staticmethod
	def id(k): return {"type": "sim", "id": f"{k}"}


#========================================================================
def layout(autoId=None):
	try: autoId = str(autoId)
	except: autoId = None


	import ui

	def searchAction(label, detail, button, tone=""):
		return htm.Div([
			htm.Small(label, className="similar-action-label"),
			button,
			htm.Small(detail, className="similar-action-detail"),
		], className=f"similar-search-action {tone}".strip())

	return ui.renderBody([
		#====== top start =======================================================
		dcc.Store(id=k.assUrl, data=autoId),
		dcc.Store(id=k.renderState, storage_type="memory"),

		# 客戶端選擇狀態管理的 dummy 元素
		htm.Div(id={"type": "dummy-output", "id": "selection"}, style={"display": "none"}),
		htm.Div(id={"type": "dummy-output", "id": "init-selection"}, style={"display": "none"}),

		htm.Div([
			htm.H3(f"{ks.pg.similar.name}"),
			htm.Small(f"{ks.pg.similar.desc}", className="text-muted")
		], className="body-header"),

		htm.Div([
			htm.Div(htm.I(className="bi bi-intersect"), className="similar-intro-icon"),
			htm.Div([
				htm.Small("Review workspace", className="similar-eyebrow"),
				htm.H4("Compare confidently, then decide per group"),
				htm.P("Tune the search once, select the right images, and keep each group open until you are ready to mark it resolved."),
			]),
			htm.Div([
				htm.I(className="bi bi-lightning-charge"),
				"Actions update in place",
			], className="similar-runtime-badge"),
		], className="similar-intro"),

		htm.Div([
			htm.Div([
				htm.Div([
					htm.Span("Decision settings"),
					htm.Small("Matching, merge, and automatic selection", className="text-muted"),
				], className="similar-section-heading"),
				cardSets.renderThreshold(),
				cardSets.renderMerge(),
				cardSets.renderAutoSelect(),
			], className="similar-config-primary"),

			htm.Div([
				htm.Div([
					htm.Span("Search scope"),
					htm.Small("Control which groups and records enter this workspace", className="text-muted"),
				], className="similar-section-heading"),
				cardSets.renderCard(),
				htm.Div([
					searchAction(
						"Recommended",
						"Find the next review set; unmatched assets are marked resolved automatically.",
						dbc.Button("Find similar", id=k.btnFind, color="primary", className="w-100", disabled=True),
					),
					searchAction(
						"Keep resolved",
						"Clear only active search records while preserving completed work.",
						dbc.Button("Clear active records", id=k.btnClear, color="secondary", outline=True, className="w-100", disabled=True),
					),
					searchAction(
						"Start over",
						"Reset all similarity records, including automatically resolved results.",
						dbc.Button("Reset all records", id=k.btnReset, color="danger", outline=True, className="w-100", disabled=True),
						"similar-search-action-danger",
					),
				], className="similar-search-actions"),
			], className="similar-config-search"),
		], className="similar-config-grid"),

		#====== top end =========================================================
	], [
		#====== bottom start=====================================================

		#------------------------------------------------------------------------
		# Tabs
		#------------------------------------------------------------------------
		htm.Div([

			dbc.Tabs(
				id=k.tabs,
				active_tab=k.tabCur,
				children=[
					dbc.Tab(
						label="Current review", tab_id=k.tabCur,
						children=[

							# Action buttons
							htm.Div([

								htm.Div([

									htm.Small("Select", className="sim-control-label"),
									htm.Small("0 selected", id=k.txtCntSel, className="sim-selection-count"),
									dbc.Button("All", id=k.btnAllSelect, size="sm", color="secondary", className="txt-sm", disabled=True, title="Select every visible image"),
									dbc.Button("None", id=k.btnAllCancel, size="sm", color="secondary", className="txt-sm", disabled=True, title="Clear the current selection"),
									dbc.Button("Sources", id=k.btnSelectMns, size="sm", color="secondary", className="txt-sm", disabled=True, title="Toggle the source image in every group"),
									dbc.Button("Stacked", id=k.btnSelectStacked, size="sm", color="secondary", className="txt-sm", disabled=True, title="Replace the current selection with stacked images"),
									dbc.Button("Not stacked", id=k.btnSelectUnstacked, size="sm", color="secondary", className="txt-sm", disabled=True, title="Replace the current selection with non-stacked images"),
									dbc.Button("Export IDs", id=k.btnExportIds, size="sm", color="info", className="txt-sm", disabled=True),

								], className="sim-controls sim-global-selection"),


								htm.Div([
									htm.Small("Actions", className="sim-control-label"),

									dbc.Button("Keep selected", id=k.btnOkSel, color="success", size="sm", className="txt-sm", disabled=True, title="Keep selected images and delete the other visible images"),
									dbc.Button("Delete selected", id=k.btnRmSel, color="danger", size="sm", className="txt-sm", disabled=True, title="Delete selected images and keep the other visible images"),
									dbc.Checkbox(id=k.cbxStackDelete, label="Delete rest", className="sim-stack-delete sm"),
									dbc.Button("Stack selected", id=k.btnStack, color="info", size="sm", className="txt-sm", disabled=True, title="Create one Immich stack per similarity group and owner"),
									dbc.Button("Mark all resolved", id=k.btnOkAll, color="primary", size="sm", className="txt-sm", disabled=True),
									dbc.Button("Delete all", id=k.btnRmAll, color="danger", size="sm", className="txt-sm", disabled=True),
									htm.Details([
										htm.Summary("Confirmations", className="btn btn-secondary btn-sm txt-sm"),
										htm.Div([
											htm.Small("Skip confirmation for", className="sim-confirm-title"),
											dbc.Checkbox(id=k.cbxNChkOkSel, label="Keep selected", className="sm"),
											dbc.Checkbox(id=k.cbxNChkRmSel, label="Delete selected", className="sm"),
											dbc.Checkbox(id=k.cbxNChkOkAll, label="Mark all resolved", className="sm"),
											dbc.Checkbox(id=k.cbxNChkRmAll, label="Delete all", className="sm"),
										], className="sim-confirm-options"),
									], className="sim-confirm-menu"),

								], className="sim-controls sim-global-actions"),


							],
								className="tab-acts"
							),


							dbc.Spinner(
								htm.Div(id=k.gvSim),
								color="success", type="border", spinner_style={"width": "3rem", "height": "3rem"},
							),

							# Floating Goto Top Button
							htm.Button(
								"↑ Top",
								id="sim-goto-top-btn",
								className="goto-top-btn",
								style={"display": ""}
							),
						]
					),
					dbc.Tab(
						label="Pending",
						tab_id=k.tabPnd,
						id=k.tabPnd,
						disabled=True,
						children=[
							htm.Div([
								# top pager
								*pager.createPager(pgId=k.pagerPnd, idx=0, btnSize=9, className="mb-3"),

								dbc.Spinner(
									htm.Div(id=k.gvPnd),
									color="success", type="border", spinner_style={"width": "3rem", "height": "3rem"},
								),

								# bottom pager
								*pager.createPager(pgId=k.pagerPnd, idx=1, btnSize=9, className="mt-3"),

								# Main pager (store only)
								*pager.createStore(pgId=k.pagerPnd),
							], className="text-center")
						]
					),
				]
			)
		],
			className="ITab similar-workspace"
		),

		#====== bottom end ======================================================
	], pageClass="page-similar")



#========================================================================
# callbacks
#========================================================================

pager.regCallbacks(k.pagerPnd)


#------------------------------------------------------------------------
# Sync tab changes to now state
#------------------------------------------------------------------------
@cbk(
	out(ks.sto.now, "data", allow_duplicate=True),
	inp(k.tabs, "active_tab",),
	ste(ks.sto.now, "data"),
	prevent_initial_call=True
)
def sim_OnTabChange(active_tab, dta_now):
	if not active_tab or not dta_now: return noUpd

	now = Now.fromDic(dta_now)

	if now.sim.activeTab == active_tab: return noUpd

	lg.info(f"[sim:tab] Tab changed to: {active_tab} (from: {now.sim.activeTab})")

	patch = dash.Patch()
	patch['sim']['activeTab'] = active_tab
	return patch



#------------------------------------------------------------------------
# Handle pager changes - reload pending data
#------------------------------------------------------------------------
@cbk(
	[
		out(k.gvPnd, "children", allow_duplicate=True),
		out(ks.sto.now, "data", allow_duplicate=True),
	],
	inp(pager.id.store(k.pagerPnd), "data"),
	ste(ks.sto.now, "data"),
	prevent_initial_call=True
)
def sim_onPagerChanged(dta_pgr, dta_now):
	if not dta_pgr or not dta_now: return noUpd.by(2)

	now = Now.fromDic(dta_now)
	pgr = Pager.fromDic(dta_pgr)

	# Check if we're already on this page with same data
	oldPgr = now.sim.pagerPnd
	if oldPgr and oldPgr.idx == pgr.idx and oldPgr.size == pgr.size and oldPgr.cnt == pgr.cnt:
		if DEBUG: lg.info(f"[sim:pager] Already on page {pgr.idx}, skipping reload")
		return noUpd.by(2)

	now.sim.pagerPnd = pgr

	paged = db.pics.getPagedPending(page=pgr.idx, size=pgr.size)
	now.sim.assPend = paged

	lg.info(f"[sim:pager] paged: {pgr.idx}/{(pgr.cnt + pgr.size - 1) // pgr.size}, got {len(paged)} items")

	gvPnd = gv.mkPndGrd(now.sim.assPend, onEmpty=[
		dbc.Alert("No pending items on this page", color="secondary", className="text-center"),
	])

	return gvPnd, now.toDict()



#------------------------------------------------------------------------
# assert from url
#------------------------------------------------------------------------
@cbk(
	[
		out(ks.sto.now, "data", allow_duplicate=True),
		out(ks.sto.tsk, "data", allow_duplicate=True),
		out(ks.sto.nfy, "data", allow_duplicate=True),
	],
	inp(k.assUrl, "data"),
	[
		ste(ks.sto.now, "data"),
		ste(ks.sto.nfy, "data"),
	],
	prevent_initial_call="initial_duplicate"
)
def sim_SyncUrlAssetToNow(autoId, dta_now, dta_nfy):
	now = Now.fromDic(dta_now)
	nfy = Nfy.fromDic(dta_nfy)

	ass:Optional[models.Asset] = None

	if autoId and autoId != 'None':
		autoId = int(autoId) if autoId else 0

		if autoId == now.sim.aidUrl:
			# 已執行過
			return noUpd.by(3)

		lg.info(f"[sim] from url autoId[{autoId}]")
		if autoId != 0: ass = db.pics.getByAutoId(autoId)
		if ass:
			lg.info(f"[sim:sync] asset from url: #{ass.autoId} id[{ass.id}] simOk[{ass.simOk}]")

			if ass.autoId == now.sim.aidUrl:
				nfy.info(f'[sim:sync] ignore searched #{ass.autoId}')
				return noUpd, noUpd, nfy.toDict()

			if ass.simOk == 1:
				nfy.info(f'[sim:sync] ignore resolved #{ass.autoId}')
				return noUpd, noUpd, nfy.toDict()

	if ass:
		lg.info(f"[sim:sync] trigger #{ass.autoId} id[{ass.id}]")
		now.sim.aidUrl = ass.autoId
		now.sim.assAid = ass.autoId

		mdl = Mdl()
		mdl.id = ks.pg.similar
		mdl.cmd = ks.cmd.sim.fnd
		mdl.msg = f'Search images similar to {ass.autoId}'

		tsk = mdl.mkTsk()

		lg.info(f"[sim:sync] to task: {tsk}")
		return now.toDict(), tsk.toDict(), noUpd


	# if not autoId:
	#     if not now.sim.assUrl: return noUpd.by(3)
	#
	#     patch = dash.Patch()
	#     patch['sim']['assUrl'] = None
	#     return patch, noUpd, noUpd

	return noUpd.by(3)



#------------------------------------------------------------------------
# onStatus
#------------------------------------------------------------------------
@cbk(
	[
		out(k.gvSim, "children"),
		out(k.gvPnd, "children"),
		out(ks.sto.now, "data", allow_duplicate=True),
		out(pager.id.store(k.pagerPnd), "data", allow_duplicate=True),
		out(k.tabPnd, "disabled"),
		out(k.tabPnd, "label"),
		out(k.tabs, "active_tab", allow_duplicate=True),
		out(k.renderState, "data"),
	],
	inp(ks.sto.now, "data"),
	[
		ste(ks.sto.cnt, "data"),
		ste(k.renderState, "data"),
	],
	prevent_initial_call="initial_duplicate"
)
def sim_Load(dta_now, dta_cnt, oldRenderState):
	now = Now.fromDic(dta_now)
	cnt = Cnt.fromDic(dta_cnt)

	trgId = getTrgId()
	if trgId: lg.info(f"[sim:load] load, trig: [ {trgId} ]")

	cntNo, cntOk, cntPn = cnt.simNo, cnt.simOk, cnt.simPnd

	multiMode = db.dto.muod.on
	renderState = _similarRenderState(now.sim.assCur, multiMode)
	renderStateChanged = oldRenderState != renderState

	if not renderStateChanged:
		gview = noUpd
	elif multiMode:
		gview = _patchMultiGrid(oldRenderState, renderState, now.sim.assCur)
		if gview is None:
			gview = gv.mkGrdGrps(now.sim.assCur, onEmpty=[
				dbc.Alert("No grouped results found..", color="secondary", className="text-center m-5"),
			])
	else:
		gview = gv.mkGrd(now.sim.assCur, onEmpty=[
			dbc.Alert("Please find the similar images..", color="secondary", className="text-center m-5"),
		])

	# Initialize or get pager
	pgr = now.sim.pagerPnd
	if not pgr:
		pgr = Pager(idx=1, size=20)
		now.sim.pagerPnd = pgr

	# Update pager total count
	pagerData = None
	oldPn = pgr.cnt
	if pgr.cnt != cntPn:
		pgr.cnt = cntPn
		# Keep current page if still valid, otherwise reset to last valid page
		totalPages = (cntPn + pgr.size - 1) // pgr.size if cntPn > 0 else 1
		if pgr.idx > totalPages: pgr.idx = max(1, totalPages)
		now.sim.pagerPnd = pgr
		# Only update pager store if count actually changed
		if oldPn != cntPn: pagerData = pgr

	lg.info(f"--------------------------------------------------------------------------------")
	lg.info(f"[sim:load] trig[{trgId}] muod[{db.dto.muod}] cntNo[{cntNo}] cntOk[{cntOk}] cntPn[{cntPn}]({oldPn}) assCur[{len(now.sim.assCur)}] assAid[{now.sim.assAid}]")

	# Load pending data - reload if count changed or no data
	isInitial = not trgId
	needReload = isInitial
	if cntPn > 0:
		if not now.sim.assPend or len(now.sim.assPend) == 0: needReload = True
		elif oldPn != cntPn:
			needReload = True
			lg.info(f"[sim:load] Pending count changed from {oldPn} to {cntPn}, reloading data")
	else: needReload = True

	if needReload:
		paged = db.pics.getPagedPending(page=pgr.idx, size=pgr.size)
		lg.info(f"[sim:load] pend reload, idx[{pgr.idx}] size[{pgr.size}] got[{len(paged)}]")
		now.sim.assPend = paged

	# Only rebuild gvPnd if pending data changed
	if needReload:
		gvPnd = gv.mkPndGrd(now.sim.assPend, onEmpty=[
			dbc.Alert("Please find the similar images..", color="secondary", className="text-center m-5"),
		])
	else: gvPnd = noUpd

	# Update pending tab state based on cntPn
	tabDisabled = cntPn < 1
	tabLabel = f"pending ({cntPn})" if cntPn >= 1 else "pending"

	# Only update now if there were actual changes
	nowChanged = needReload or (pagerData is not None)
	nowDict = now.toDict() if nowChanged else noUpd

	activeTab = now.sim.activeTab if now.sim.activeTab else k.tabCur

	return [
		gview, gvPnd,
		nowDict,
		pagerData.toDict() if pagerData else noUpd,
		tabDisabled, tabLabel, activeTab,
		renderState if renderStateChanged else noUpd,
	]


#------------------------------------------------------------------------
# Update status counters - Using CLIENT-SIDE callbacks for performance
#------------------------------------------------------------------------
ccbk(
	cbkFn("similar", "onCardSelectClicked"),
	out(ks.sto.ste, "data"),
	[inp({"type": "card-select", "id": ALL}, "n_clicks")],
	prevent_initial_call=True
)

ccbk(
	cbkFn("similar", "onStackCoverClicked"),
	out(ks.sto.ste, "data", allow_duplicate=True),
	[inp({"type": gv.STACK_COVER_BUTTON, "id": ALL, "group": ALL, "owner": ALL}, "n_clicks")],
	prevent_initial_call=True,
)


#------------------------------------------------------------------------
# Initialize client-side selection state when assets load
#------------------------------------------------------------------------
ccbk(
	cbkFn("similar", "onSimJs"),
	out({"type": "dummy-output", "id": "init-selection"}, "children"),
	inp(ks.sto.now, "data"),
	inp(ks.sto.ste, "data"),
	inp(ks.sto.sets, "data"),
	prevent_initial_call="initial_duplicate"
)


#------------------------------------------------------------------------
# Update all button states based on current data
#------------------------------------------------------------------------
@cbk(
	[
		out(k.btnFind, "disabled"),
		out(k.btnClear, "disabled"),
		out(k.btnReset, "disabled"),
		out(k.btnOkAll, "disabled"),
		out(k.btnRmAll, "disabled"),
		out(k.btnRmSel, "disabled"),
		out(k.btnOkSel, "disabled"),
		out(k.btnStack, "disabled"),
		out(k.btnExportIds, "disabled"),
		out({"type": gv.STACK_GROUP_BUTTON, "id": ALL}, "disabled"),
		out({"type": gv.GROUP_ACTION_BUTTON, "action": ALL, "id": ALL}, "disabled"),
		out({"type": gv.STACK_COVER_BUTTON, "id": ALL, "group": ALL, "owner": ALL}, "outline"),
		out({"type": gv.STACK_COVER_BUTTON, "id": ALL, "group": ALL, "owner": ALL}, "children"),
		out({"type": gv.STACK_COVER_BUTTON, "id": ALL, "group": ALL, "owner": ALL}, "disabled"),
	],
	[
		inp(ks.sto.now, "data"),
		inp(ks.sto.ste, "data"),
		inp(ks.sto.cnt, "data"),
		inp(ks.sto.tsk, "data"),
	],
	[
		ste({"type": gv.STACK_GROUP_BUTTON, "id": ALL}, "id"),
		ste({"type": gv.GROUP_ACTION_BUTTON, "action": ALL, "id": ALL}, "id"),
		ste({"type": gv.STACK_COVER_BUTTON, "id": ALL, "group": ALL, "owner": ALL}, "id"),
	],
	prevent_initial_call="initial_duplicate"
)
def sim_UpdateButtons(
	dta_now, dta_ste, dta_cnt, dta_tsk,
	groupButtonIds, groupActionButtonIds, coverButtonIds,
):
	# Selection and cover changes are already rendered synchronously by the
	# client-side state manager. A server response here only repaints those
	# controls later with potentially stale state.
	if ctx.triggered_id == ks.sto.ste:
		return noUpd.by(14)

	now = Now.fromDic(dta_now)
	ste = Ste.fromDic(dta_ste) if dta_ste else Ste()
	cnt = Cnt.fromDic(dta_cnt)
	tsk = Tsk.fromDic(dta_tsk)

	from mod.mgr.tskSvc import mgr
	isTaskRunning = False
	if mgr:
		for _, info in mgr.list().items():
			if info.status.value in ['pending', 'running']:
				isTaskRunning = True
				break
	if tsk.id and tsk.cmd: isTaskRunning = True

	cntAssets = len(now.sim.assCur) if now.sim.assCur else 0
	cntNo = cnt.ass - cnt.simOk if cnt else 0
	cntPn = cnt.simPnd if cnt else 0
	disFind = cntNo <= 0 or (cntPn >= cntNo) or isTaskRunning
	cntSrchd = db.pics.countHasSimIds(isOk=0) if not isTaskRunning else 0
	disClear = cntSrchd <= 0 or isTaskRunning
	cntOk = cnt.simOk if cnt else 0
	disReset = cntOk <= 0 and cntPn <= 0 or isTaskRunning
	disOk = cntAssets <= 0
	disDel = cntAssets <= 0
	disExport = cntAssets <= 0

	cntSel = len(ste.selectedIds) if ste.selectedIds else 0
	disRm = cntSel == 0
	disRS = cntSel == 0
	disStack = isTaskRunning or cntSel == 0
	selectedIds = set(ste.selectedIds)
	selectedGroupIds = {
		str(groupId)
		for groupId, groupAssets in sim_stack.groupAssets(now.sim.assCur, db.dto.muod.on).items()
		if any(asset.autoId in selectedIds for asset in groupAssets)
	}

	groupStackDisabled = []
	for buttonId in groupButtonIds or []:
		disabled = isTaskRunning or str(buttonId.get('id')) not in selectedGroupIds
		groupStackDisabled.append(disabled)

	groupActionDisabled = []
	for buttonId in groupActionButtonIds or []:
		disabled = isTaskRunning
		if not disabled and buttonId.get('action') in {gv.GROUP_KEEP_SELECTED, gv.GROUP_DELETE_SELECTED}:
			disabled = str(buttonId.get('id')) not in selectedGroupIds
		groupActionDisabled.append(disabled)

	# The browser owns cover labels and active styling so they never lag behind
	# the click or get restored by an older callback response.
	coverOutline = dash.no_update
	coverChildren = dash.no_update
	coverDisabled = [isTaskRunning for _ in coverButtonIds or []]

	# lg.info(f"[sim:UpdBtns] disFind[{disFind}]")

	return (
		disFind, disClear, disReset, disOk, disDel, disRm, disRS, disStack,
		disExport, groupStackDisabled, groupActionDisabled,
		coverOutline, coverChildren, coverDisabled,
	)


#------------------------------------------------------------------------
# Handle group view button click
#------------------------------------------------------------------------
@cbk(
	[
		out(ks.sto.now, "data", allow_duplicate=True),
		out(k.tabs, "active_tab", allow_duplicate=True),  # Switch to current tab
	],
	inp({"type": "btn-view-group", "id": ALL}, "n_clicks"),
	[
		ste(ks.sto.now, "data"),
	],
	prevent_initial_call=True
)
def sim_OnSwitchViewGroup(clks, dta_now):
	if not ctx.triggered: return noUpd.by(2)

	# Check if any button was actually clicked
	if not any(clks): return noUpd.by(2)

	now = Now.fromDic(dta_now)

	trgId = ctx.triggered_id

	if not trgId: return noUpd.by(2)

	assId = trgId["id"]

	lg.info(f"[sim:vgrp] switch: id[{assId}] clks[{clks}]")

	asset = db.pics.getById(assId)
	if not asset: return noUpd.by(2)

	now.sim.assAid = asset.autoId
	now.sim.assCur = db.pics.getSimAssets(asset.autoId, db.dto.rtree)

	if DEBUG: lg.info(f"[sim:vgrp] Loaded {len(now.sim.assCur)} assets for group")

	return now.toDict(), k.tabCur  # Switch to current tab


#========================================================================
# trigger modal
#========================================================================
@cbk(
	[
		out(ks.sto.nfy, "data", allow_duplicate=True),
		out(ks.sto.now, "data", allow_duplicate=True),
		out(ks.sto.mdl, "data", allow_duplicate=True),
		out(ks.sto.tsk, "data", allow_duplicate=True),
		out(ks.sto.ste, "data", allow_duplicate=True),
	],
	[
		inp(k.btnFind, "n_clicks"),
		inp(k.btnClear, "n_clicks"),
		inp(k.btnReset, "n_clicks"),
		inp(k.btnRmSel, "n_clicks"),
		inp(k.btnOkSel, "n_clicks"),
		inp(k.btnStack, "n_clicks"),
		inp(k.btnOkAll, "n_clicks"),
		inp(k.btnRmAll, "n_clicks"),
		inp({"type": gv.STACK_GROUP_BUTTON, "id": ALL}, "n_clicks"),
		inp({"type": gv.GROUP_ACTION_BUTTON, "action": ALL, "id": ALL}, "n_clicks"),
	],
	[
		ste(ks.sto.now, "data"),
		ste(ks.sto.cnt, "data"),
		ste(ks.sto.mdl, "data"),
		ste(ks.sto.tsk, "data"),
		ste(ks.sto.nfy, "data"),
		ste(ks.sto.ste, "data"),
		ste(k.cbxNChkOkAll, "value"),
		ste(k.cbxNChkRmSel, "value"),
		ste(k.cbxNChkOkSel, "value"),
		ste(k.cbxNChkRmAll, "value"),
		ste(k.cbxStackDelete, "value"),
		ste({"type": gv.STACK_GROUP_DELETE, "id": ALL}, "value"),
		ste({"type": gv.STACK_GROUP_DELETE, "id": ALL}, "id"),
	],
	prevent_initial_call=True
)
def sim_RunModal(
	clk_fnd, clk_clr, clk_rst, clk_rm, clk_rs, clk_stack, clk_ok, clk_ra, clk_stack_groups, clk_group_actions,
	dta_now, dta_cnt, dta_mdl, dta_tsk, dta_nfy, dta_ste,
	nchkOkAll, nchkRmSel, ncRS, ncRA, stackDelete, groupDeleteValues, groupDeleteIds
):
	if not ctx.triggered:
		lg.info(f"[sim:RunModal] non clicked")
		return noUpd.by(5)
	triggerValue = ctx.triggered[0].get('value')
	if (isinstance(triggerValue, list) and not any(triggerValue)) or (not isinstance(triggerValue, list) and not triggerValue):
		return noUpd.by(5)

	trgId = getTrgId()
	# if trgId: lg.info(f"[sim:RunModal] ---------->> trig: [ {trgId} ]")

	now = Now.fromDic(dta_now)
	cnt = Cnt.fromDic(dta_cnt)
	mdl = Mdl.fromDic(dta_mdl)
	tsk = Tsk.fromDic(dta_tsk)
	nfy = Nfy.fromDic(dta_nfy)
	ste = Ste.fromDic(dta_ste)
	isGroupAction = trgId.get('type') == gv.GROUP_ACTION_BUTTON
	groupAction = trgId.get('action') if isGroupAction else None
	groupTargetId = trgId.get('id') if isGroupAction else None

	retNow, retTsk, retSte = noUpd, noUpd, noUpd


	# Check if any task is already running
	from mod.mgr.tskSvc import mgr
	if mgr:
		for _, info in mgr.list().items():
			if info.status.value in ['pending', 'running']:
				nfy.warn(f"Task already running, please wait for it to complete")
				return noUpd.by(5).upd(0, nfy)

	if tsk.id:
		if mgr and mgr.getInfo(tsk.id):
			ti = mgr.getInfo(tsk.id)
			if ti and ti.status in ['pending', 'running']:
				nfy.warn(f"[similar] Task already running: {tsk.id}")
				return noUpd.by(5).upd(0, nfy)
			# lg.info(f"[similar] Clearing completed task: {tsk.id}")
			tsk.id = None
			tsk.cmd = None

	lg.info(f"[similar] trig[{trgId}] tsk[{tsk}]")

	#------------------------------------------------------------------------
	if trgId == k.btnClear:
		cntRs = db.pics.countHasSimIds(isOk=0)
		if cntRs <= 0:
			nfy.warn(f"[similar] No search records to clear")
			return noUpd.by(5).upd(0, nfy)

		mdl.reset()
		mdl.id = ks.pg.similar
		mdl.cmd = ks.cmd.sim.clear
		mdl.msg = [
			f"Clear search records but keep resolved items?", htm.Br(),
			f"Will clear ({cntRs}) search records", htm.Br(),
			htm.B("Resolved items (simOk=1) will be kept"), htm.Br(),
		]
	#------------------------------------------------------------------------
	elif trgId == k.btnReset:
		cntOk = db.pics.countSimOk(isOk=1)
		cntRs = db.pics.countHasSimIds()
		if cntOk <= 0 and cntRs <= 0:
			nfy.warn(f"[similar] DB does not contain any similarity records")
			return noUpd.by(5).upd(0, nfy)

		mdl.reset()
		mdl.id = ks.pg.similar
		mdl.cmd = ks.cmd.sim.reset
		mdl.msg = [
			f"Are you sure you want to reset all records?", htm.Br(),
			f"include resolved({cntOk}) and search({cntRs})", htm.Br(),
			htm.B("This operation cannot be undone"), htm.Br(),
			"You may need to perform all similarity searches again."
		]
	#------------------------------------------------------------------------
	elif trgId == k.btnRmSel or groupAction == gv.GROUP_DELETE_SELECTED:
		try: assAll = sim_stack.assetsForGroup(now.sim.assCur, db.dto.muod.on, groupTargetId)
		except ValueError as e:
			nfy.warn(str(e))
			return noUpd.by(5).upd(0, nfy)
		ass = ste.getSelected(assAll)
		assKeep = [a for a in assAll if a.autoId not in {s.autoId for s in ass}]
		cnt = len(ass)

		lg.info(f"[sim:delSels] {cnt} assets selected")

		if cnt > 0:
			if db.dto.mrg.on:
				errs = immich.validateKeepPaths(assKeep)
				if errs:
					nfy.error(f"Cannot merge: {errs[0]}")
					return noUpd.by(5).upd(0, nfy)

			mdl.reset()
			mdl.id = ks.pg.similar
			mdl.cmd = ks.cmd.sim.selRm
			mdl.args = {'targetGroupId': groupTargetId}
			if groupTargetId is not None and assKeep:
				mdl.args['allowMarkResolved'] = True
			mdl.msg = [
				f"Are you sure you want to Delete selected images( {cnt} ) and Keep others( {len(assKeep)} )"
				f" in {'group ' + str(groupTargetId) if groupTargetId is not None else 'the current results'}?", htm.Br(),
				htm.B("This operation cannot be undone"),
			]
			if groupTargetId is not None:
				mdl.msg.extend([htm.Br(), "Choose Confirm to leave survivors open, or Confirm & mark resolved to finish this group now."])

			if db.dto.mrg.on: mdl.msg.extend(_mkMrgMsg(assKeep))

			if groupTargetId is None and nchkRmSel:
				retTsk = mdl.mkTsk()
				mdl.reset()
	#------------------------------------------------------------------------
	elif trgId == k.btnOkSel or groupAction == gv.GROUP_KEEP_SELECTED:
		try: assAll = sim_stack.assetsForGroup(now.sim.assCur, db.dto.muod.on, groupTargetId)
		except ValueError as e:
			nfy.warn(str(e))
			return noUpd.by(5).upd(0, nfy)
		ass = ste.getSelected(assAll)
		assOthers = [a for a in assAll if a.autoId not in {s.autoId for s in ass}]
		cnt = len(ass)

		lg.info(f"[sim:resolveSels] {cnt} assets selected")

		if cnt > 0:
			if db.dto.mrg.on:
				errs = immich.validateKeepPaths(ass)
				if errs:
					nfy.error(f"Cannot merge: {errs[0]}")
					return noUpd.by(5).upd(0, nfy)

			mdl.reset()
			mdl.id = ks.pg.similar
			mdl.cmd = ks.cmd.sim.selOk
			mdl.args = {'targetGroupId': groupTargetId}
			if groupTargetId is not None:
				mdl.args['allowMarkResolved'] = True
			mdl.msg = [
				f"Are you sure you want to Keep selected images( {cnt} ) and Delete others( {len(assOthers)} )"
				f" in {'group ' + str(groupTargetId) if groupTargetId is not None else 'the current results'}?", htm.Br(),
				htm.B("This operation cannot be undone"),
			]
			if groupTargetId is not None:
				mdl.msg.extend([htm.Br(), "Choose Confirm to leave survivors open, or Confirm & mark resolved to finish this group now."])

			if db.dto.mrg.on: mdl.msg.extend(_mkMrgMsg(ass))

			if groupTargetId is None and ncRS:
				retTsk = mdl.mkTsk()
				mdl.reset()
	#------------------------------------------------------------------------
	elif trgId == k.btnStack or trgId.get('type') == gv.STACK_GROUP_BUTTON:
		targetGroupId = trgId.get('id') if trgId.get('type') == gv.STACK_GROUP_BUTTON else None
		deleteOthers = bool(stackDelete)
		if targetGroupId is not None:
			deleteByGroup = {
				str(item.get('id')): bool(value)
				for item, value in zip(groupDeleteIds or [], groupDeleteValues or [])
			}
			deleteOthers = deleteByGroup.get(str(targetGroupId), False)

		try:
			plan = sim_stack.buildPlan(
				now.sim.assCur,
				ste.selectedIds,
				db.dto.muod.on,
				targetGroupId=targetGroupId,
				coverIds=ste.stackCoverIds,
			)
		except ValueError as e:
			nfy.warn(str(e))
			return noUpd.by(5).upd(0, nfy)

		if deleteOthers and db.dto.mrg.on:
			errs = immich.validateKeepPaths(plan.selected)
			if errs:
				nfy.error(f"Cannot merge: {errs[0]}")
				return noUpd.by(5).upd(0, nfy)

		mdl.reset()
		mdl.id = ks.pg.similar
		mdl.cmd = ks.cmd.sim.stack
		mdl.args = {
			'selectedIds': [asset.autoId for asset in plan.selected],
			'coverIds': plan.coverIds,
			'targetGroupId': targetGroupId,
			'deleteOthers': deleteOthers,
		}
		if targetGroupId is not None:
			mdl.args['allowMarkResolved'] = True
		mdl.msg = [
			f"Finalize {len(plan.stacks)} Immich stack(s) from {len(plan.selected)} selected assets across {len(plan.groups)} group(s)?",
			htm.Br(),
			"A chosen cover is used; otherwise existing stacks keep their cover and new stacks use the first displayed selection.",
			htm.Br(),
			(
				f"Delete the {len(plan.others)} remaining assets; this group stays open until Mark resolved."
				if targetGroupId is not None and deleteOthers else
				"Keep this group open until Mark resolved."
				if targetGroupId is not None else
				f"Delete the {len(plan.others)} remaining assets and finish those groups."
				if deleteOthers else
				"Keep the groups open for more stacks; a group finishes automatically once every image belongs to the same stack."
			),
		]
		if deleteOthers:
			mdl.msg.extend([htm.Br(), htm.B("Deleting unselected assets cannot be undone here.")])
			if db.dto.mrg.on: mdl.msg.extend(_mkMrgMsg(plan.selected))
		if targetGroupId is not None:
			mdl.msg.extend([htm.Br(), "Choose Confirm to leave the group open, or Confirm & mark resolved to finish it now."])
	#------------------------------------------------------------------------
	elif trgId == k.btnRmAll or groupAction == gv.GROUP_DELETE_ALL:
		try: ass = sim_stack.assetsForGroup(now.sim.assCur, db.dto.muod.on, groupTargetId)
		except ValueError as e:
			nfy.warn(str(e))
			return noUpd.by(5).upd(0, nfy)
		cnt = len(ass)

		lg.info(f"[sim:delAll] {cnt} assets to delete")

		if cnt > 0:
			mdl.reset()
			mdl.id = ks.pg.similar
			mdl.cmd = ks.cmd.sim.allRm
			mdl.args = {'targetGroupId': groupTargetId}
			mdl.msg = [
				f"Are you sure you want to Delete all {cnt} images"
				f" in {'group ' + str(groupTargetId) if groupTargetId is not None else 'the current results'}?", htm.Br(),
				htm.B("This operation cannot be undone"),
			]

			if groupTargetId is None and ncRA:
				retTsk = mdl.mkTsk()
				mdl.reset()
	#------------------------------------------------------------------------
	elif trgId == k.btnOkAll or groupAction == gv.GROUP_MARK_RESOLVED:
		try: ass = sim_stack.assetsForGroup(now.sim.assCur, db.dto.muod.on, groupTargetId)
		except ValueError as e:
			nfy.warn(str(e))
			return noUpd.by(5).upd(0, nfy)
		cnt = len(ass)

		lg.info(f"[sim:resolve] {cnt} assets")

		if cnt > 0:
			mdl.reset()
			mdl.id = ks.pg.similar
			mdl.cmd = ks.cmd.sim.allOk
			mdl.args = {'targetGroupId': groupTargetId}
			mdl.msg = (
				f"Mark group {groupTargetId} resolved and remove its {cnt} images from the current list?"
				if groupTargetId is not None else
				f"Are you sure you want to Keep all {cnt} images in the current results?"
			)

			if groupTargetId is None and nchkOkAll:
				retTsk = mdl.mkTsk()
				mdl.reset()
	#------------------------------------------------------------------------
	elif trgId == k.btnFind:
		retSte = ste.clear()
		if cnt.vec <= 0:
			nfy.error("No vector data to process")
			now.sim.clearAll()
			return noUpd.by(5).upd(0, [nfy, now])

		thMin = db.dto.thMin

		lg.info(('='*30)+'[btnFind]'+('='*30))
		lg.info(f"[thMin] min[{thMin}] max[1.0]")

		dstAss: Optional[models.Asset] = None

		# asset from url
		if now.sim.aidUrl and now.sim.assAid and trgId != "sim-btn-fnd": dstAss = db.pics.getByAutoId(now.sim.assAid)

		#------------------------------------------------
		if not dstAss:
			asses = db.pics.getAnyNonSim()
			if asses:
				dstAss = asses[0]
				lg.info(f"[sim] use #{dstAss.autoId} assetId[{dstAss.id}]")

		now.sim.clearAll()

		#------------------------------------------------
		if not dstAss: nfy.warn(f"[sim] not any asset to find..")
		else:
			now.sim.assAid = dstAss.autoId

			mdl.id = ks.pg.similar
			mdl.cmd = ks.cmd.sim.fnd
			tsk = mdl.mkTsk()
			mdl.reset()

			lg.info(f"[sim:run] now.sim.assAid[{now.sim.assAid}]")

			# only find auto trigger tsk
			retTsk = tsk
			retNow = now


	lg.info(f"[similar] modal[{mdl.id}] cmd[{mdl.cmd}]")

	return noUpd.by(5).upd(0, [nfy, retNow, mdl, retTsk, retSte])


#========================================================================
# task acts
#========================================================================
from mod.models import IFnProg


def queueAutoNext(sto: models.ITaskStore):
	tsk = sto.tsk

	asses = db.pics.getAnyNonSim()
	if asses:
		ass = asses[0]
		lg.info(f"[sim] auto found non-simOk assetId[{ass.id}]")

		mdl = models.Mdl()
		mdl.id = ks.pg.similar
		mdl.cmd = ks.cmd.sim.fnd
		mdl.args = {'thMin': db.dto.thMin}

		ntsk = mdl.mkTsk()
		ntsk.args['assetId'] = ass.id

		sto.tsk.nexts.append(ntsk)

		sto.tsk = tsk
		# nfy.success([f"Auto-Find next: #{ass.autoId}"])


def sim_FindSimilar(doReport: IFnProg, sto: models.ITaskStore):
	from db import sim

	nfy, now, tsk = sto.nfy, sto.now, sto.tsk

	maxItems = db.dto.rtreeMax
	thMin = db.dto.thMin
	thMin = co.vad.float(thMin, 0.9)

	fromUrl = now.sim.assAid > 0 and now.sim.assAid == now.sim.aidUrl

	lg.info(f"[sim:fs] config maxItems[{maxItems}] fromUrl[{fromUrl}]")


	try:
		t0 = time.time()
		lg.info(f"[sim:fs] now.sim.assAid[{now.sim.assAid}]")
		doReport(1, f"prepare..")

		try: asset = sim.findCandidate(now.sim.assAid, tsk.args)
		except RuntimeError as e:
			if "already searched" in str(e):
				now.sim.assCur = []
				return sto, [str(e)]
			raise e

		sRst = sim.searchBy(asset, doReport, sto.isCancelled, fromUrl)
		grps = sRst.groups

		if sRst.corrupted:
			nfy.warn(f"{len(sRst.corrupted)} asset(s) had corrupted vector indexes (auto-repair failed). Please re-run Vector to resync. IDs: {sRst.corrupted}")

		if not grps:
			nfy.info(f"No similar Threshold[{thMin}] groups found for asset #{asset.autoId}")
			now.sim.assCur = []
			return sto, f"No similar Threshold[{thMin}] groups found for asset #{asset.autoId}"

		if not grps[0].assets:
			nfy.info(f"Asset #{asset.autoId} no similar found")
			return sto, f"Asset #{asset.autoId} no similar found"

		# Auto mark single items as resolved
		db.pics.setSimAutoMark()

		assets = []
		for g in grps: assets.extend(g.assets)

		doReport(95, f"Finalizing {len(grps)} group(s) with {len(assets)} total assets")
		time.sleep(0.5)

		# Update state
		now.sim.assAid = asset.autoId
		now.sim.assCur = assets
		now.sim.activeTab = k.tabCur

		lg.info(f"[sim:fs] done, found {len(grps)} group(s) with {len(assets)} assets")
		lg.info(f"[sim:fs] assets autoIds: {[a.autoId for a in assets]}")

		if not now.sim.assCur: raise RuntimeError(f"No groups found")

		doReport(100, f"Completed finding {len(grps)} similar photo group(s)")

		# Generate completion message
		if db.dto.muod.on:
			mxGrp = db.dto.muod.sz

			msg = [f"Found {len(grps)} similar photo group(s) with {len(assets)} total photos"]
			if len(grps) >= mxGrp: msg.append(f"Reached maximum group limit ({mxGrp} groups).")
		else:
			root = grps[0].asset
			assert root is not None
			cntInfos = len(grps[0].bseInfos)
			cntAll = len(assets)
			hasRoot = any(a.autoId == root.autoId for a in assets)
			msg = [f"Found {cntInfos} similar, displaying {cntAll} for #{root.autoId} ({root.id})"]
			if not hasRoot: msg.append(f"⚠️ Root #{root.autoId} missing from display!")
			if cntAll > cntInfos: msg.append(f"include ({cntAll - cntInfos}) asset extra tree in similar tree.")
			if cntAll >= maxItems: msg.append(f"Reached maximum search limit ({maxItems} items).")

		# Clear selection state, auto-select is now calculated on client side
		sto.ste.clear()
		sto.ste.cntTotal = len(now.sim.assCur) if now.sim.assCur else 0

		elapsed = time.time() - t0
		msg.append(f"Elapsed: {elapsed:.1f}s")

		nfy.success(msg)
		return sto, msg
	except Exception as e:
		msg = f"[sim:fs] Similar search failed: {str(e)}"
		nfy.error(msg)
		lg.error(traceback.format_exc())
		now.sim.clearAll()
		sto.ste.clear()
		raise RuntimeError(msg)



def sim_ClearSims(doReport: IFnProg, sto: models.ITaskStore):
	nfy, now, tsk = sto.nfy, sto.now, sto.tsk

	try:
		keepSimOk = tsk.cmd == ks.cmd.sim.clear

		doReport(10, "Preparing to clear similarity records...")

		if keepSimOk:
			cntRs = db.pics.countHasSimIds(isOk=0)
			if cntRs <= 0:
				msg = "No search records to clear"
				lg.info(msg)
				nfy.info(msg)
				return sto, msg
		else:
			cntOk = db.pics.countSimOk(isOk=1)
			cntRs = db.pics.countHasSimIds()
			if cntOk <= 0 and cntRs <= 0:
				msg = "No similarity records to clear"
				lg.info(msg)
				nfy.info(msg)
				return sto, msg

		doReport(30, "Clearing similarity records from database...")

		db.pics.clearAllSimIds(keepSimOk=keepSimOk)

		doReport(90, "Updating dynamic data...")

		now.sim.clearAll()
		sto.ste.clear()

		doReport(100, "Clear completed")

		if keepSimOk: msg = f"Successfully cleared search records but kept resolved items"
		else: msg = f"Successfully cleared all similarity records"

		lg.info(f"[sim_Clear] {msg}")
		nfy.success(msg)

		return sto, msg
	except Exception as e:
		msg = f"Failed to clear similarity records: {str(e)}"
		lg.error(f"[sim_Clear] {msg}")
		lg.error(traceback.format_exc())
		nfy.error(msg)
		raise RuntimeError(msg)



def _actionAssets(sto: models.ITaskStore) -> tuple[list[models.Asset], Optional[int]]:
	targetGroupId = sto.tsk.args.get('targetGroupId')
	assets = sim_stack.assetsForGroup(sto.now.sim.assCur, db.dto.muod.on, targetGroupId)
	return assets, targetGroupId


def _removeHandledAssets(sto: models.ITaskStore, handledAssets: list[models.Asset]):
	handledIds = {asset.autoId for asset in handledAssets}
	sto.now.sim.assCur, sto.ste.selectedIds = sim_stack.removeHandled(
		sto.now.sim.assCur,
		sto.ste.selectedIds,
		handledAssets,
	)
	sto.ste.stackCoverIds = [autoId for autoId in sto.ste.stackCoverIds if autoId not in handledIds]
	sto.now.sim.assAid = sto.now.sim.assCur[0].autoId if sto.now.sim.assCur else 0
	sto.ste.cntTotal = len(sto.now.sim.assCur)

	if not sto.now.sim.assCur:
		sto.now.sim.assPend.clear()
		if not db.dto.autoNext: sto.now.sim.activeTab = k.tabPnd
		else: queueAutoNext(sto)


def _resolveTargetGroupIfRequested(sto: models.ITaskStore, targetGroupId: Optional[int]) -> int:
	if targetGroupId is None or not sto.tsk.args.get('markResolved'): return 0

	try:
		remainingAssets = sim_stack.assetsForGroup(sto.now.sim.assCur, db.dto.muod.on, targetGroupId)
	except ValueError:
		return 0

	if not remainingAssets: return 0
	db.pics.setResolveBy(remainingAssets)
	_removeHandledAssets(sto, remainingAssets)
	return len(remainingAssets)


def sim_SelectedDelete(doReport: IFnProg, sto: models.ITaskStore):
	nfy, now, ste = sto.nfy, sto.now, sto.ste
	targetGroupId = sto.tsk.args.get('targetGroupId')
	xmpInfos = []
	try:
		assAlls, targetGroupId = _actionAssets(sto)
		assSels = ste.getSelected(assAlls) if ste else []
		assLefts = [a for a in assAlls if a.autoId not in {s.autoId for s in assSels}]

		cntSelect = len(assSels)
		msg = f"[sim] Delete Selected Assets( {cntSelect} ) Success!"

		if not assSels or cntSelect == 0: raise RuntimeError("Selected not found")

		lg.info(f"[sim:delSel] delete[{cntSelect}] keep[{len(assLefts)}] mergeOn[{db.dto.mrg.on}]")

		with psql.mkConn() as conn:
			with conn.cursor() as cur:
				if db.dto.mrg.on:
					opts = immich.MergeOpts(
						albums=db.dto.mrg.albums,
						favorites=db.dto.mrg.favs,
						tags=db.dto.mrg.tags,
						rating=db.dto.mrg.rating,
						description=db.dto.mrg.desc,
						location=db.dto.mrg.loc,
						visibility=db.dto.mrg.vis
					)
					result = immich.mergeMetadata(assLefts, assSels, opts, cur)
					xmpInfos = result.get('xmpInfos', [])

				immich.trashByAssets(assSels, cur)
				conn.commit()

		db.pics.deleteBy(assSels)
		if targetGroupId is None: db.pics.setResolveBy(assLefts)

		if xmpInfos: immich.cleanupXmpBak(xmpInfos)

		_removeHandledAssets(sto, assAlls if targetGroupId is None else assSels)
		resolvedCount = _resolveTargetGroupIfRequested(sto, targetGroupId)
		if resolvedCount:
			msg += f" Marked group {targetGroupId} resolved with {resolvedCount} remaining image(s)."
		elif targetGroupId is not None and assLefts:
			msg += f" Group {targetGroupId} remains open with {len(assLefts)} image(s)."

		nfy.success(msg)

		return sto, msg
	except Exception as e:
		if xmpInfos: immich.restoreXmpBak(xmpInfos)
		msg = f"[sim] Delete selected failed: {str(e)}"
		nfy.error(msg)
		lg.error(traceback.format_exc())
		if targetGroupId is None:
			now.sim.clearAll()
			sto.ste.clear()

		raise RuntimeError(msg)


def sim_SelectedResolve(doReport: IFnProg, sto: models.ITaskStore):
	nfy, now, ste = sto.nfy, sto.now, sto.ste
	targetGroupId = sto.tsk.args.get('targetGroupId')
	xmpInfos = []
	try:
		assAlls, targetGroupId = _actionAssets(sto)
		assSels = ste.getSelected(assAlls) if ste else []
		assOthers = [a for a in assAlls if a.autoId not in {s.autoId for s in assSels}]

		cntSelect = len(assSels)
		cntOthers = len(assOthers)
		msg = (
			f"[sim] Resolve Selected Assets( {cntSelect} ) and Delete Others( {cntOthers} ) Success!"
			if targetGroupId is None else
			f"[sim] Kept Selected Assets( {cntSelect} ) and Deleted Others( {cntOthers} ) Success!"
		)

		if not assSels or cntSelect == 0: raise RuntimeError("Selected not found")

		lg.info(f"[sim:selOk] {'resolve' if targetGroupId is None else 'keep'} assets[{cntSelect}] delete[ {cntOthers} ] mergeOn[{db.dto.mrg.on}]")

		with psql.mkConn() as conn:
			with conn.cursor() as cur:
				if db.dto.mrg.on:
					opts = immich.MergeOpts(
						albums=db.dto.mrg.albums,
						favorites=db.dto.mrg.favs,
						tags=db.dto.mrg.tags,
						rating=db.dto.mrg.rating,
						description=db.dto.mrg.desc,
						location=db.dto.mrg.loc,
						visibility=db.dto.mrg.vis
					)
					result = immich.mergeMetadata(assSels, assOthers, opts, cur)
					xmpInfos = result.get('xmpInfos', [])

				if assOthers: immich.trashByAssets(assOthers, cur)
				conn.commit()

		if assOthers: db.pics.deleteBy(assOthers)
		if targetGroupId is None: db.pics.setResolveBy(assSels)

		if xmpInfos: immich.cleanupXmpBak(xmpInfos)

		_removeHandledAssets(sto, assAlls if targetGroupId is None else assOthers)
		resolvedCount = _resolveTargetGroupIfRequested(sto, targetGroupId)
		if resolvedCount:
			msg += f" Marked group {targetGroupId} resolved with {resolvedCount} kept image(s)."
		elif targetGroupId is not None:
			msg += f" Group {targetGroupId} remains open with {len(assSels)} image(s)."

		return sto, msg
	except Exception as e:
		if xmpInfos: immich.restoreXmpBak(xmpInfos)
		msg = f"[sim] Resolve selected failed: {str(e)}"
		nfy.error(msg)
		lg.error(traceback.format_exc())
		if targetGroupId is None:
			now.sim.clearAll()
			sto.ste.clear()

		raise RuntimeError(msg)


def sim_StackSelected(doReport: IFnProg, sto: models.ITaskStore):
	nfy, now, ste, tsk = sto.nfy, sto.now, sto.ste, sto.tsk
	xmpInfos = []
	try:
		selectedIds = [int(autoId) for autoId in tsk.args.get('selectedIds', [])]
		coverIds = [int(autoId) for autoId in tsk.args.get('coverIds', [])]
		targetGroupId = tsk.args.get('targetGroupId')
		deleteOthers = bool(tsk.args.get('deleteOthers', False))
		plan = sim_stack.buildPlan(
			now.sim.assCur,
			selectedIds,
			db.dto.muod.on,
			targetGroupId=targetGroupId,
			coverIds=coverIds,
		)

		doReport(5, f"Preparing {len(plan.stacks)} stack(s) across {len(plan.groups)} group(s)")
		stackMethods = {}
		stackResults = []
		protectedStackAssetIds = set()
		deleteAssets = []
		deleteIds = set()

		with psql.mkConn() as conn:
			with conn.cursor() as cur:
				for idx, stack in enumerate(plan.stacks):
					doReport(10 + int(45 * idx / len(plan.stacks)), f"Stacking group {stack.groupId}")
					stackId, method, memberIds, primaryId = immich.stackByAssetsPreferApi(
						stack.assets,
						cur,
						preferredPrimaryId=stack.primary.id if stack.coverAutoId is not None else None,
					)
					stackMethods[stackId] = method
					stackResults.append((stackId, primaryId, memberIds))
					protectedStackAssetIds.update(memberIds)

				if deleteOthers:
					deleteAssets, _ = sim_stack.splitUnselectedByStackMembership(
						plan.others,
						protectedStackAssetIds,
					)
					deleteIds = {asset.autoId for asset in deleteAssets}

				if deleteOthers and db.dto.mrg.on:
					for group in plan.groups:
						groupDeleteAssets = [asset for asset in group.others if asset.autoId in deleteIds]
						if not groupDeleteAssets: continue
						groupKeepAssets = [asset for asset in group.assets if asset.autoId not in deleteIds]
						result = immich.mergeMetadata(groupKeepAssets, groupDeleteAssets, immich.MergeOpts(
							albums=db.dto.mrg.albums,
							favorites=db.dto.mrg.favs,
							tags=db.dto.mrg.tags,
							rating=db.dto.mrg.rating,
							description=db.dto.mrg.desc,
							location=db.dto.mrg.loc,
							visibility=db.dto.mrg.vis,
						), cur)
						xmpInfos.extend(result.get('xmpInfos', []))

				if deleteAssets:
					doReport(70, f"Moving {len(deleteAssets)} unselected asset(s) to trash")
					immich.trashByAssets(deleteAssets, cur)
				conn.commit()

		stackMemberIds = {memberId for _, _, memberIds in stackResults for memberId in memberIds}
		for asset in now.sim.assCur:
			if asset.id in stackMemberIds and asset.ex is None: asset.ex = models.AssetExInfo()
		sim_stack.applyStackMetadata(now.sim.assCur, stackResults)

		if targetGroupId is not None:
			resolvedAssets = []
			handledAssets = deleteAssets
			completedGroupIds = []
		elif deleteOthers:
			resolvedAssets = [asset for asset in plan.assets if asset.autoId not in deleteIds]
			handledAssets = plan.assets
			completedGroupIds = [group.groupId for group in plan.groups]
		else:
			resolvedAssets, completedGroupIds = sim_stack.fullyStackedGroupAssets(plan)
			handledAssets = resolvedAssets

		if deleteAssets: db.pics.deleteBy(deleteAssets)
		if resolvedAssets: db.pics.setResolveBy(resolvedAssets)

		if xmpInfos: immich.cleanupXmpBak(xmpInfos)

		if handledAssets: _removeHandledAssets(sto, handledAssets)
		stackedAutoIds = {asset.autoId for asset in plan.selected}
		ste.selectedIds = [autoId for autoId in ste.selectedIds if autoId not in stackedAutoIds]
		ste.stackCoverIds = [autoId for autoId in ste.stackCoverIds if autoId not in stackedAutoIds]
		resolvedTargetCount = _resolveTargetGroupIfRequested(sto, targetGroupId)

		apiStacks = sum(method == 'api' for method in stackMethods.values())
		dbStacks = sum(method == 'database' for method in stackMethods.values())
		doReport(100, f"Finalized {len(stackMethods)} stack(s)")
		if resolvedTargetCount:
			assetResult = f"marked group {targetGroupId} resolved with {resolvedTargetCount} remaining asset(s)"
			if deleteAssets: assetResult = f"deleted {len(deleteAssets)} remaining asset(s) and {assetResult}"
		elif targetGroupId is not None:
			assetResult = f"deleted {len(deleteAssets)} remaining asset(s)" if deleteOthers else "kept remaining assets"
			assetResult += f" and left group {targetGroupId} open for Mark resolved"
		elif deleteOthers:
			protectedOthers = len(plan.others) - len(deleteAssets)
			assetResult = f"deleted {len(deleteAssets)} remaining asset(s) and finished {len(completedGroupIds)} group(s)"
			if protectedOthers:
				assetResult += f" and preserved {protectedOthers} existing stack member(s)"
		else:
			openGroups = len(plan.groups) - len(completedGroupIds)
			assetResult = f"resolved {len(completedGroupIds)} fully stacked group(s)"
			if openGroups: assetResult += f" and left {openGroups} group(s) open for more stacks"
		msg = (
			f"Finalized {len(stackMethods)} Immich stack(s) across {len(plan.groups)} group(s); "
			f"{assetResult} (API: {apiStacks}, database: {dbStacks})."
		)
		nfy.success(msg)
		return sto, msg
	except Exception as e:
		if xmpInfos: immich.restoreXmpBak(xmpInfos)
		msg = f"[sim] Stack selected failed: {str(e)}"
		nfy.error(msg)
		lg.error(traceback.format_exc())
		raise RuntimeError(msg)


def sim_AllResolve(doReport: IFnProg, sto: models.ITaskStore):
	nfy, now = sto.nfy, sto.now
	targetGroupId = sto.tsk.args.get('targetGroupId')
	try:
		assets, targetGroupId = _actionAssets(sto)
		cntAll = len(assets)
		msg = f"[sim] set Resolved Assets( {cntAll} ) Success!"

		if not assets or cntAll == 0: raise RuntimeError("Current Assets not found")
		lg.info(f"[sim:allResolve] resolve assets[{cntAll}] ")

		db.pics.setResolveBy(assets)

		_removeHandledAssets(sto, assets)

		return sto, msg
	except Exception as e:
		msg = f"[sim] Resolved All failed: {str(e)}"
		nfy.error(msg)
		lg.error(traceback.format_exc())
		if targetGroupId is None:
			now.sim.clearAll()
			sto.ste.clear()

		raise RuntimeError(msg)


def sim_AllDelete(doReport: IFnProg, sto: models.ITaskStore):
	nfy, now = sto.nfy, sto.now
	targetGroupId = sto.tsk.args.get('targetGroupId')
	try:
		assets, targetGroupId = _actionAssets(sto)
		cntAll = len(assets)
		msg = f"[sim] Delete All Assets( {cntAll} ) Success!"

		if not assets or cntAll == 0: raise RuntimeError("Current Assets not found")

		lg.info(f"[sim:allDel] delete assets[{cntAll}] ")

		with psql.mkConn() as conn:
			with conn.cursor() as cur:
				immich.trashByAssets(assets, cur)
				conn.commit()

		db.pics.deleteBy(assets)

		_removeHandledAssets(sto, assets)

		return sto, msg
	except Exception as e:
		msg = f"[sim] Delete all failed: {str(e)}"
		nfy.error(msg)
		lg.error(traceback.format_exc())
		if targetGroupId is None:
			now.sim.clearAll()
			sto.ste.clear()

		raise RuntimeError(msg)



#========================================================================
# Set up global functions
#========================================================================
mapFns[ks.cmd.sim.fnd] = sim_FindSimilar
mapFns[ks.cmd.sim.clear] = sim_ClearSims
mapFns[ks.cmd.sim.reset] = sim_ClearSims
mapFns[ks.cmd.sim.selOk] = sim_SelectedResolve
mapFns[ks.cmd.sim.selRm] = sim_SelectedDelete
mapFns[ks.cmd.sim.stack] = sim_StackSelected
mapFns[ks.cmd.sim.allOk] = sim_AllResolve
mapFns[ks.cmd.sim.allRm] = sim_AllDelete
