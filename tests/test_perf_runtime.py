import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


class TestLazyMlRuntime(unittest.TestCase):
    def test_conf_import_does_not_import_torch(self):
        code = (
            "import sys; sys.path.insert(0, 'src'); import conf; "
            "assert 'torch' not in sys.modules, list(k for k in sys.modules if k.startswith('torch'))"
        )
        subprocess.run([sys.executable, '-c', code], cwd=ROOT, check=True)

    def test_imgs_import_does_not_import_torch(self):
        code = (
            "import sys; sys.path.insert(0, 'src'); import imgs; "
            "assert 'torch' not in sys.modules, list(k for k in sys.modules if k.startswith('torch'))"
        )
        subprocess.run([sys.executable, '-c', code], cwd=ROOT, check=True)

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
    def test_batch_upsert_uses_single_request(self):
        import numpy as np
        from db import vec_batch, vecs

        class FakeConn:
            def __init__(self): self.calls = []
            def upsert(self, **kwargs): self.calls.append(kwargs)

        fake = FakeConn()
        old = vecs.conn
        vecs.conn = fake
        try:
            items = [
                (1, np.ones(2048, dtype=np.float32), 'a'),
                (2, np.ones(2048, dtype=np.float32), 'b'),
            ]
            self.assertEqual(vec_batch.saveBatch(items, batchSize=128), 2)
            self.assertEqual(len(fake.calls), 1)
            self.assertEqual(len(fake.calls[0]['points']), 2)
        finally:
            vecs.conn = old


if __name__ == '__main__':
    unittest.main()
