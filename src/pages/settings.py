from conf import ks, envs
from dsh import dash, htm, dbc, dcc
from util import log

import rtm
from ui import cardSets

lg = log.get(__name__)

dash.register_page(
	__name__,
	path=f'/',
	title=f"{ks.title}: " + 'System Settings',
)


#========================================================================
def layout():
	import ui

	def statusItem(label, value, statusClass, iconClass):
		return htm.Div([
			htm.Div([
				htm.I(className=f"bi {iconClass}"),
				htm.Small(label),
			], className="settings-status-label"),
			htm.Div(value, className="settings-status-value"),
		], className=f"settings-status-item {statusClass}")

	return ui.renderBody([
		#====== top start =======================================================

		htm.Div([
			htm.H3(f"{ks.pg.setting.name}"),
			htm.Small(f"{ks.pg.setting.desc}", className="text-muted")
		], className="body-header"),

		htm.Div([
			htm.Div(htm.I(className="bi bi-shield-check"), className="settings-intro-icon"),
			htm.Div([
				htm.Small("System readiness", className="settings-eyebrow"),
				htm.H4("Configure once, then work with confidence"),
				htm.P("Connections and local services are checked automatically. Review the status below before fetching or processing assets."),
		]),
		], className="settings-intro"),

		htm.Div([
			htm.Div([
				dbc.Card([
					dbc.CardHeader([
						htm.Span("System configuration"),
						htm.Small("Live environment checks", className="text-muted"),
					]),
					dbc.CardBody([
						htm.Div([
							statusItem("Deduper data", envs.ddupData or "Not configured", "chk-data", "bi-database"),
							statusItem("Immich logic", "Repository integration", "chk-logic", "bi-github"),
							statusItem("Qdrant", envs.qdrantUrl or "Not configured", "chk-vec", "bi-boxes"),
							statusItem("PostgreSQL", f"{envs.psqlHost}:{envs.psqlPort}", "chk-psql", "bi-server"),
							statusItem("Immich path", rtm.immichPath or "Not configured", "chk-path", "bi-folder2-open"),
							statusItem("ResNet152", "Feature extraction", "chk-model", "bi-cpu"),
							statusItem("ExifTool", "Metadata editor", "chk-exiftool", "bi-card-list"),
						], className="card-system-cfgs settings-status-grid")
					])
				], className="settings-system-card")
			], className="settings-overview"),


			htm.Div([

				cardSets.renderThreshold(),

				cardSets.renderCard(),


			], className="settings-controls")

		], className="settings-layout"),
		#====== top end =========================================================
	], [
		#====== bottom start=====================================================

		#====== bottom end ======================================================
	], pageClass="page-settings")
