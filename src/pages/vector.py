import db
from conf import ks
import conf
from dsh import dash, htm, cbk, dbc, inp, out, ste, getTrgId, noUpd
from util import log
from mod import models, mapFns, tskSvc
from ui import cardSets

lg = log.get(__name__)

dash.register_page(
	__name__,
	path=f'/{ks.pg.vector}',
	title=f"{ks.title}: " + ks.pg.vector.name,
)

class K:
	btnDoVec="vector-btnDoVec"
	btnClear="vector-btnClear"
	btnRepairIdx="vector-btnRepairIdx"


#========================================================================
def layout():
	import ui

	def pipelineStep(number, phase, title, text, icon):
		return htm.Div([
			htm.Div(str(number), className="vector-step-number"),
			htm.Div([
				htm.Div([
					htm.Small(phase),
					htm.I(className=f"bi {icon}"),
				], className="vector-step-meta"),
				htm.Strong(title),
				htm.P(text),
			]),
		], className="vector-step")

	return ui.renderBody([
		#====== top start =======================================================

		htm.Div([
			htm.H3(f"{ks.pg.vector.name}"),
			htm.Small(f"{ks.pg.vector.desc}", className="text-muted")
		], className="body-header"),

		htm.Div([
			htm.Div(htm.I(className="bi bi-stars"), className="vector-intro-icon"),
			htm.Div([
				htm.Small("Similarity engine", className="vector-eyebrow"),
				htm.H4("Prepare assets for fast, reliable duplicate search"),
				htm.P("The pipeline reconciles existing data, generates missing embeddings, and verifies the index before it finishes."),
		]),
			htm.Span(f"{conf.device.type.upper()} runtime", className="vector-runtime-badge"),
		], className="vector-intro"),

		dbc.Card([
			dbc.CardHeader([
				htm.Span("Processing pipeline"),
				htm.Small("Runs automatically in this order", className="text-muted"),
			]),
			dbc.CardBody([
				htm.Div([
					pipelineStep(1, "Reconcile", "Backfill UUID fingerprints", "Identify Qdrant points that need a stable asset fingerprint and restore it from the local catalog.", "bi-fingerprint"),
					pipelineStep(2, "Reconcile", "Clean orphaned points", "Remove vectors that no longer correspond to an active, vectored Immich asset.", "bi-node-minus"),
					pipelineStep(3, "Generate", "Create missing embeddings", "Generate image embeddings for every asset that is not ready for similarity search yet.", "bi-cpu"),
					pipelineStep(4, "Verify", "Repair the search index", "Wait for indexing to settle, detect desynchronization, and prepare broken points for regeneration.", "bi-shield-check"),
				], className="vector-steps"),
				htm.Div([
					htm.I(className="bi bi-info-circle"),
					"You can safely cancel a running task; completed work remains recorded.",
				], className="vector-cancel-note"),
			])
		], className="vector-pipeline-card"),

		htm.Div([
			cardSets.renderGpuSettings() if conf.device.type in ['cuda','mps'] else cardSets.renderCpuSettings()
		], className="vector-runtime-settings"),

		htm.Div([
			htm.Div([
				htm.Small("Recommended", className="vector-action-label text-info"),
				dbc.Button("Execute: Process Assets", id=K.btnDoVec, color="primary", size="lg", className="w-100 vector-action-button", disabled=True),
				htm.Small("Run the complete reconcile, generate, and verify pipeline."),
			], className="vector-action-unit"),
			htm.Div([
				htm.Small("Recovery", className="vector-action-label text-warning"),
				dbc.Button("Repair Index", id=K.btnRepairIdx, color="warning", size="lg", className="w-100 vector-action-button", disabled=True, title="Scan Qdrant for HNSW index desync and repair, or clear vectored flag for unrepairable points"),
				htm.Small("Use independently only when search quality suggests an index issue."),
			], className="vector-action-unit"),
			htm.Div([
				htm.Small("Destructive", className="vector-action-label text-danger"),
				dbc.Button("Clear All Vectors", id=K.btnClear, color="danger", size="lg", className="w-100 vector-action-button", disabled=True),
				htm.Small("Remove every generated embedding; assets will need processing again."),
			], className="vector-action-unit vector-action-danger"),
		], className="vector-action-grid"),

		htm.Details([
			htm.Summary([
				htm.I(className="bi bi-life-preserver"),
				"When should I run Repair Index manually?",
			]),
			htm.Div([
				htm.P("The complete pipeline already repairs the index. Run the standalone repair only when:"),
				htm.Ul([
					htm.Li("Similarity search misses obvious duplicates or ranks a source behind unrelated results."),
					htm.Li("Processing was cancelled and you want to verify the remaining index."),
					htm.Li("Qdrant was restored or migrated and consistency needs verification."),
					htm.Li("A crash or network interruption may have stopped a bulk update."),
				]),
			], className="vector-repair-content"),
		], className="vector-repair-note"),
		#====== top end =========================================================
	], [
		#====== bottom start=====================================================

		#====== bottom end ======================================================
	], pageClass="page-vector")



