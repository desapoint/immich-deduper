from typing import List, Optional
from dsh import htm, dbc
from conf import ks
from util import log
from mod import models


lg = log.get(__name__)

from ui import gvEx, cards

STACK_GROUP_BUTTON = "sim-stack-group"
STACK_GROUP_DELETE = "sim-stack-group-delete"
STACK_COVER_BUTTON = "sim-stack-cover"
GROUP_ACTION_BUTTON = "sim-group-action"
GROUP_KEEP_SELECTED = "keep-selected"
GROUP_DELETE_SELECTED = "delete-selected"
GROUP_MARK_RESOLVED = "mark-resolved"
GROUP_DELETE_ALL = "delete-all"


def _mkGroupAction(
	label: str,
	groupId: int,
	action: str,
	color: str,
	disabled: bool = False,
	title: str = "",
	outline: bool = False,
):
	return dbc.Button(
		label,
		id={"type": GROUP_ACTION_BUTTON, "action": action, "id": groupId},
		size="sm",
		color=color,
		className="txt-sm sim-group-action",
		disabled=disabled,
		title=title,
		outline=outline,
	)


def _mkGroupHeader(groupId: int, count: int):
	return htm.Div([
		htm.Div([
			htm.Div([
				htm.Small("Similarity group", className="sim-group-eyebrow"),
				htm.Strong(f"#{groupId}"),
			], className="sim-group-name"),
			htm.Span(f"{count} images", className="sim-group-count"),
		], className="sim-group-title", **{"data-group-id": str(groupId)}),
		htm.Div([
			htm.Small("Select", className="sim-control-label"),
			dbc.Button("All", size="sm", color="secondary", id=f"cbx-sel-grp-all-{groupId}", className="txt-sm", title="Select every image in this group"),
			dbc.Button("None", size="sm", color="secondary", id=f"cbx-sel-grp-non-{groupId}", className="txt-sm", title="Clear this group's selection"),
			dbc.Button("Stacked", size="sm", color="secondary", id=f"sel-grp-stacked-{groupId}", className="txt-sm", title="Select only stacked images in this group"),
			dbc.Button("Not stacked", size="sm", color="secondary", id=f"sel-grp-unstacked-{groupId}", className="txt-sm", title="Select only non-stacked images in this group"),
		], className="sim-controls sim-group-selection"),
		htm.Div([
			htm.Small("Actions", className="sim-control-label"),
			_mkGroupAction("Keep selected", groupId, GROUP_KEEP_SELECTED, "success", disabled=True, title="Keep selected images and delete the other images in this group"),
			_mkGroupAction("Delete selected", groupId, GROUP_DELETE_SELECTED, "danger", disabled=True, title="Delete selected images and keep the other images in this group"),
			dbc.Checkbox(
				id={"type": STACK_GROUP_DELETE, "id": groupId},
				label="Delete rest",
				value=False,
				className="sim-stack-delete sm",
			),
			dbc.Button(
				"Stack selected",
				id={"type": STACK_GROUP_BUTTON, "id": groupId},
				size="sm",
				color="info",
				className="txt-sm",
				disabled=True,
				title="Stack selected images; reuse existing stacks and keep this group open",
			),
			_mkGroupAction("Mark resolved", groupId, GROUP_MARK_RESOLVED, "primary", title="Finish this group without deleting its remaining images"),
			_mkGroupAction("Delete group", groupId, GROUP_DELETE_ALL, "danger", title="Delete every remaining image in this group"),
		], className="sim-controls sim-group-actions"),
	], className="hr sim-group-header", **{"data-group-id": str(groupId)})


def mkCardRow(asset: models.Asset, groupId: int, style: Optional[dict] = None):
	return htm.Div(cards.mk(asset, stackGroupId=groupId), style=style or {})


def mkGroupRows(groupId: int, assets: List[models.Asset], style: Optional[dict] = None):
	return [
		_mkGroupHeader(groupId, len(assets)),
		*[mkCardRow(asset, groupId, style) for asset in assets],
	]


