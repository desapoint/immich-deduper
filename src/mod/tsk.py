import json
from dsh import htm, dbc, inp, out, ste, cbk, noUpd
from conf import ks
from util import log

from . import models
from .models import ITaskStore, IFnCall
# type define


# global function map
mapFns: dict[str, IFnCall] = {}

DEBUG = False

lg = log.get(__name__)


def _statusValue(status):
    return status.value if hasattr(status, "value") else status


def _messageText(message):
    if message is None: return ""
    if isinstance(message, str): return message.strip()
    if isinstance(message, list):
        return "\n".join(filter(None, (_messageText(item) for item in message))).strip()

    if hasattr(message, "to_plotly_json"):
        component = message.to_plotly_json()
        if component.get("type") == "Br": return ""
        return _messageText(component.get("props", {}).get("children"))

    return str(message).strip()


def _addCompletionNotification(sto, gws):
    status = _statusValue(gws.ste)
    taskMessages = sto.nfy.msgs[getattr(sto, "_nfyStart", len(sto.nfy.msgs)):]
    message = gws.msg
    taskName = sto.tsk.name or "Task"

    if not message:
        if status == models.TskStatus.FAILED.value: message = f"{taskName} failed"
        elif status == models.TskStatus.CANCELLED.value: message = f"{taskName} cancelled"
        else: message = f"{taskName} completed"

    target = _messageText(message)
    matchingMessage = any(_messageText(item.get("message")) == target for item in taskMessages)
    hasTaskError = any(item.get("type") == "danger" for item in taskMessages)

    if matchingMessage or (status == models.TskStatus.FAILED.value and hasTaskError): return

    if status == models.TskStatus.FAILED.value: sto.nfy.error(message)
    elif status == models.TskStatus.CANCELLED.value: sto.nfy.info(message)
    else: sto.nfy.success(message)

class k:
    div = 'task-ws-div'
    prg = 'task-ws-progress'
    txt = 'task-ws-txt'
    rst = 'task-ws-result'
    btnCancel = 'task-ws-btn-cancel'

def render():
    return htm.Div([
        htm.Div([
            htm.Span(className="task-status-dot", **{"aria-hidden": "true"}),
            htm.Span("Idle", id=k.txt, className="task-status-text"),
        ], className="task-status-summary"),
        dbc.Button(
            htm.I(className="bi bi-stop-circle"),
            id=k.btnCancel,
            className="task-status-cancel",
            size="sm",
            color="warning",
            disabled=True,
            title="Cancel running task",
        ),
        dbc.Progress(
            id=k.prg,
            value=0,
            animated=True,
            striped=True,
            label="0%",
            className="task-status-progress",
        ),
        htm.Div(id=k.rst, className="visually-hidden", **{"aria-live": "polite"}),
    ],
        id=k.div,
        className="tskPanel task-status idle",
        **{"aria-live": "polite", "aria-label": "Task status"},
    )


#========================================================================
# callbacks
#========================================================================
@cbk(
    [
        out(k.div, "className", allow_duplicate=True),
        out(k.txt, "children"),
        out(k.btnCancel, "disabled", allow_duplicate=True),
    ],
    inp(ks.sto.tsk, "data"),
    prevent_initial_call=True
)
def tsk_PanelStatus(dta_tsk):

    tsk = models.Tsk.fromDic(dta_tsk)
    isRunning = bool(tsk.id and tsk.name)
    css = "tskPanel task-status running" if isRunning else "tskPanel task-status idle"
    return css, tsk.name if isRunning else "Idle", not isRunning


