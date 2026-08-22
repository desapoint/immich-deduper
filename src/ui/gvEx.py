from typing import Optional
import dash.html as htm
from util import log
from conf import ks, co
from mod import models

lg = log.get(__name__)

def mkCardTip(tipId: str, title: str, content, contentClass: str = ""):
	contentCss = "sim-card-poptip-content"
	if contentClass: contentCss += f" {contentClass}"

	return htm.Div([
		htm.Div([
			htm.Div(title, className="sim-card-poptip-title"),
			htm.Div(content, className=contentCss),
		], className="sim-card-poptip-surface"),
	], className="poptip sim-card-poptip", id=tipId, role="dialog", **{"aria-label": title})

def mkExifRows(asset:models.Asset):
	rows = []

	if asset.jsonExif:
		rows = mkExifGrid(asset.jsonExif.toDict())
		pass

	return rows

def mkExifGrid(dicExif:dict):
	table = []

	for key in ks.defs.exif.keys():
		if key in dicExif and dicExif[key] is not None:
			display_key = ks.defs.exif.get(key, key)

			value = dicExif[key]
			if key == "fileSizeInByte": display_value = co.fmt.size(value)
			elif key == "focalLength" and isinstance(value, (int, float)): display_value = f"{value} mm"
			elif key == "fNumber" and isinstance(value, (int, float)): display_value = f"f/{value}"
			else:
				if not value: continue
				display_value = co.fmt.date(value)

			table.append(
				htm.Tr([
					htm.Td(display_key),
					htm.Td(display_value),
				])
			)

	# for key, value in dicExif.items():
	#     if key not in ks.defs.exif and value is not None:
	#         table.append(
	#             htm.Tr([
	#                 htm.Td(key),
	#                 htm.Td(str(value)),
	#             ])
	#         )

	return table


def mkTipExif(autoId, dicExif: Optional[models.AssetExif]):
	if not dicExif: return None

	table = mkExifGrid(dicExif.toDict())

	if len(table) > 0:
		return mkCardTip(
			f'exif-{autoId}',
			"EXIF details",
			htm.Table(htm.Tbody(table), className="sim-card-poptip-table"),
			"sim-card-poptip-content-scroll",
		)

	return None
