from dsh import dash, htm, dcc
from conf import ks

dash.register_page(
	__name__,
	path=f'/404',
	title=f" 404 NotFound " + ks.title,
)

def layout():
	import ui

	return ui.renderBody([
		htm.Div([
			htm.Div([
				htm.I(className="bi bi-signpost-split"),
			], className="not-found-icon"),
			htm.Small("404 · Page not found", className="not-found-eyebrow"),
			htm.H1("This route does not lead anywhere"),
			htm.P("The link may be outdated or mistyped. Your library and Deduper data are unchanged."),
			htm.Div([
				dcc.Link([
					htm.I(className="bi bi-house-door"),
					"Return to settings",
				], href="/", className="btn btn-primary"),
				dcc.Link([
					htm.I(className="bi bi-grid-3x3-gap"),
					"Open asset library",
				], href=f"/{ks.pg.view}", className="btn btn-outline-info"),
			], className="not-found-actions"),
			htm.Div([
				htm.Span("You can also continue with"),
				dcc.Link("Fetch", href=f"/{ks.pg.fetch}"),
				htm.Span("or"),
				dcc.Link("Similar", href=f"/{ks.pg.similar}"),
			], className="not-found-links"),
		], className="not-found-state"),
	], [], pageClass="page-not-found")
