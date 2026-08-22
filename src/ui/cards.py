from os import wait, path
import hashlib
from typing import List

from dash_bootstrap_components import ListGroup
from dsh import htm, dbc, dcc
from conf import ks, co
from util import log
from mod import models
import db

from ui import gvEx

lg = log.get(__name__)

def mk(ass: models.Asset, modSim=True, stackGroupId=None):

	imgSrc = f"/api/img/{ass.autoId}" if ass.id else None

	checked = False
	cssIds = "checked" if checked else ""

	exi = ass.jsonExif
	ex = ass.ex
	stackId = ex.stackId if ex else None
	stackPrimaryId = ex.stackPrimaryAssetId if ex else None
	isStackPrimary = bool(stackId and stackPrimaryId == ass.id)
	stackHue = int(hashlib.sha1(stackId.encode()).hexdigest()[:8], 16) % 360 if stackId else 0
	stackColor = f"hsl({stackHue}, 70%, 45%)" if stackId else None
	stackLabel = f"Stack {stackId[:8]}" if stackId else None
	stackCardStyle = {"--sim-stack-color": stackColor} if stackColor else None
	ownerName = db.psql.getUsrName(ass.ownerId)

	imgW = exi.exifImageWidth
	imgH = exi.exifImageHeight

	isMain = ass.vw.isMain
	isRels = ass.vw.isRelats
	isLive = ass.vdoId is not None
	canFnd = ass.simOk == 0
	hasVec = ass.isVectored == 1

	css = f"h-100 sim {cssIds} {'sim-card-five-zone' if modSim else 'view'}"
	if isMain: css += " main"
	if isRels: css += " rels"
	if stackId: css += " has-stack"

	tipExif = gvEx.mkTipExif(ass.autoId, ass.jsonExif)

	imgPopId = {"type": "img-pop-multi", "aid": ass.autoId} if modSim else {"type": "img-pop", "aid": ass.autoId}

	mediaStage = htm.Div([
		htm.Div([
			htm.Video(
				src=f"/api/livephoto/{ass.autoId}", loop=True, muted=True, preload="metadata",
				id=imgPopId,
				className="livephoto",
			) if isLive else None,
			htm.Img(
				src=imgSrc,
				id=imgPopId,
				className="card-img"
			),
		], className='view sim-card-media-frame' if modSim else 'view'),

		*([
			htm.Div(
				htm.Span([htm.I(className='bi bi-camera-video-fill'), "Live Photo"], className="tag blue livePhoto"),
				className="sim-card-media-badges",
			) if isLive else None,
			htm.Div([
				htm.Span(f"{co.fmt.size(ass.jsonExif.fileSizeInByte)}", className="tag") if ass.jsonExif and ass.jsonExif.fileSizeInByte else None,
				htm.Span(f"{imgW} × {imgH}", className="tag lg") if imgW and imgH else None,
			], className="sim-card-media-facts"),
		] if modSim else [
			htm.Div([
				htm.Span(f"#{ass.autoId}", className="tag"),
				htm.Span(f"SimOK!", className="tag info") if ass.simOk else None,
			], className="LT"),
			htm.Div([
				htm.Span(f"LivePhoto", className="tag blue livePhoto") if isLive else None,
				htm.Span([htm.I(className='bi bi-images'), f'{len(ex.albs)}'], className='tag', **{'data-tip-id': f'albs-{ass.autoId}'}) if ex else None, #type: ignore
				htm.Span([htm.I(className='bi bi-bookmark-check-fill'), f'{len(ex.tags)}'], className='tag', **{'data-tip-id': f'tags-{ass.autoId}'}) if ex else None, #type: ignore
				htm.Span([htm.I(className='bi bi-person-bounding-box'), f'{len(ex.facs)}'], className='tag', **{'data-tip-id': f'facs-{ass.autoId}'}) if ex else None, #type: ignore
			], className="RT"),
			htm.Div([
				htm.Span([htm.I(className='bi bi-person-circle'), ownerName], className='tag'),
			], className="LB"),
			htm.Div([
				htm.Span(f"{co.fmt.size(ass.jsonExif.fileSizeInByte)}", className="tag") if ass.jsonExif else None,
				htm.Span(f"{imgW} x {imgH}", className="tag lg"),
			], className="RB"),
		]),
	], className="viewer sim-card-media" if modSim else "viewer")

	captureDate = exi.dateTimeOriginal or ass.localDateTime or ass.fileCreatedAt
	captureLabel = str(captureDate).replace("T", " ")[:16] if captureDate else "Date unavailable"
	fileName = ass.originalFileName or path.basename(ass.originalPath) or f"Asset #{ass.autoId}"
	pathFileName = path.basename(ass.originalPath) if ass.originalPath else None

	metadataItems = []
	if ass.isFavorite:
		metadataItems.append(htm.Span([htm.I(className="bi bi-heart-fill"), "Favorite"], className="tag sim-card-meta-item is-favorite", title="Marked as favorite"))
	if ex and ex.rating and ex.rating > 0:
		metadataItems.append(htm.Span([htm.I(className="bi bi-star-fill"), f"{ex.rating}"], className="tag sim-card-meta-item", title=f"Rating {ex.rating}"))
	if ex and ex.albs:
		metadataItems.append(htm.Span([htm.I(className="bi bi-images"), f"{len(ex.albs)}"], className="tag sim-card-meta-item", title=f"{len(ex.albs)} album(s)", **{"data-tip-id": f"albs-{ass.autoId}"})) # type: ignore
	if ex and ex.tags:
		metadataItems.append(htm.Span([htm.I(className="bi bi-tags-fill"), f"{len(ex.tags)}"], className="tag sim-card-meta-item", title=f"{len(ex.tags)} tag(s)", **{"data-tip-id": f"tags-{ass.autoId}"})) # type: ignore
	if ex and ex.facs:
		metadataItems.append(htm.Span([htm.I(className="bi bi-people-fill"), f"{len(ex.facs)}"], className="tag sim-card-meta-item", title=f"{len(ex.facs)} recognized person(s)", **{"data-tip-id": f"facs-{ass.autoId}"})) # type: ignore
	if ass.libId:
		metadataItems.append(htm.Span([htm.I(className="bi bi-hdd-network-fill"), "External"], className="tag sim-card-meta-item", title="External-library asset"))
	if ex and ex.stackAssets:
		metadataItems.append(htm.Span([htm.Span(className="ico stack"), f"{len(ex.stackAssets)}"], className="tag sim-card-meta-item", title=f"{len(ex.stackAssets)} image(s) in this stack", **{"data-tip-id": f"stack-{ass.autoId}"})) # type: ignore
	if ass.simOk:
		metadataItems.append(htm.Span([htm.I(className="bi bi-check-circle-fill"), "Resolved"], className="tag sim-card-meta-item", title="Similarity record is resolved"))

	detailRows = [
		("Immich ID", ass.id),
		("Original filename", ass.originalFileName),
		("Full path", ass.originalPath),
		("Stored filename", pathFileName if pathFileName and pathFileName != ass.originalFileName else None),
		("Device ID", ass.deviceId),
		("Asset type", ass.type),
		("Captured", captureDate),
		("Created", ass.fileCreatedAt),
		("Modified", ass.fileModifiedAt),
		("Library ID", ass.libId),
		("Stack ID", stackId),
		("Stack thumbnail ID", stackPrimaryId),
		("Live Photo video ID", ass.vdoId),
		("Live Photo path", ass.pathVdo),
	]
	detailLinks = [
		htm.Span("EXIF", className="tag sim-card-detail-link", **{"data-tip-id": f"exif-{ass.autoId}"}) if exi and exi.toAvDict() else None, # type: ignore
		htm.Span("Description", className="tag sim-card-detail-link", **{"data-tip-id": f"desc-{ass.autoId}"}) if ex and ex.description else None, # type: ignore
		htm.Span("Location", className="tag sim-card-detail-link", **{"data-tip-id": f"loc-{ass.autoId}"}) if ex and ex.latitude is not None and ex.longitude is not None else None, # type: ignore
	]

	similarCardBody = dbc.CardBody([
		htm.Div([
			htm.Span(
				fileName,
				className="tag sim-card-filename",
				title=f"{fileName} — select to copy",
				tabIndex=0,
				role="button",
				**{"aria-label": f"Copy filename {fileName}"},
			),
			htm.Div([
				htm.Span([htm.I(className="bi bi-calendar3"), captureLabel], className="sim-card-identity-item", title=str(captureDate) if captureDate else None),
				htm.Span([htm.I(className="bi bi-person-circle"), ownerName or "Unknown owner"], className="sim-card-identity-item", title=ass.ownerId or None),
			], className="sim-card-identity-secondary"),
		], className="sim-card-identity"),
		htm.Div(metadataItems, className="sim-card-metadata", **{"aria-label": "Asset metadata summary"}),
		htm.Details([
			htm.Summary([
				htm.Span("Details"),
				htm.I(className="bi bi-chevron-down", **{"aria-hidden": "true"}),
			], className="sim-card-details-summary"),
			htm.Div([
				*[
					htm.Div([
						htm.Span(label, className="sim-card-detail-label"),
						htm.Span(str(value), className="sim-card-detail-value", title=str(value)),
					], className="sim-card-detail-row")
					for label, value in detailRows if value not in (None, "")
				],
				htm.Div(detailLinks, className="sim-card-detail-links") if any(detailLinks) else None,
			], className="sim-card-detail-grid"),
		], className="sim-card-details", open=bool(db.dto.showGridInfo)),
	], className="p-0 sim-card-content")

	return htm.Div([
		#------------------------------------------------------------------------
		# hidden meta data for export
		#------------------------------------------------------------------------
		htm.Div(
			className="card-meta",
			style={"display": "none"},
			**{"data-meta": f'{{"id":"{ass.id}","autoId":{ass.autoId},"originalFileName":"{ass.originalFileName}","originalPath":"{ass.originalPath}"}}'}  # type: ignore[arg-type]
		),
		#------------------------------------------------------------------------
		# dynamic
		#------------------------------------------------------------------------
		htm.Div([
			htm.Div([
				htm.Div([
					htm.Li(alb.albumName, className="tag album") for alb in (ex.albs if ex and ex.albs else [])
				])
			], className="poptip", id=f'albs-{ass.autoId}') if ex and ex.albs else None,

			htm.Div([
				htm.Div([
					htm.Li(tag.value, className="tag") for tag in (ex.tags if ex and ex.tags else [])
				])
			], className="poptip", id=f'tags-{ass.autoId}') if ex and ex.tags else None,
			htm.Div([
				htm.Div([
					htm.Li(fac.name, className="tag") for fac in (ex.facs if ex and ex.facs else [])
				])
			], className="poptip", id=f'facs-{ass.autoId}') if ex and ex.facs else None,

			htm.Div([
				htm.P(ex.description, className="desc-content")
			], className="poptip", id=f'desc-{ass.autoId}') if ex and ex.description else None,

			htm.Div([
				htm.Div([
					htm.Span(f"{ex.city}, ") if ex.city else None,
					htm.Span(f"{ex.state}, ") if ex.state else None,
					htm.Span(f"{ex.country}") if ex.country else None,
					htm.Br(),
					htm.Span(f"{ex.latitude:.6f}, {ex.longitude:.6f}"),
				], className="loc-content")
			], className="poptip", id=f'loc-{ass.autoId}') if ex and ex.latitude is not None and ex.longitude is not None else None,

			htm.Div([
				htm.Div([
					htm.Img(
						src=f"/api/img/id/{mid}",
						style={"width": "64px", "height": "64px", "objectFit": "cover", "borderRadius": "4px"}
					) for mid in ex.stackAssets
				], style={"display": "flex", "flexWrap": "wrap", "gap": "4px", "maxWidth": "280px"})
			], className="poptip", id=f'stack-{ass.autoId}') if ex and ex.stackAssets else None,

			tipExif,

		]),
		#------------------------------------------------------------------------
		dbc.Card([
			dbc.CardHeader([
				htm.Div([
					htm.Div(
						dbc.Checkbox(label=f"#{ass.autoId}", value=False),
						className="sim-card-selection",
					),
					htm.Div(
						[
							htm.Span("Source", className="sim-source-label", title="Source image used to find this similarity group")
						] if isMain else [
							htm.Span("score:", className="tag sm info no-border"),
							htm.Span(f"{ass.vw.score:.5f}", className="tag lg ms-1")
						] if isRels else [
							htm.Span("score:", className="tag sm second no-border"),
							htm.Span(f"{ass.vw.score:.5f}", className="tag lg ms-1")
						],
						className="sim-card-score",
					),
				], id={"type": "card-select", "id": ass.autoId}, className="curP sim-card-select sim-card-header-primary", **{
					"data-stacked": "true" if stackId else "false",
					"data-stack-id": stackId or "",
					"data-group-id": str(stackGroupId) if stackGroupId is not None else "",
				}),
				htm.Div([
					htm.Div([
						htm.Span(stackLabel, className="badge sim-stack-badge", style={"backgroundColor": stackColor}, title=f"Immich stack {stackId}"),
						htm.Span("Thumbnail", className="badge bg-warning text-dark sim-stack-thumbnail", title="Current Immich stack thumbnail") if isStackPrimary else None,
					] if stackId else [], className="sim-stack-status"),
					dbc.Button(
						"Set cover",
						id={"type": "sim-stack-cover", "id": ass.autoId, "group": stackGroupId, "owner": ass.ownerId},
						n_clicks=0,
						size="sm",
						color="info",
						outline=True,
						className="sim-stack-cover-btn text-nowrap",
						title="Use this image as the stack cover; it will also be selected",
					),
				], className="sim-card-header-secondary"),
			],
				className="p-2 sim-card-header sim-card-decision"
			) if modSim else None,

			#------------------------------------------------------------------------
			mediaStage,
			similarCardBody if modSim else dbc.CardBody([
				dbc.Row([
					htm.Span("immich id"),htm.Span(f"{ass.id}",className="tag"),
					*([htm.Span("device"),htm.Span(f"{ass.deviceId}",className="tag second")] if ass.deviceId else []),
					htm.Span("Path"),htm.Span(f"{path.dirname(ass.originalPath)}",className="tag second multiline"),
					htm.Span("File"), htm.Span([
						htm.Span(f"{ass.originalFileName}", className="tag second multiline"),
						htm.Span(f"{path.basename(ass.originalPath)}", className="tag yellow multiline ms-1") if ass.originalPath and path.basename(ass.originalPath) != ass.originalFileName else None,
					]),
					htm.Span("CreateAt"), htm.Span(f"{ass.fileCreatedAt}", className="tag second"),
					htm.Span("ModifiedAt"), htm.Span(f"{ass.fileModifiedAt}", className="tag second"),

					*([htm.Span("livePhoto"), htm.Span(f"{ass.pathVdo}", className="tag blue"),] if isLive else []),
					*([htm.Span("live VdoId"), htm.Span(f"{ass.vdoId}", className="tag blue"),] if isLive else []),

				], class_name="grid grid-info"),
				htm.Div([

					htm.Span('Resolved', className='tag') if ass.simOk else None,
					htm.Span('Favorite', className='tag') if ass.isFavorite else None,
					htm.Span(f'Rating {ex.rating}', className='tag yellow') if ex and ex.rating and ex.rating > 0 else None,
					htm.Span(ex.visibility, className='tag info') if ex and ex.visibility and ex.visibility != 'timeline' else None,

					htm.Span("exif", className='tag blue', **{'data-tip-id': f'exif-{ass.autoId}'}) if ass.jsonExif else None, #type: ignore
					htm.Span("external", className='tag yellow') if ass.libId else None,

					htm.Span('desc', className='tag second', **{'data-tip-id': f'desc-{ass.autoId}'}) if ex and ex.description else None, #type: ignore

					htm.Span('location', className='tag green', **{'data-tip-id': f'loc-{ass.autoId}'}) if ex and ex.latitude is not None and ex.longitude is not None else None, #type: ignore

					htm.Span([
						htm.Span(className='ico stack'),
						f'{len(ex.stackAssets)}',
					], className='tag second', **{'data-tip-id': f'stack-{ass.autoId}'}) if ex and ex.stackAssets else None, #type: ignore

					# htm.Span([
					#     htm.I(className='bi bi-person-bounding-box'),
					#     f'{len(ex.tags)}'
					# ], className='tag') if ex else None,

					# htm.Span([
					# 	'GIDs: ',
					# 	*[htm.Span(i) for i in ass.simGIDs],
					# ], className='tag info') if ass.simGIDs else None,

				], className=f'tagbox'),

				# dbc.Row([
				#     htm.Table( htm.Tbody(gvEx.mkExifRows(ass)) , className="exif"),
				# ]) if db.dto.showGridInfo else None,

				htm.Div([

					dcc.Link(
						f"Find Similar #{ass.autoId}",
						href=f"/{ks.pg.similar}/{ass.autoId}",
						className="btn btn-primary btn-sm w-76 me-2"
					) if canFnd and hasVec else htm.Button(
						f"No Vector #{ass.autoId}",
						className="btn btn-secondary btn-sm w-76 me-2",
						disabled=True,
						title="This asset has no vector, please generate vectors first",
						style={"border": "1px solid #6c757d", "opacity": "0.7"}
					) if canFnd and not hasVec else None,

					htm.Button(
						htm.I(className='bi bi-trash'),
						id={'type': 'asset-del', 'aid':ass.autoId}, n_clicks=0,
						className="btn btn-danger btn-sm w-20"
					),

				], className='m-2 txt-r') if not modSim else None,


			], className="p-0"),
		], className=css, style=stackCardStyle)
	])