#------------------------------------------------------------------------
@cbk(
    [
        out(ks.sto.nfy, "data", allow_duplicate=True),
        out(k.btnCancel, "disabled", allow_duplicate=True),
    ],
    inp(k.btnCancel, "n_clicks"),
    ste(ks.sto.tsk, "data"),
    ste(ks.sto.nfy, "data"),
    prevent_initial_call=True
)
def tsk_onBtnCancel(_nclk, dta_tsk, dta_nfy):
    if not _nclk: return noUpd.by(2)

    tsk = models.Tsk.fromDic(dta_tsk)
    nfy = models.Nfy.fromDic(dta_nfy)

    lg.info(f"[tsk] Cancel button clicked, tsk.id[{tsk.id}] tsk.tsn[{tsk.tsn}]")

    if not tsk.tsn:
        nfy.warn("No running task to cancel")
        return nfy.toDict(), noUpd

    from .mgr import tskSvc

    if tskSvc.cancelBy(tsk.tsn):
        nfy.info(f"Task {tsk.name} cancelled")
        lg.info(f"[tsk] Cancelled task: {tsk.tsn}")
        return nfy.toDict(), True
    else:
        nfy.warn("Failed to cancel task")
        return nfy.toDict(), noUpd

#------------------------------------------------------------------------
@cbk(
    [
        out(ks.sto.tsk, "data", allow_duplicate=True),
        out(ks.sto.nfy, "data", allow_duplicate=True),
    ],
    inp(ks.sto.tsk, "data"),
    ste(ks.sto.nfy, "data"),
    ste(ks.sto.now, "data"),
    ste(ks.sto.cnt, "data"),
    ste(ks.sto.ste, "data"),
    ste(ks.glo.gws, "data"),
    prevent_initial_call=True
)
def tsk_OnTasking(dta_tsk, dta_nfy, dta_now, dta_cnt, dta_ste, dta_gws):
    tsk = models.Tsk.fromDic(dta_tsk)
    nfy = models.Nfy.fromDic(dta_nfy)
    now = models.Now.fromDic(dta_now)
    cnt = models.Cnt.fromDic(dta_cnt)
    ste = models.Ste.fromDic(dta_ste)
    gws = models.Gws.fromDic(dta_gws)

    if not tsk.id or not tsk.cmd: return noUpd.by(2)

    if not gws.dtc:
        nfy.error(f"Cannot start task: WebSocket is not connected, state[{dta_gws}]")
        tsk.reset()

        return tsk.toDict(), nfy.toDict()

    #prevent task concurrent
    from .mgr.tskSvc import mgr
    if mgr:
        for tid, info in mgr.list().items():
            if info.status.value in ['pending', 'running']:
                nfy.warn(f"Task already running, please wait for it to complete")
                return tsk.toDict(), nfy.toDict()

    from .mgr import tskSvc

    lg.info(f"[tws:ing] into id[{tsk.id}] name[{tsk.name}] cmd[{tsk.cmd}]")

    fn = mapFns.get(tsk.cmd)

    if not fn:
        msg = f"[tws:ing] mapFns cmd[{tsk.cmd}] not found"
        nfy.error(msg)
        return tsk.toDict(), nfy.toDict()

    try:
        sto = ITaskStore(nfy, now, cnt, tsk, ste)

        tsn = tskSvc.mkTask(tsk, fn, sto)
        ok = tskSvc.runBy(tsn)
        tsk.tsn = tsn

        if ok:
            lg.info(f"[tws:ing] started, tsn[{tsn}] tsk: {tsk}")
            return tsk.toDict(), nfy.toDict()
        else:
            msg = "Failed to start task"
            nfy.error(msg)
            return tsk.toDict(), nfy.toDict()

    except Exception as e:
        msg = f"[tws:ing] Task failed: {str(e)}"
        lg.error(msg)
        nfy.error(msg)
        return tsk.toDict(), nfy.toDict()


