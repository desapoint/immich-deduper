#!/usr/bin/env python3

import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SRC = os.path.join(ROOT, 'src')
if SRC not in sys.path:
    sys.path.insert(0, SRC)

# tskMgr only needs these imports for socket integration, which this unit test
# deliberately does not exercise. Keep the regression test lightweight.
flask_socketio = types.ModuleType('flask_socketio')
flask_socketio.SocketIO = object
flask_socketio.emit = lambda *_args, **_kwargs: None
sys.modules.setdefault('flask_socketio', flask_socketio)

from mod.mgr.tskMgr import MAX_COMPLETED_TASKS, TskInfo, TskMgr
from mod.models import TskStatus


def _info(sn, status, ended=None):
    info = TskInfo(sn=sn, name=sn, dtc=0)
    info.status = status
    info.dte = ended
    return info


def test_prune_keeps_newest_terminal_tasks_and_active_state():
    mgr = TskMgr()

    for index in range(MAX_COMPLETED_TASKS + 3):
        sn = f'done-{index}'
        mgr.infos[sn] = _info(sn, TskStatus.COMPLETED, float(index + 1))
        mgr.tsks[sn] = object()
        mgr.threads[sn] = object()

    for sn, status in [('pending', TskStatus.PENDING), ('running', TskStatus.RUNNING)]:
        mgr.infos[sn] = _info(sn, status)
        mgr.tsks[sn] = object()
        mgr.threads[sn] = object()

    mgr._pruneCompleted()

    terminal = [sn for sn in mgr.infos if sn.startswith('done-')]
    assert len(terminal) == MAX_COMPLETED_TASKS
    assert 'done-0' not in mgr.infos
    assert 'done-1' not in mgr.infos
    assert 'done-2' not in mgr.infos
    assert f'done-{MAX_COMPLETED_TASKS + 2}' in mgr.infos

    for sn in ('pending', 'running'):
        assert sn in mgr.infos
        assert sn in mgr.tsks
        assert sn in mgr.threads

    for sn in ('done-0', 'done-1', 'done-2'):
        assert sn not in mgr.tsks
        assert sn not in mgr.threads


def test_prune_ignores_terminal_tasks_without_end_time():
    mgr = TskMgr()
    sn = 'in-transition'
    mgr.infos[sn] = _info(sn, TskStatus.COMPLETED)
    mgr.tsks[sn] = object()

    for index in range(MAX_COMPLETED_TASKS + 1):
        done = f'done-{index}'
        mgr.infos[done] = _info(done, TskStatus.FAILED, float(index + 1))
        mgr.tsks[done] = object()

    mgr._pruneCompleted()

    assert sn in mgr.infos
    assert sn in mgr.tsks
    assert 'done-0' not in mgr.infos


if __name__ == '__main__':
    test_prune_keeps_newest_terminal_tasks_and_active_state()
    test_prune_ignores_terminal_tasks_without_end_time()
    print('task history retention tests passed')
