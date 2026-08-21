from typing import List
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
GROUP_KEEP_ALL = "keep-all"
GROUP_DELETE_ALL = "delete-all"


def _mkGroupAction(label: str, groupId: int, action: str, color: str, disabled: bool = False):
	return dbc.Button(
		label,
		id={"type": GROUP_ACTION_BUTTON, "action": action, "id": groupId},
		size="sm",
		color=color,
		className="txt-sm ms-1",
		disabled=disabled,
	)


def _mkGroupHeader(groupId: int, count: int):
	return htm.Div([
		htm.Label(f"Group {groupId} ( {count} items )"),
		dbc.Button([htm.Span(className="fake-checkbox checked"), "select this group all"], size="sm", color="secondary", id=f"cbx-sel-grp-all-{groupId}", className="txt-sm me-1"),
		dbc.Button([htm.Span(className="fake-checkbox"), "deselect this group All"], size="sm", color="secondary", id=f"cbx-sel-grp-non-{groupId}", className="txt-sm"),
		_mkGroupAction("Keep selected, delete others", groupId, GROUP_KEEP_SELECTED, "success", disabled=True),
		_mkGroupAction("Delete selected, keep others", groupId, GROUP_DELETE_SELECTED, "danger", disabled=True),
		dbc.Checkbox(
			id={"type": STACK_GROUP_DELETE, "id": groupId},
			label="Delete unselected",
			value=False,
			className="d-inline-block ms-3 sm",
		),
		dbc.Button(
			"Stack selected",
			id={"type": STACK_GROUP_BUTTON, "id": groupId},
			size="sm",
			color="info",
			className="txt-sm ms-1",
			disabled=True,
			title="Stack selected assets in this group; existing stacks are reused, otherwise the first displayed selection becomes the cover",
		),
		_mkGroupAction("Keep all", groupId, GROUP_KEEP_ALL, "success"),
		_mkGroupAction("Delete all", groupId, GROUP_DELETE_ALL, "danger"),
	], className="hr", **{"data-group-id": str(groupId)})


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

	gid = assets[0].vw.muodId if assets[0].vw.muodId is not None else assets[0].autoId
	rows.append(_mkGroupHeader(gid, len(assets)))

	for idx, a in enumerate(assets):
		card = cards.mk(a, stackGroupId=gid) if maker is cards.mk else maker(a)

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
		grpCount = len(grpAssets)


		rows.append(_mkGroupHeader(grpId, grpCount))

		for asset in grpAssets:
			card = cards.mk(asset, stackGroupId=grpId)
			rows.append(htm.Div(card, style=styItem))

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
