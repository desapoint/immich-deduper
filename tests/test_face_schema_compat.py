#!/usr/bin/env python3

import importlib.util
import os
from contextlib import contextmanager
from types import SimpleNamespace

MODULE_PATH = os.path.join(os.path.dirname(__file__), '..', 'src', 'db', 'face_compat.py')
spec = importlib.util.spec_from_file_location('face_compat', MODULE_PATH)
face_compat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(face_compat)


LEGACY_QUERY = '''
Select af."assetId", af.id, af."personId", p.name, p."ownerId"
From asset_face af
Join person p On af."personId" = p.id
Where af."assetId" = ANY(%s) And af."deletedAt" Is Null
'''


class FakeLogger:
    def info(self, _message):
        pass


class FakeCursor:
    def __init__(self, columns):
        self.columns = columns
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchall(self):
        return [(column,) for column in self.columns]


class FakeConnection:
    def __init__(self, columns):
        self.columns = columns

    def cursor(self):
        return FakeCursor(self.columns)


class FakePsql:
    def __init__(self, columns):
        self.columns = columns
        self.schema = SimpleNamespace(assetFace='asset_face', asset='asset')
        self.Q = lambda sql: sql
        self.lg = FakeLogger()

    def getSchema(self):
        return self.schema

    @contextmanager
    def mkConn(self):
        yield FakeConnection(self.columns)


def test_current_schema_rewrites_face_join():
    fake = FakePsql({'personGroupId'})
    face_compat.install(fake)

    sql = fake.Q(LEGACY_QUERY)
    assert 'af."personGroupId" As "personId"' in sql
    assert 'Join asset a On af."assetId" = a.id' in sql
    assert 'p."personGroupId"' in sql
    assert 'a."ownerId" = p."ownerId"' in sql
    assert 'af."personId"' not in sql


def test_legacy_schema_keeps_original_query():
    fake = FakePsql({'personId'})
    face_compat.install(fake)

    assert fake.Q(LEGACY_QUERY) == LEGACY_QUERY


def test_install_is_idempotent():
    fake = FakePsql({'personGroupId'})
    face_compat.install(fake)
    first_q = fake.Q
    face_compat.install(fake)
    assert fake.Q is first_q


if __name__ == '__main__':
    test_current_schema_rewrites_face_join()
    test_legacy_schema_keeps_original_query()
    test_install_is_idempotent()
    print('face schema compatibility tests passed')
