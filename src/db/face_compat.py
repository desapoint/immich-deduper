"""Compatibility shim for Immich face/person schema changes.

Newer Immich moved asset_face.personId to personGroupId and removed person.id.
Deduper's extended-info query still uses the legacy join, so rewrite only that
specific query after detecting the active asset_face column.
"""

_FACE_QUERY_MARKER = 'Join person p On af."personId" = p.id'


def _face_mode(psql_module):
    sch = psql_module.getSchema()
    with psql_module.mkConn() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = %s
                  AND column_name IN ('personId', 'personGroupId')
                """,
                (sch.assetFace,),
            )
            columns = {row[0] for row in cursor.fetchall()}

    if 'personGroupId' in columns:
        return 'personGroupId'
    if 'personId' in columns:
        return 'personId'
    raise RuntimeError(
        f"Unsupported Immich face schema: neither personId nor personGroupId exists on {sch.assetFace}"
    )


def _current_face_query(psql_module):
    sch = psql_module.getSchema()
    return f"""
                    Select af."assetId", af.id, af."personGroupId" As "personId", p.name, p."ownerId",
                            af."imageWidth", af."imageHeight", af."boundingBoxX1", af."boundingBoxY1",
                            af."boundingBoxX2", af."boundingBoxY2", af."sourceType"
                    From {sch.assetFace} af
                    Join {sch.asset} a On af."assetId" = a.id
                    Join person p On af."personGroupId" = p."personGroupId" And a."ownerId" = p."ownerId"
                    Where af."assetId" = ANY(%s) And af."deletedAt" Is Null
                    """


def install(psql_module):
    """Install the query rewrite once for the active Immich schema."""
    if getattr(psql_module, '_face_compat_installed', False):
        return

    mode = _face_mode(psql_module)
    original_q = psql_module.Q

    if mode == 'personGroupId':
        def compat_q(sql):
            if _FACE_QUERY_MARKER in sql:
                return original_q(_current_face_query(psql_module))
            return original_q(sql)

        psql_module.Q = compat_q
        psql_module.lg.info('[psql] Immich face schema: personGroupId compatibility enabled')
    else:
        psql_module.lg.info('[psql] Immich face schema: legacy personId')

    psql_module._face_compat_installed = True