#========================================================================
# Page Status Management - Unified callback for button states
#========================================================================
@cbk(
	[
		out(K.btnDoVec,"children"),
		out(K.btnDoVec,"disabled"),
		out(K.btnClear,"disabled"),
		out(K.btnRepairIdx,"disabled"),
	],
	[
		inp(ks.sto.cnt,"data"),
		inp(ks.sto.tsk,"data"),
	],
	prevent_initial_call=False
)
def vec_UpdateStatus(dta_cnt,dta_tsk):
	cnt=models.Cnt.fromDic(dta_cnt) if dta_cnt else models.Cnt()
	tsk=models.Tsk.fromDic(dta_tsk) if dta_tsk else models.Tsk()

	hasPics=cnt.ass>0
	hasVecs=cnt.vec>0
	cntNeedVec=cnt.ass-cnt.vec
	isTskRunning=tsk.id is not None

	btnTxt="Execute - Process Assets"
	disBtnRun=True
	disBtnClr=True
	disBtnRep=True

	lg.info(f"[vec] ass[{cnt.ass}] vec[{cnt.vec}] needVec[{cntNeedVec}] tskRunning[{isTskRunning}]")

	if isTskRunning:
		btnTxt="Task in progress.."
		disBtnRun=True
		disBtnClr=True
		disBtnRep=True
	elif hasVecs and cntNeedVec<=0:
		btnTxt="Vectors Complete"
		disBtnRun=True
		disBtnClr=False
		disBtnRep=False
	elif hasPics:
		if cntNeedVec>0:
			btnTxt=f"Process Assets( {cntNeedVec} )"
			disBtnRun=False
		else:
			btnTxt="Vectors Complete"
			disBtnRun=True
		disBtnClr=False if hasVecs else True
		disBtnRep=False if hasVecs else True
	else:
		btnTxt="Please Get Assets First"
		disBtnRun=True
		disBtnClr=True
		disBtnRep=True

	return btnTxt,disBtnRun,disBtnClr,disBtnRep

