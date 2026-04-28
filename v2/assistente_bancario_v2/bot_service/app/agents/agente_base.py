"""Fábrica padronizada de agentes Agno (V2) — espelho do BANKPER.

Padrões:
- Agentes têm `update_memory_on_run=True` (Team NÃO).
- Cada agente/Team recebe SUA própria instância de SqliteDb apontando
  para o mesmo arquivo (evita colisão de metadata do SQLAlchemy).
- Sem `respond_directly` ou `determine_input_for_members` — apenas TeamMode.route.
- Tools são plain async functions (sem closures, sem decoradores).
"""

from __future__ import annotations

from typing import Any

import structlog

# IMPORTAR o patch ANTES de qualquer Agent/Team (issue #7319/#7381 do Agno)
from assistente_bancario_v2.bot_service.app.agents._agno_patches import aplicar_patches

aplicar_patches()

from agno.agent import Agent  # noqa: E402
from agno.db.sqlite import SqliteDb  # noqa: E402
from agno.models.google import Gemini  # noqa: E402
from agno.team.mode import TeamMode  # noqa: E402
from agno.team.team import Team  # noqa: E402

from assistente_bancario_v2.bot_service.app.core.config import configuracao_bot  # noqa: E402

logger = structlog.get_logger("agente_base")

_db_compartilhado: SqliteDb | None = None


def obter_db() -> SqliteDb:
    """Retorna a `SqliteDb` única compartilhada por todos os agentes e o Team.

    Esta é a forma OFICIAL recomendada pela doc do Agno
    (https://docs.agno.com/memory/working-with-memories/overview) — todos os
    agentes que devem ver as mesmas memórias precisam usar a MESMA instância.

    O patch em `_agno_patches.py` corrige o bug do issue #7381 que impedia
    isso de funcionar (Table 'agno_memories' is already defined for this
    MetaData instance).
    """
    global _db_compartilhado
    if _db_compartilhado is None:
        _db_compartilhado = SqliteDb(db_file=configuracao_bot.agno_db_file)
    return _db_compartilhado


_INSTRUCOES_BASE_AGENTE = [
    "Você é um assistente bancário digital do Banco Ágil.",
    "Sempre responda em português brasileiro, profissional e acolhedor.",
    "Use Markdown — listas com cada item em sua própria linha.",
    "Nunca invente dados. Use APENAS dados retornados pelas ferramentas.",
    "Formate valores monetários como: R$ 1.234,56.",
    "Seja breve, objetivo e termine perguntando se pode ajudar com mais alguma coisa.",
]


def criar_agente(
    *,
    nome: str,
    descricao: str,
    role: str,
    instrucoes: list[str],
    tools: list[Any] | None = None,
    num_history_runs: int = 3,
) -> Agent | None:
    """Cria um Agent Agno padronizado. Retorna None se Gemini não estiver configurado."""
    if not configuracao_bot.gemini_api_key:
        logger.warning("agente_nao_criado_sem_gemini", agente=nome)
        return None

    return Agent(
        name=nome,
        role=role,
        description=descricao,
        model=Gemini(id=configuracao_bot.gemini_model, api_key=configuracao_bot.gemini_api_key),
        tools=tools or [],
        instructions=_INSTRUCOES_BASE_AGENTE + instrucoes,
        markdown=True,
        add_datetime_to_context=True,
        db=obter_db(),
        add_history_to_context=True,
        num_history_runs=num_history_runs,
        enable_session_summaries=True,
        add_session_summary_to_context=True,
        update_memory_on_run=True,
    )


_INSTRUCOES_LIDER = [
    "Você é o Coordenador do Banco Ágil. Sua única tarefa é DELEGAR cada mensagem",
    "para um agente especializado. Você NUNCA escreve resposta para o cliente.",
    "Cada mensagem do cliente vem com um prefixo `[id_cliente=CLI...]` — repasse o id_cliente",
    "ao agente quando necessário; ele saberá usar nas ferramentas.",
]


def criar_team(
    *,
    nome: str,
    instrucoes: list[str],
    membros: list[Agent],
    mode: TeamMode = TeamMode.route,
) -> Team | None:
    """Cria o Team Agno no padrão BANKPER (route, sem respond_directly)."""
    if not configuracao_bot.gemini_api_key:
        return None
    if not membros:
        return None

    return Team(
        name=nome,
        mode=mode,
        model=Gemini(id=configuracao_bot.gemini_model, api_key=configuracao_bot.gemini_api_key),
        members=membros,
        instructions=_INSTRUCOES_LIDER + instrucoes,
        markdown=True,
        db=obter_db(),
        add_history_to_context=True,
        num_history_runs=5,
        enable_session_summaries=True,
        add_session_summary_to_context=True,
    )
