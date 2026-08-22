from typing import Optional
from dsh import htm, dcc, dbc, inp, out, ste, cbk, ctx, noUpd, getTrgId, ALL
from dsh import ccbk, cbkFn

from conf import ks
from mod import models
from ui import gvEx
from util import log
from db import dto


lg = log.get(__name__)


class k:
	modal = "img-modal"
	store = ks.sto.mdlImg
	content = "img-modal-content"
	status = "img-modal-status"
	floatL = "img-modal-floatL"
	floatR = "img-modal-floatR"

	imgHelp = "img-modal-help"
	btnHelp = "btn-img-help"

	imgInfo = "img-modal-info"
	btnInfo = "btn-img-info"

	btnMode = "btn-img-mode"
	btnPrev = "btn-img-prev"
	btnNext = "btn-img-next"
	btnSelect = "btn-img-select"
	navCtrls = "img-nav-controls"

	txtHAuto = "Use automatic height"
	txtHFix = "Use fixed height"

	cssAuto = "auto"



#------------------------------------------------------------------------
# ui
#------------------------------------------------------------------------
layoutHelp = htm.Div([
	htm.H6("Keyboard shortcuts", className="mb-2"),
	htm.Table([
		htm.Tbody([
			htm.Tr([htm.Td(htm.Code("Space")), htm.Td("Toggle selection", className="ps-3")]),
			htm.Tr([htm.Td(htm.Code("← / h")), htm.Td("Previous image", className="ps-3")]),
			htm.Tr([htm.Td(htm.Code("→ / l")), htm.Td("Next image", className="ps-3")]),
			htm.Tr([htm.Td(htm.Code("i")), htm.Td("Toggle details", className="ps-3")]),
			htm.Tr([htm.Td(htm.Code("m")), htm.Td("Toggle scale mode", className="ps-3")]),
			htm.Tr([htm.Td(htm.Code("ESC / q")), htm.Td("Close preview", className="ps-3")]),
			htm.Tr([htm.Td(htm.Code("?")), htm.Td("Toggle shortcuts", className="ps-3")]),
		])
	], className="small help-content"),
], id=k.imgHelp, className="help")

layoutInfo = htm.Div([
	htm.H6("Image details", className="mb-2"),
	htm.Div(id=f"{k.imgInfo}-content", className="info-content"),
], id=k.imgInfo, className="info")


def render():
	return [
		htm.Div(id={"type": "dummy-output", "id": "mdlimg-current"}, style={"display": "none"}),
		htm.Div(id={"type": "dummy", "id": "mdlimg-db"}, style={"display": "none"}),

		dbc.Modal([
			dbc.ModalHeader([
				htm.Div("Image preview", className="img-viewer-title me-auto"),
				htm.Div([
					dbc.Button(
						[htm.I(className="bi bi-arrows-fullscreen"), htm.Span("Fit screen", className="img-viewer-mode-label")],
						id=k.btnMode,
						color="secondary",
						outline=False,
						size="sm",
						className="img-viewer-mode",
						title="Toggle between fit-to-screen and actual-size viewing",
					),
					htm.Div([
						dbc.Button(
							[htm.I(className="bi bi-info-circle"), htm.Span("Details", className="visually-hidden")],
							id=k.btnInfo,
							color="secondary",
							outline=False,
							size="sm",
							className="img-viewer-header-icon",
							title="Show or hide image details",
						),
						layoutInfo,
					], className="img-viewer-header-action img-viewer-info-action"),
					htm.Div([
						dbc.Button(
							[htm.I(className="bi bi-keyboard"), htm.Span("Shortcuts", className="visually-hidden")],
							id=k.btnHelp,
							color="secondary",
							outline=False,
							size="sm",
							className="img-viewer-header-icon",
							title="Show or hide keyboard shortcuts",
						),
						layoutHelp,
					], className="img-viewer-header-action img-viewer-help-action"),
				], className="img-viewer-header-actions"),
			], close_button=True, className="img-viewer-header"),
			dbc.ModalBody([
				htm.Div([
					htm.Div(id=k.content, className="img img-viewer-stage"),
					htm.Button(
						htm.I(className="bi bi-chevron-left"),
						id=k.btnPrev,
						className="btn btn-secondary img-viewer-nav img-viewer-nav-prev",
						style={"zIndex": 1000, "display": "none"},
						title="Previous image",
						**{"aria-label": "Previous image"},
					),
					htm.Button(
						htm.I(className="bi bi-chevron-right"),
						id=k.btnNext,
						className="btn btn-secondary img-viewer-nav img-viewer-nav-next",
						style={"zIndex": 1000, "display": "none"},
						title="Next image",
						**{"aria-label": "Next image"},
					),
				], className="img-viewer-media"),
			], className="img-viewer-main"),
			dbc.ModalFooter([
				htm.Div(id=k.status, className="viewer-asset-status"),
				htm.Div([
					dbc.Button(
						"Select image",
						id=k.btnSelect,
						color="info",
						className="img-viewer-select",
						style={"display": "none"}
					),
				], className="img-viewer-primary-actions"),
			], className="img-viewer-footer"),
		],
			id=k.modal,
			size="xl",
			centered=False,
			className="img-pop",
		),

		dcc.Store(id=k.store),
	]