#------------------------------------------------------------------------
#------------------------------------------------------------------------
@cbk(
	[
		out(ks.sto.mdl, "data", allow_duplicate=True),
		out(ks.sto.nfy, "data", allow_duplicate=True),
		out(ks.sto.now, "data", allow_duplicate=True),
	],
	[
		inp(K.btnDoVec,"n_clicks"),
		inp(K.btnClear,"n_clicks"),
		inp(K.btnRepairIdx,"n_clicks"),
	],
	[
		ste(ks.sto.now, "data"),
		ste(ks.sto.cnt, "data"),
		ste(ks.sto.mdl, "data"),
		ste(ks.sto.tsk, "data"),
		ste(ks.sto.nfy, "data"),
	],
	prevent_initial_call=True
)
def vec_RunModal(nclk_proc,nclk_clear,nclkRepair,dta_now,dta_cnt,dta_mdl,dta_tsk,dta_nfy):
	if not nclk_proc and not nclk_clear and not nclkRepair:return noUpd.by(3)

	trgId = getTrgId()
	if trgId == ks.sto.tsk and not dta_tsk.get('id'): return noUpd.by(3)

	tsk = models.Tsk.fromDic(dta_tsk)
	if tsk.id: return noUpd.by(3)

	now = models.Now.fromDic(dta_now)
	cnt = models.Cnt.fromDic(dta_cnt)
	mdl = models.Mdl.fromDic(dta_mdl)
	nfy = models.Nfy.fromDic(dta_nfy)

	lg.info(f"[vec] trig[{trgId}] clk[{nclk_proc}/{nclk_clear}] tsk[{tsk}]")

	if trgId == K.btnDoVec:
		import chk
		modelOk, modelMsg = chk.model()
		if not modelOk:
			errMsg = modelMsg if isinstance(modelMsg, str) else '\n'.join(modelMsg)
			nfy.error(f"Model check failed: {errMsg}")
		elif cnt.ass <= 0: nfy.error("No asset data to process")
		else:
			mdl.id = ks.pg.vector
			mdl.cmd = ks.cmd.vec.toVec
			mdl.msg = f"Begin processing photos[{cnt.ass - cnt.vec}] ?"
	elif trgId==K.btnClear:
		if cnt.vec<=0:nfy.error("No vector data to clear")
		else:
			mdl.id=ks.pg.vector
			mdl.cmd=ks.cmd.vec.clear
			mdl.msg=[
				"Are you sure you want to clear all vectors?"
			]
	elif trgId==K.btnRepairIdx:
		if cnt.vec<=0:nfy.error("No vector data to repair")
		else:
			mdl.id=ks.pg.vector
			mdl.cmd=ks.cmd.vec.repairIdx
			mdl.msg=f"Scan Qdrant HNSW index for [ {cnt.vec} ] points. Broken points will be cleared and need re-generation. Continue?"

	return mdl.toDict(),nfy.toDict(),now.toDict()


#========================================================================
# task acts
#========================================================================
import imgs
from mod.models import IFnProg

def vec_ToVec(doReport: IFnProg, sto: models.ITaskStore):
	nfy, _, cnt = sto.nfy, sto.now, sto.cnt
	msg = "[vec] Processing successful"

	try:
		photoQ = db.dto.photoQ

		doReport(1, f"[ToVec] start with photoQ[{photoQ}]")

		if sto.isCancelled():
			msg = "Task was cancelled before processing"
			nfy.info(msg)
			return sto, msg

		doReport(2, "reconcile: scan no-uuid")
		nuids = db.vecs.getNoUuidAids()

		if nuids:
			allAss = db.pics.getAll()
			aidVec1 = {a.autoId: a.id for a in allAss if a.isVectored == 1}
			toFill = [(aid, aidVec1[aid]) for aid in nuids if aid in aidVec1]
			toDel = [aid for aid in nuids if aid not in aidVec1]

			if toFill:
				doReport(3, f"reconcile step1: backfill uuid ({len(toFill)})")
				db.vecs.setUuidPayloads(toFill)

			if toDel:
				doReport(4, f"reconcile: del orphan/non-ved ({len(toDel)})")
				bsz = 500
				batches = (len(toDel) + bsz - 1) // bsz
				for i in range(0, len(toDel), bsz):
					chunk = toDel[i:i + bsz]
					db.vecs.deleteBy(chunk)
					lg.info(f"[vec] delete batch[{i // bsz + 1}/{batches}] cnt[{len(chunk)}]")

		assets=db.pics.getAllNonVector()
		doReport(7, f"reconcile: process vecs ({len(assets)})")

		if not assets or len(assets) == 0:
			msg = "No assets to process"
			nfy.error(msg)
			return sto, msg

		if sto.isCancelled():
			msg = "Task was cancelled during initialization"
			nfy.info(msg)
			return sto, msg

		cntAll = len(assets)
		doReport(8, f"Found [ {cntAll} ] start processing..")

		newAids=set(a.autoId for a in assets)
		rst=imgs.processVectors(assets,photoQ,onUpdate=doReport,isCancelled=sto.isCancelled)

		if sto.isCancelled():
			msg=f"Processing cancelled: completed[ {rst.done} ] error[ {rst.erro} ]"
			nfy.info(msg)
			return sto,msg

		doReport(95,"wait Qdrant index build")
		if db.vecs.waitForGreen(timeout=600,isCancel=sto.isCancelled,doReport=doReport):
			doReport(96,"scan idx desync (exclude this-round)")
			scanned,repaired,broken=db.vecs.scanRepairIdx(doReport,sto.isCancelled,excludeAids=newAids)
			lg.info(f"[vec] post-repair scanned={scanned} repaired={repaired} broken={len(broken)}")
			if broken:
				db.pics.setVectoredByAids(broken,done=0)
				nfy.warn(f"Post-repair: {len(broken)} broken cleared, run again to regenerate. IDs: {broken[:20]}{'...' if len(broken) > 20 else ''}")
			elif repaired:
				nfy.info(f"Post-repair: fixed {repaired}/{scanned} point(s)")
		else:
			nfy.warn("Qdrant index still building, skipped post-repair")

		cnt.vec=db.pics.count(vectored=1)

		msg=f"Completed: total[ {rst.all} ] done[ {rst.done} ] Skip[ {rst.skip} ]"
		if rst.erro: msg += f" Error[ {rst.erro}]"

		nfy.success(msg)

		return sto, msg
	except Exception as e:
		if sto.isCancelled():
			msg = "Task was cancelled"
			nfy.info(msg)
			return sto, msg
		else:
			msg = f"Asset processing failed: {str(e)}"
			nfy.error(msg)
			raise RuntimeError(msg)


