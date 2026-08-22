from dsh import htm, dcc, dbc

from conf import ks
from mod import models
from db import dto

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


def _initialState():
	sets = dto.mdlImgSets or {}
	mdl = models.MdlImg()
	mdl.modeH = sets.get('auto', False)
	mdl.hideHelp = sets.get('help', True)
	mdl.hideInfo = sets.get('info', True)
	return mdl.toDict()



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
], id=k.imgHelp, className="help hide")

layoutInfo = htm.Div([
	htm.H6("Image details", className="mb-2"),
	htm.Div(id=f"{k.imgInfo}-content", className="info-content"),
], id=k.imgInfo, className="info hide")


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
					htm.Div([
						htm.Button(
							htm.I(className="bi bi-chevron-left"),
							id=k.btnPrev,
							className="btn btn-secondary img-viewer-nav img-viewer-nav-prev",
							style={"zIndex": 1000, "display": "none"},
							title="Previous image",
							**{"aria-label": "Previous image"},
						),
					], className="img-viewer-nav-zone img-viewer-nav-zone-prev"),
					htm.Div(
						htm.Div(id=k.content, className="img img-viewer-stage"),
						className="img-viewer-media",
					),
					htm.Div([
						htm.Button(
							htm.I(className="bi bi-chevron-right"),
							id=k.btnNext,
							className="btn btn-secondary img-viewer-nav img-viewer-nav-next",
							style={"zIndex": 1000, "display": "none"},
							title="Next image",
							**{"aria-label": "Next image"},
						),
					], className="img-viewer-nav-zone img-viewer-nav-zone-next"),
				], className="img-viewer-content"),
				htm.Div([
					dbc.Button(
						"Select image",
						id=k.btnSelect,
						color="info",
						className="img-viewer-select",
						style={"display": "none"}
					),
				], className="img-viewer-primary-actions img-viewer-select-slot"),
			], className="img-viewer-main"),
			dbc.ModalFooter([
				htm.Div(id=k.status, className="viewer-asset-status"),
			], className="img-viewer-footer"),
		],
			id=k.modal,
			size="xl",
			centered=False,
			className="img-pop",
		),

		dcc.Store(id=k.store, data=_initialState()),
	]