#------------------------------------------------------------------------
@cbk(
    [
        out(k.prg, "value"),
        out(k.prg, "label"),
        out(k.rst, "children"),
    ],
    inp(ks.glo.gws, "data"),
    ste(ks.sto.tsk, "data"),
    ste(k.rst, "children"),
    prevent_initial_call=True
)
def tsk_UpdUI(gwsmsg, dta_tsk, rstChs):
    if not gwsmsg: return noUpd.by(3)

    gws = models.Gws.fromDic(gwsmsg)

    # lg.info(f"[tws:uui] received: {gwsmsg}, tsk: {dta_tsk}")
    try:
        # Direct message string from custom WebSocket
        tsk = models.Tsk.fromDic(dta_tsk)

        # 暫時不檢查 tsn，因為目前只支援單一任務
        # 之後可以改進為維護 tsn 映射表

        typ = gws.typ

        if typ == 'start':
            taskName = gws.nam
            tsn = gws.tsn
            lg.info(f"[tws:uui] start: {taskName} (tsn: {tsn}) current tsk: {dta_tsk}")
            return 0, "0%", f"Starting {taskName}..."

        elif typ == 'progress':
            # lg.info(f"[tws:uui] prog recv: {data}")
            prog = gws.prg
            msgs = gws.msg

            if isinstance(msgs, list):
                htms = []
                for idx, line in enumerate(msgs):
                    if idx > 0: htms.append(htm.Br())
                    htms.append(line)

                lg.info(f"[tws:uui] prog[{prog}] htms[{htms}] ")
                return prog, f"{prog}%", htms
            else:
                lg.info(f"[tws:uui] prog[{prog}] msg[{msgs}] ")
                return prog, f"{prog}%", msgs

        elif typ == 'complete':
            ste = _statusValue(gws.ste)
            msg = gws.msg

            if isinstance(msg, list):
                htms = []
                for idx, line in enumerate(msg):
                    if idx > 0: htms.append(htm.Br())
                    htms.append(line)
                msg = htms

            if ste == 'failed':
                return 100, "Failed", msg if msg else "task failed"

            if ste == 'cancelled':
                return 100, "Cancelled", msg if msg else "task cancelled"

            lg.info(f"[tws:uui] complete, ste[{ste}] chs[{rstChs}]")
            return 100, "completed", msg if msg else "Completed"


    except Exception as e:
        lg.error(f"[tws:uui] Error parsing message: {e}")

    return noUpd.by(3)



#------------------------------------------------------------------------
# 處理任務完成並更新 store
#------------------------------------------------------------------------
@cbk(
    [
        out(ks.sto.cnt, "data", allow_duplicate=True),
        out(ks.sto.nfy, "data", allow_duplicate=True),
        out(ks.sto.now, "data", allow_duplicate=True),
        out(ks.sto.tsk, "data", allow_duplicate=True),
        out(ks.sto.ste, "data", allow_duplicate=True),
    ],
    inp(ks.glo.gws, "data"),
    ste(ks.sto.tsk, "data"),
    prevent_initial_call=True
)
def tsk_OnData(wmsg, dta_tsk):
    if not wmsg: return noUpd.by(5)

    gws = models.Gws.fromDic(wmsg)

    try:

        typ = gws.typ

        if typ == 'start' or typ == 'progress':
            tsk = models.Tsk.fromDic(dta_tsk)

            if typ == 'start':
                taskName = gws.nam
                tsn = gws.tsn
            else:
                tsn = gws.tsn
                taskName = None

                from .mgr import tskSvc
                if tskSvc.mgr and tsn:
                    ti = tskSvc.mgr.getInfo(tsn)
                    if ti: taskName = ti.name

                if not taskName:
                    lg.warning(f"[tws:dta] Could not determine task name from progress message")
                    return noUpd.by(5)

            if not tsk.name or (taskName and tsk.name != taskName):
                lg.info(f"[tws:dta] Syncing task state on reconnect: {taskName} (tsn: {tsn})")
                tsk.name = taskName
                tsk.tsn = tsn
                tsk.id = f"reconnect-{tsn}" if tsn else f"reconnect-{taskName}"
                # Don't set cmd to avoid triggering new task
                return noUpd, noUpd, noUpd, tsk.toDict(), noUpd

            return noUpd.by(5)

        if typ == 'complete':

            from .mgr import tskSvc
            sto = tskSvc.getResultBy(gws.tsn)

            _addCompletionNotification(sto, gws)

            dicCnt, dicNfy, dicNow, dicTsk, dicSte = noUpd.by(5)

            # every task refresh cnt
            dicCnt = models.Cnt.mkNewCnt().toDict()

            dicNfy = sto.nfy.toDict()
            dicNow = sto.now.toDict()
            dicSte = sto.ste.toDict()

            tsk = sto.tsk  #note: can't concurrent

            if tsk.nexts and len(tsk.nexts):
                ntsk = tsk.nexts[0]
                ntsk.nexts = tsk.nexts[1:]

                dicTsk = ntsk.toDict()
            else:
                # Completion is reported through notifications; return the
                # persistent header status to its compact idle state.
                tsk.reset()
                dicTsk = tsk.toDict()

            return dicCnt, dicNfy, dicNow, dicTsk, dicSte

    except Exception as e:
        lg.error(f"[tws:dta] Error in tsk_OnComplete: {e}", exc_info=True)

    return noUpd.by(5)