def vec_Clear(doReport: IFnProg, sto: models.ITaskStore):
	nfy, _, cnt = sto.nfy, sto.now, sto.cnt
	msg = "[AssetVec] Clearing successful"

	try:
		doReport(10, "Preparing to clear all Vectors")

		if cnt.vec <= 0:
			msg = "No vector data to clear"
			nfy.warn(msg)
			return sto, msg

		doReport(30, "Clearing Vectors...")

		count = db.vecs.count()
		if count >= 0:
			db.vecs.cleanAll()
			db.pics.clearAllVectored()

		doReport(90, f"Cleared {count} vector records")

		cnt.vec = db.pics.count(vectored=1)

		msg = f"Successfully cleared all photo vector data ({count} records)"
		nfy.success(msg)

		doReport(100, "Clearing complete")
		return sto, msg
	except Exception as e:
		msg = f"Failed to clear vectors: {str(e)}"
		nfy.error(msg)
		raise RuntimeError(msg)

def vecRepairIdx(doReport:IFnProg,sto:models.ITaskStore):
	nfy,_,cnt=sto.nfy,sto.now,sto.cnt
	msg="[vec] Repair index successful"

	try:
		doReport(1,"wait Qdrant index build")
		if not db.vecs.waitForGreen(timeout=600,isCancel=sto.isCancelled,doReport=doReport):
			msg="Qdrant index still building, please retry later"
			nfy.warn(msg)
			return sto,msg

		doReport(5,"scan idx desync")
		scanned,repaired,broken=db.vecs.scanRepairIdx(doReport,sto.isCancelled)
		lg.info(f"[vec] repairIdx scanned={scanned} repaired={repaired} broken={len(broken)}")

		if broken:
			db.pics.setVectoredByAids(broken,done=0)
			cnt.vec=db.pics.count(vectored=1)
			nfy.warn(f"Index scan: repaired[{repaired}] broken[{len(broken)}] cleared vectored flag, run Process Assets to regenerate")
			msg=f"scanned[{scanned}] repaired[{repaired}] broken[{len(broken)}]"
		elif repaired:
			nfy.info(f"Index scan: repaired {repaired}/{scanned} point(s)")
			msg=f"scanned[{scanned}] repaired[{repaired}]"
		else:
			nfy.success(f"Index scan clean: {scanned} point(s) verified")
			msg=f"scanned[{scanned}] all clean"

		doReport(100,msg)
		return sto,msg
	except Exception as e:
		if sto.isCancelled():
			msg="Task was cancelled"
			nfy.info(msg)
			return sto,msg
		else:
			msg=f"Repair index failed: {str(e)}"
			nfy.error(msg)
			raise RuntimeError(msg)

#========================================================================
# Set up global functions
#========================================================================
mapFns[ks.cmd.vec.toVec]=vec_ToVec
mapFns[ks.cmd.vec.clear]=vec_Clear
mapFns[ks.cmd.vec.repairIdx]=vecRepairIdx