#------------------------------------------------------------------------
# trigger: single
#------------------------------------------------------------------------
@cbk(
	out(k.store, "data", allow_duplicate=True),
	inp({"type": "img-pop", "aid": ALL}, "n_clicks"),
	ste(k.store, "data"),
	prevent_initial_call=True
)
def mdlImg_OnImgPopClicked(clks, dta_mdl):
	if not clks or not any(clks): return noUpd

	if not ctx.triggered: return noUpd

	mdl = models.MdlImg.fromDic(dta_mdl)

	sets = dto.mdlImgSets or {}
	mdl.modeH = sets.get('auto', False)
	mdl.hideHelp = sets.get('help', False)
	mdl.hideInfo = sets.get('info', False)

	trigIdx = ctx.triggered_id
	if isinstance(trigIdx, dict) and "aid" in trigIdx:
		aid = trigIdx["aid"]
		lg.info(f"[mdlImg:single] clicked, aid[{aid}]")

		if aid:
			mdl.open = True
			mdl.isMulti = False
			mdl.imgUrl = f"/api/img/{aid}?q=preview"

	return mdl.toDict()


#------------------------------------------------------------------------
# trigger: multi
#------------------------------------------------------------------------
@cbk(
	out(k.store, "data", allow_duplicate=True),
	inp({"type": "img-pop-multi", "aid": ALL}, "n_clicks"),
	[
		ste(k.store, "data"),
		ste(ks.sto.now, "data"),
	],
	prevent_initial_call=True
)
def mdlImg_OnImgPopMultiClicked(clks, dta_mdl, dta_now):
	if not clks or not any(clks): return noUpd

	if not ctx.triggered: return noUpd

	now = models.Now.fromDic(dta_now)
	mdl = models.MdlImg.fromDic(dta_mdl)

	sets = dto.mdlImgSets or {}
	mdl.modeH = sets.get('auto', False)
	mdl.hideHelp = sets.get('help', True)
	mdl.hideInfo = sets.get('info', True)

	trigIdx = ctx.triggered_id

	if isinstance(trigIdx, dict) and "aid" in trigIdx:
		aid = trigIdx["aid"]
		lens = len(now.sim.assCur)
		lg.info(f"[mdlImg:multi] clicked, aid[{aid}] lens[{lens}] dta:{mdl}")

		if aid and now.sim.assCur:
			mdl.open = True
			mdl.isMulti = True
			mdl.imgUrl = f"/api/img/{aid}?q=preview"
			mdl.curIdx = next((i for i, ass in enumerate(now.sim.assCur) if ass.autoId == aid), 0)

	return mdl.toDict()


#------------------------------------------------------------------------
# Client-side callback for mdlImg content update
#------------------------------------------------------------------------
ccbk(
	cbkFn("mdlImg", "onUpdMdl"),

	[
		out(k.modal, "is_open"),
		out(k.content, "children"),
		out(k.status, "children"),
		out(k.btnPrev, "style"),
		out(k.btnNext, "style"),
		out(k.btnSelect, "style"),
		out(k.btnSelect, "children"),
		out(k.btnSelect, "color"),
		out(k.imgHelp, "className"),
		out(k.btnHelp, "children"),
		out(k.imgInfo, "className"),
		out(k.btnInfo, "children"),
		out(f"{k.imgInfo}-content", "children"),
		out(k.modal, "className", allow_duplicate=True),
		out(k.btnMode, "children", allow_duplicate=True),
	],
	inp(k.store, "data"),
	[
		ste(ks.sto.now, "data"),
		ste(ks.sto.ste, "data"),
	],
	prevent_initial_call=True
)

