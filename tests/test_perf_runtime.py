import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


class TestLazyMlRuntime(unittest.TestCase):
    def _run_clean_python(self, code, env=None):
        subprocess.run(
            [sys.executable, '-c', code],
            cwd=ROOT,
            env=env,
            check=True,
        )

    def test_conf_import_does_not_import_torch(self):
        self._run_clean_python(
            "import sys; sys.path.insert(0, 'src'); import conf; "
            "assert 'torch' not in sys.modules, list(k for k in sys.modules if k.startswith('torch'))"
        )

    def test_configured_device_hint_stays_lazy(self):
        for device in ('cpu', 'cuda128'):
            env = os.environ.copy()
            env['DEDUP_DEVICE'] = device
            self._run_clean_python(
                "import sys; sys.path.insert(0, 'src'); import conf; "
                "assert conf.device.type in ('cpu', 'cuda'); "
                "assert 'torch' not in sys.modules, list(k for k in sys.modules if k.startswith('torch'))",
                env=env,
            )

    def test_imgs_import_does_not_import_torch_or_torchvision(self):
        self._run_clean_python(
            "import sys; sys.path.insert(0, 'src'); import imgs; "
            "assert 'torch' not in sys.modules, list(k for k in sys.modules if k.startswith('torch')); "
            "assert 'torchvision' not in sys.modules, list(k for k in sys.modules if k.startswith('torchvision'))"
        )

    def test_model_check_does_not_load_ml_runtime(self):
        code = (
            "import os, sys, tempfile; sys.path.insert(0, 'src'); "
            "os.environ['DEDUP_DATA'] = tempfile.mkdtemp(); "
            "import model_check_opt; model_check_opt.model(); "
            "assert 'torch' not in sys.modules; assert 'torchvision' not in sys.modules"
        )
        self._run_clean_python(code)

    def test_memory_trim_does_not_import_torch(self):
        self._run_clean_python(
            "import sys; sys.path.insert(0, 'src'); import perf; perf.trimMemory(); "
            "assert 'torch' not in sys.modules"
        )

    def test_model_unload_respects_active_sessions(self):
        import imgs
        fake = object()
        with patch.object(imgs, '_loadModel', return_value=fake), \
             patch.object(imgs, '_startModelMonitor', return_value=None), \
             patch.object(imgs, 'trimMemory', return_value=None):
            imgs._model = None
            imgs._model_active = 0
            self.assertIs(imgs.getModel(), fake)
            imgs._model_active = 1
            self.assertFalse(imgs.unloadModel(reason='test'))
            self.assertIs(imgs._model, fake)
            imgs._model_active = 0
            self.assertTrue(imgs.unloadModel(reason='test'))
            self.assertIsNone(imgs._model)


class TestBatchVectorWrites(unittest.TestCase):
    @staticmethod
    def _items():
        import numpy as np
        return [
            (1, np.ones(2048, dtype=np.float32), 'a'),
            (2, np.ones(2048, dtype=np.float32), 'b'),
        ]

    def test_batch_upsert_uses_single_request(self):
        from db import vec_batch, vecs

        class FakeConn:
            def __init__(self): self.calls = []
            def upsert(self, **kwargs): self.calls.append(kwargs)

        fake = FakeConn()
        old = vecs.conn
        vecs.conn = fake
        try:
            self.assertEqual(vec_batch.saveBatch(self._items(), batchSize=128), 2)
            self.assertEqual(len(fake.calls), 1)
            self.assertEqual(len(fake.calls[0]['points']), 2)
            self.assertTrue(fake.calls[0]['wait'])
        finally:
            vecs.conn = old

    def test_batch_failure_falls_back_per_vector(self):
        from db import vec_batch, vecs

        def save_one(aid, vector, uuid, confirm=False):
            self.assertFalse(confirm)
            if aid == 2:
                raise RuntimeError('single write failed')

        with patch.object(vec_batch, 'saveBatch', side_effect=RuntimeError('batch failed')), \
             patch.object(vecs, 'save', side_effect=save_one) as save_mock:
            status = vec_batch.saveBatchWithFallback(self._items(), batchSize=128)

        self.assertIsNone(status[1])
        self.assertIn('single write failed', status[2])
        self.assertEqual(save_mock.call_count, 2)


class TestStreamingAssetReads(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.execute(
            'CREATE TABLE assets ('
            'autoId INTEGER PRIMARY KEY, id TEXT NOT NULL, isVectored INTEGER NOT NULL DEFAULT 0)'
        )
        self.conn.executemany(
            'INSERT INTO assets(autoId, id, isVectored) VALUES (?, ?, ?)',
            [(1, 'a', 0), (2, 'b', 0), (3, 'c', 0), (4, 'd', 1), (5, 'e', 0)],
        )
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def test_non_vector_chunks_advance_by_auto_id(self):
        from db import pics_stream

        with patch.object(pics_stream.pics, 'mkConn', return_value=self.conn):
            first = pics_stream.getNonVectorChunk(afterAutoId=0, limit=2)
            self.assertEqual([asset.autoId for asset in first], [1, 2])

            self.conn.execute('UPDATE assets SET isVectored=1 WHERE autoId IN (1, 2)')
            self.conn.commit()

            second = pics_stream.getNonVectorChunk(afterAutoId=2, limit=2)
            self.assertEqual([asset.autoId for asset in second], [3, 5])

            self.conn.execute('UPDATE assets SET isVectored=1 WHERE autoId IN (3, 5)')
            self.conn.commit()
            self.assertEqual(pics_stream.getNonVectorChunk(afterAutoId=5, limit=2), [])

    def test_uuid_reconciliation_queries_only_vectored_requested_ids(self):
        from db import pics_stream

        with patch.object(pics_stream.pics, 'mkConn', return_value=self.conn):
            result = pics_stream.getVectoredUuidMap({1, 4, 5}, batchSize=2)

        self.assertEqual(result, {4: 'd'})


if __name__ == '__main__':
    unittest.main()
