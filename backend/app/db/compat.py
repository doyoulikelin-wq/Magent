"""Cross-database type compatibility layer.

Import ``UUID``, ``JSONB``, and ``StringArray`` from here instead of
``sqlalchemy.dialects.postgresql`` so the same models work on both
PostgreSQL and SQLite (for local development / testing).
"""

from __future__ import annotations

import json

from sqlalchemy import JSON, String, Text
from sqlalchemy import Uuid as _SAUuid
from sqlalchemy import types


class UUID(_SAUuid):
    """Drop-in replacement for ``postgresql.UUID(as_uuid=True)``.

    On PostgreSQL the native UUID column is used; on SQLite values are
    stored as ``CHAR(32)``.
    """

    cache_ok = True

    def __init__(self, as_uuid: bool = True) -> None:  # noqa: ARG002
        super().__init__(native_uuid=True)


# JSONB → generic JSON (works on PG + SQLite)
JSONB = JSON


class StringArray(types.TypeDecorator):
    """``ARRAY(String)`` on PostgreSQL, ``TEXT`` (JSON-encoded) on SQLite."""

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):  # type: ignore[override]
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY

            return dialect.type_descriptor(PG_ARRAY(String))
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):  # type: ignore[override]
        if dialect.name == "postgresql":
            return value
        if value is not None:
            return json.dumps(value, ensure_ascii=False)
        return None

    def process_result_value(self, value, dialect):  # type: ignore[override]
        if dialect.name == "postgresql":
            return value
        if value is not None:
            return json.loads(value)
        return None