def mkGrd(assets: list[models.Asset], minW=230, onEmpty=None, maker=cards.mk):
	if not assets or len(assets) == 0:
		if onEmpty:
			if isinstance(onEmpty, str): return dbc.Alert(f"{onEmpty}", color="warning", className="text-center")
			else: return onEmpty
		return htm.Div(dbc.Alert("--------", color="warning"), className="text-center")

	cntAss = len(assets)

	if cntAss <= 4:
		styGrid = {
			"display": "flex",
			"flexWrap": "wrap",
			"gap": "1rem",
			"justifyContent": "center"
		}
		styItem = {"flex": f"1 1 {minW}px"}
	else:
		styGrid = {
			"display": "grid",
			"gridTemplateColumns": f"repeat(auto-fit, minmax({minW}px, 1fr))",
			"gap": "1rem"
		}
		styItem = {}

	rows = []
	firstRels = False
	cntRelats = sum(1 for a in assets if a.vw.isRelats)
	isSimGrid = maker is cards.mk

	gid = assets[0].vw.muodId if assets[0].vw.muodId is not None else assets[0].autoId
	if isSimGrid: rows.append(_mkGroupHeader(gid, len(assets)))

	for idx, a in enumerate(assets):
		card = cards.mk(a, stackGroupId=gid) if isSimGrid else maker(a)

		if a.vw.isRelats and not firstRels:
			firstRels = True
			rows.append(htm.Div(htm.Label(f"relates ({cntRelats}) :"), className="hr"))

		rows.append(htm.Div(card, style=styItem))

	lg.info(f"[sim:gv] assets[{len(assets)}] rows[{len(rows)}]")

	return htm.Div(rows, className="gv fsp", style=styGrid)


def mkGrdGrps(assets: List[models.Asset], minW=250, maxW=300, onEmpty=None):
	if not assets or len(assets) == 0:
		if onEmpty:
			if isinstance(onEmpty, str): return dbc.Alert(f"{onEmpty}", color="warning", className="text-center")
			else: return onEmpty
		return htm.Div(dbc.Alert("--------", color="warning"), className="text-center")

	cntAss = len(assets)

	if cntAss <= 4:
		styGrid = {
			"display": "flex",
			"flexWrap": "wrap",
			"gap": "1rem",
			"justifyContent": "center"
		}
		styItem = {"flex": f"1 1 {minW}px"}
	else:
		styGrid = {
			"display": "grid",
			"gridTemplateColumns": f"repeat(auto-fit, minmax({minW}px, 1fr))",
			"gap": "1rem"
		}
		styItem = {}

	groups = {}
	for asset in assets:
		grpId = asset.vw.muodId or 0
		if grpId not in groups: groups[grpId] = []
		groups[grpId].append(asset)

	rows = []
	for grpId in sorted(groups.keys()):
		grpAssets = groups[grpId]
		rows.extend(mkGroupRows(grpId, grpAssets, styItem))

	lg.info(f"[fsp:gv] assets[{len(assets)}] groups[{len(groups)}] rows[{len(rows)}]")

	return htm.Div(rows, className="gv fsp", style=styGrid)



def mkPndGrd(assets: list[models.Asset], minW=230, maxW=300, onEmpty=None):
	if not assets or len(assets) == 0:
		if onEmpty:
			if isinstance(onEmpty, str): return dbc.Alert(f"{onEmpty}", color="warning", className="text-center")
			else: return onEmpty
		return htm.Div(dbc.Alert("--------", color="warning"), className="text-center")

	cntAss = len(assets)

	if cntAss <= 4:
		styGrid = {
			"display": "flex",
			"flexWrap": "wrap",
			"gap": "1rem",
			"justifyContent": "start"
		}
		styItem = {"flex": f"1 1 {minW}px", "maxWidth": f"{maxW}px"}
	else:
		styGrid = {
			"display": "grid",
			"gridTemplateColumns": f"repeat(auto-fit, minmax({minW}px, 1fr))",
			"gap": "1rem"
		}
		styItem = {}

	rows = [htm.Div(cards.mkCardPnd(a), style=styItem) for a in assets]

	lg.info(f"[sim:gvPnd] assets[{len(assets)}] rows[{len(rows)}]")

	return htm.Div(rows, style=styGrid)
