"""Monkey-patches para o Agno 2.5.x / 2.6.x.

Workaround oficial das issues:
  https://github.com/agno-agi/agno/issues/7319  (Postgres)
  https://github.com/agno-agi/agno/issues/7381  (SQLite/MySQL — closed COMPLETED)

Bug: `_create_table` e `_get_or_create_table` em
`agno.db.sqlite.sqlite.SqliteDb` chamam `Table(name, self.metadata, ...)`
sem `extend_existing=True`. Quando a mesma `SqliteDb` é compartilhada
entre múltiplos agentes (exatamente como a doc oficial do Agno
recomenda), a segunda chamada para o mesmo `table_name` falha com
`InvalidRequestError: Table 'agno_memories' is already defined for
this MetaData instance.`

Fix: interceptar `_create_table` e `_get_or_create_table` para usar a
`Table` cacheada em `self.metadata.tables` quando ela já existe — caso
contrário, a flag `extend_existing=True` resolve no autoload.

Importar este módulo UMA vez no bootstrap do bot_service (em
`agente_base.py`) ANTES de criar qualquer Agent.
"""

from __future__ import annotations

import structlog
from agno.db.sqlite.sqlite import SqliteDb

logger = structlog.get_logger("agno_patches")

_PATCH_FLAG = "_assistente_v2_patched"


def aplicar_patches() -> None:
    """Aplica os monkey-patches uma única vez."""
    if getattr(SqliteDb, _PATCH_FLAG, False):
        return

    _orig_get_or_create = SqliteDb._get_or_create_table
    _orig_create = SqliteDb._create_table

    def _patched_get_or_create_table(self, table_name, table_type, create_table_if_not_found=False):  # type: ignore[no-untyped-def]
        # Cache: se já está no metadata, devolve direto (evita re-registrar via autoload)
        cached = self.metadata.tables.get(table_name)
        if cached is not None:
            return cached
        return _orig_get_or_create(
            self, table_name, table_type, create_table_if_not_found
        )

    def _patched_create_table(self, table_name, table_type):  # type: ignore[no-untyped-def]
        # Cache de criação: se já registrado neste metadata, devolve sem recriar
        cached = self.metadata.tables.get(table_name)
        if cached is not None:
            return cached
        return _orig_create(self, table_name, table_type)

    SqliteDb._get_or_create_table = _patched_get_or_create_table  # type: ignore[method-assign]
    SqliteDb._create_table = _patched_create_table  # type: ignore[method-assign]
    setattr(SqliteDb, _PATCH_FLAG, True)
    logger.info("agno_sqlite_patch_aplicado")