def mkCardPnd(ass: models.Asset, showRelated=True):
	imgSrc = f"/api/img/{ass.autoId}" if ass.autoId else "assets/noimg.png"

	if not ass.id: return htm.Div("-No ass.id-")

	assId = ass.id

	checked = False
	cssIds = "checked" if checked else ""

	exi = ass.jsonExif

	imgW = exi.exifImageWidth if exi else 0
	imgH = exi.exifImageHeight if exi else 0

	htmSimInfos = []

	htmRelated = None
	if ass.vw.cntRelats and showRelated:
		rids = []

		htmRelated = [
			htm.Hr(className="my-2"),
			htm.Div([
				htm.Span("Related groups: ", className="text-muted"),
				htm.Span(f"{ass.vw.cntRelats}", className="badge bg-warning")
			]),
			htm.Div(rids)
		]

	return dbc.Card([
		htm.Div([
			dbc.Row([
				dbc.Col(
					dbc.Button(
						"ViewGroup",
						id={"type": "btn-view-group", "id": assId},
						color="info",
						size="sm",
						className=""
					)
				),
				dbc.Col([
					htm.Span("Matches: ", className="txt-sm"), htm.Span(f"{len(ass.simInfos) - 1}", className="tag lg ms-1 ps-2 pe-2")
				], className="justify-content-end")
			]
				, className="p-0")

		], className="pt-2 ps-2 pb-3"),
		htm.Div([
			htm.Img(
				src=imgSrc,
				id={"type": "img-pop", "aid": ass.autoId}, n_clicks=0,
				className="card-img"
			),
			htm.Div([
				htm.Span(f"#{ass.autoId}", className="tag sm second"),
			], className="LB"),
			htm.Div([
				htm.Span(f"{imgW}", className="tag lg"),
				htm.Span("x"),
				htm.Span(f"{imgH}", className="tag lg"),
			], className="RB")
		], className="img"),
		dbc.CardBody([
			dbc.Row([
				htm.Span("id"), htm.Span(f"{ass.id}", className="badge bg-success text-truncate"),

			], class_name="grid"),

			dbc.Row([
				htm.Span("fileName"), htm.Span(f"{ass.originalFileName}", className="text-truncate"),
				htm.Span("createAt"), htm.Span(f"{ass.fileCreatedAt}", className="text-truncate txt-sm"),

			], class_name="grid2"),


			htm.Div(htmSimInfos),
			htm.Div(htmRelated),

		], className="p-2")
	], className=f"h-100 sim {cssIds}")