#------------------------------------------------------------------------
@cbk(
    out(k.btnCancel, "disabled"),
    inp(ks.glo.gws, "data"),
    ste(ks.sto.tsk, "data"),
    prevent_initial_call=True
)
def tsk_OnStatus(wmsg, dta_tsk):
    if not wmsg: return noUpd

    try:
        # Direct message string from custom WebSocket
        data = json.loads(wmsg) if isinstance(wmsg, str) else wmsg
        if not data: raise RuntimeError( "[tsk] no data" )
        msgType = data.get('typ') or data.get('type')

        if msgType == 'start':
            return False
        elif msgType == 'complete':
            return True
    except Exception as e:
        lg.error(f"[tws:status] Error updating task status: {e}")

    return noUpd


#------------------------------------------------------------------------
# only for test
# @cbk(
#     out("task-test-ws-btn", "disabled"),
#     inp("task-test-ws-btn", "n_clicks"),
#     ste(ks.sto.tsk, "data"),
#     prevent_initial_call=True
# )
# def tsk_Test(n_clicks, dta_tsk):
    # if DEBUG: lg.info(f"[TSW] Button clicked: {n_clicks}")
    #
    # from .mgr.tskSvc import mgr
    # if not n_clicks: return noUpd
    #
    # tsk = models.Tsk.fromDic(dta_tsk)
    # if DEBUG: lg.info(f"[TSW] Current task: id={tsk.id}, name={tsk.name}")
    #
    # if not tsk.id:
    #     lg.info("[TSW] Creating test task for ws test")
    #     tsk.id = f"ws-test-{n_clicks}"
    #     tsk.name = "ws Test"
    #
    # if not mgr:
    #     lg.error("[TSW] TskMgr not initialized")
    #     return noUpd
    #
    # if not mgr.wsLoop:
    #     lg.error("[TSW] TskMgr ws_loop not available")
    #     return noUpd
    #
    # lg.info(f"[TSW] TskMgr ready, sending progress messages for task: {tsk.id}")
    #
    # start_msg = {
    #     'type': 'start',
    #     'tsn': tsk.tsn,
    #     'name': 'ws Test'
    # }
    # asyncio.run_coroutine_threadsafe(
    #     mgr.broadcast(start_msg),
    #     mgr.wsLoop
    # )
    #
    # for i in range(5):
    #     progress = i * 20 + 20
    #     msg = {
    #         'type': 'progress',
    #         'tsn': tsk.tsn,
    #         'progress': progress,
    #         'message': f'Test progress {progress}%',
    #         'status': 'running'
    #     }
    #
    #     lg.info(f"[TSW] Sending progress: {progress}%")
    #
    #     asyncio.run_coroutine_threadsafe(
    #         mgr.broadcast(msg),
    #         mgr.wsLoop
    #     )
    #
    #     time.sleep(0.5)  # wait ui update
    #
    # complete_msg = {
    #     'type': 'complete',
    #     'tsn': tsk.tsn,
    #     'status': 'completed',
    #     'result': 'Test completed successfully',
    #     'error': None
    # }
    # asyncio.run_coroutine_threadsafe(
    #     mgr.broadcast(complete_msg),
    #     mgr.wsLoop
    # )
    # lg.info("[TSW] ws test completed")
    #
    # return noUpd