#------------------------------------------------------------------------
# Client-side callback for mdlImg navigation
#------------------------------------------------------------------------
ccbk(
	cbkFn("mdlImg", "onNavigation"),

	[
		out(k.store, "data", allow_duplicate=True),
		out(k.content, "children", allow_duplicate=True),
		out(k.status, "children", allow_duplicate=True),
		out(k.btnPrev, "style", allow_duplicate=True),
		out(k.btnNext, "style", allow_duplicate=True),
		out(k.btnSelect, "children", allow_duplicate=True),
		out(k.btnSelect, "color", allow_duplicate=True),
	],
	[
		inp(k.btnPrev, "n_clicks"),
		inp(k.btnNext, "n_clicks"),
	],
	[
		ste(ks.sto.now, "data"),
		ste(ks.sto.ste, "data"),
		ste(k.store, "data"),
	],
	prevent_initial_call=True
)

#------------------------------------------------------------------------
# Client-side callback for mdlImg help toggle
#------------------------------------------------------------------------
ccbk(
	cbkFn("mdlImg", "onHelpToggle"),

	[
		out(k.store, "data", allow_duplicate=True),
		out(k.imgHelp, "className", allow_duplicate=True),
		out(k.btnHelp, "children", allow_duplicate=True),
	],
	inp(k.btnHelp, "n_clicks"),
	ste(k.store, "data"),
	prevent_initial_call=True
)

#------------------------------------------------------------------------
# Client-side callback for mdlImg info toggle
#------------------------------------------------------------------------
ccbk(
	cbkFn("mdlImg", "onInfoToggle"),

	[
		out(k.store, "data", allow_duplicate=True),
		out(k.imgInfo, "className", allow_duplicate=True),
		out(k.btnInfo, "children", allow_duplicate=True),
	],
	inp(k.btnInfo, "n_clicks"),
	ste(k.store, "data"),
	prevent_initial_call=True
)

#------------------------------------------------------------------------
# Client-side callback for mdlImg mode toggle
#------------------------------------------------------------------------
ccbk(
	cbkFn("mdlImg", "onModeToggle"),

	[
		out(k.store, "data", allow_duplicate=True),
		out(k.modal, "className", allow_duplicate=True),
		out(k.btnMode, "children", allow_duplicate=True),
	],
	inp(k.btnMode, "n_clicks"),
	[ste(k.store, "data")],
	prevent_initial_call=True
)

#------------------------------------------------------------------------
# Client-side callback for mdlImg ste changes
#------------------------------------------------------------------------
ccbk(
	cbkFn("mdlImg", "onSteChanged"),

	[
		out(k.btnSelect, "children", allow_duplicate=True),
		out(k.btnSelect, "color", allow_duplicate=True),
	],
	inp(ks.sto.ste, "data"),
	[
		ste(ks.sto.now, "data"),
		ste(k.store, "data"),
	],
	prevent_initial_call=True
)

#------------------------------------------------------------------------
# Client-side callback for mdlImg selection
#------------------------------------------------------------------------
ccbk(
	cbkFn("mdlImg", "onBtnSelectToSte"),

	out(ks.sto.ste, "data", allow_duplicate=True),
	[inp(k.btnSelect, "n_clicks")],
	[ste(ks.sto.now, "data"), ste(k.store, "data")],
	prevent_initial_call=True
)

#------------------------------------------------------------------------
# Client-side callback to set current mdlImg autoId for hotkeys
#------------------------------------------------------------------------
ccbk(
	cbkFn("mdlImg", "onStoreToDummy"),

	out({"type": "dummy-output", "id": "mdlimg-current"}, "children"),
	[inp(k.store, "data"), inp(ks.sto.now, "data")],
	prevent_initial_call=True
)

#------------------------------------------------------------------------
# Server callback to persist mdlImg settings to db
#------------------------------------------------------------------------
@cbk(
	out({"type": "dummy", "id": "mdlimg-db"}, "children"),
	inp(k.store, "data"),
	prevent_initial_call=True
)
def mdlImg_SaveSets(dta_mdl):
	if not dta_mdl: return noUpd
	import db
	mdl = models.MdlImg.fromDic(dta_mdl)
	db.dto.mdlImgSets = {
		'auto': mdl.modeH,
		'help': mdl.hideHelp,
		'info': mdl.hideInfo,
	}
	return noUpd
