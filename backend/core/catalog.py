from contextlib import contextmanager
from datetime import datetime
from typing import Iterator
from uuid import UUID

from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row

from backend.settings import settings

_pool: ConnectionPool | None = None


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            conninfo=settings.database_url,
            min_size=1,
            max_size=8,
            kwargs={"row_factory": dict_row},
            open=True,
        )
    return _pool


@contextmanager
def conn() -> Iterator:
    pool = get_pool()
    with pool.connection() as c:
        yield c


def insert_document(
    *, filename: str, sha256: str, storage_path: str
) -> UUID:
    with conn() as c:
        row = c.execute(
            """
            INSERT INTO documents (filename, sha256, status, storage_path)
            VALUES (%s, %s, 'pending', %s)
            RETURNING document_id
            """,
            (filename, sha256, storage_path),
        ).fetchone()
        return row["document_id"]


def find_by_sha256(sha256: str) -> dict | None:
    with conn() as c:
        return c.execute(
            "SELECT * FROM documents WHERE sha256 = %s", (sha256,)
        ).fetchone()


def get_document(document_id: UUID) -> dict | None:
    with conn() as c:
        return c.execute(
            "SELECT * FROM documents WHERE document_id = %s", (document_id,)
        ).fetchone()


def list_documents() -> list[dict]:
    with conn() as c:
        return c.execute(
            "SELECT * FROM documents ORDER BY uploaded_at DESC"
        ).fetchall()


def list_indexed_ids() -> list[str]:
    with conn() as c:
        rows = c.execute(
            "SELECT document_id FROM documents WHERE status = 'indexed'"
        ).fetchall()
        return [str(r["document_id"]) for r in rows]


def count_indexed() -> int:
    with conn() as c:
        row = c.execute(
            "SELECT COUNT(*) AS n FROM documents WHERE status = 'indexed'"
        ).fetchone()
        return int(row["n"])


def update_status(
    document_id: UUID,
    status: str,
    *,
    page_count: int | None = None,
    chunk_count: int | None = None,
    error_message: str | None = None,
) -> None:
    with conn() as c:
        c.execute(
            """
            UPDATE documents
               SET status = %s,
                   page_count = COALESCE(%s, page_count),
                   chunk_count = COALESCE(%s, chunk_count),
                   error_message = %s
             WHERE document_id = %s
            """,
            (status, page_count, chunk_count, error_message, document_id),
        )


def delete_document(document_id: UUID) -> dict | None:
    with conn() as c:
        return c.execute(
            "DELETE FROM documents WHERE document_id = %s RETURNING *",
            (document_id,),
        ).fetchone()
