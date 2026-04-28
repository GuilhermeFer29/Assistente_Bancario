"""Serviço de crédito: limite, aumento de limite (Step-Up), atualização de score."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from assistente_bancario_v2.banking_gateway.app.core.config import configuracao_gateway
from assistente_bancario_v2.banking_gateway.app.core.logging_config import logger
from assistente_bancario_v2.banking_gateway.app.db.database import fabrica_sessao
from assistente_bancario_v2.banking_gateway.app.db.models import SolicitacaoLimite
from assistente_bancario_v2.banking_gateway.app.db.repositorio import (
    atualizar_score as repo_atualizar_score,
)
from assistente_bancario_v2.banking_gateway.app.db.repositorio import (
    buscar_cliente,
    faixa_de_score,
)

# Pesos da fórmula do score (mantidos do V1)
_PESO_RENDA = 30
_PESO_EMPREGO = {"formal": 300, "autonomo": 200, "desempregado": 0}
_PESO_DEPENDENTES = {0: 100, 1: 80, 2: 60}
_PESO_DIVIDAS = {"sim": -100, "nao": 100}


def _normalizar(s: str) -> str:
    traducao = str.maketrans("áàãâäéêëíïóôõöúüç", "aaaaaeeeiioooouuc")
    return s.strip().lower().translate(traducao)


# ── Aumento de limite (gera confirmação Step-Up) ─────────────────


async def processar_solicitacao_aumento(
    id_cliente: str, novo_limite: Decimal
) -> dict[str, Any]:
    """Cria a solicitação. NÃO altera o limite imediatamente — gera confirmação Step-Up."""
    async with fabrica_sessao() as sessao:
        cliente = await buscar_cliente(sessao, id_cliente)
        if cliente is None:
            return {"aprovado": False, "mensagem": "Cliente não encontrado."}

        if novo_limite <= 0:
            return {"aprovado": False, "mensagem": "O novo limite deve ser positivo."}

        faixa = await faixa_de_score(sessao, cliente.score_credito)
        if faixa is None:
            return {
                "aprovado": False,
                "mensagem": "Não foi possível determinar a faixa de limite.",
            }

        if novo_limite > faixa.limite_maximo:
            sessao.add(
                SolicitacaoLimite(
                    id_cliente=id_cliente,
                    limite_atual=cliente.limite_credito,
                    novo_limite_solicitado=novo_limite,
                    status_pedido="rejeitado",
                )
            )
            return {
                "aprovado": False,
                "requer_confirmacao": False,
                "limite_maximo_permitido": float(faixa.limite_maximo),
                "mensagem": (
                    f"Limite solicitado excede o máximo permitido (R$ {faixa.limite_maximo:.2f}) "
                    f"para o seu score atual."
                ),
            }

    # Operação aprovada em princípio — emitir Step-Up
    from assistente_bancario_v2.banking_gateway.app.services.confirmacao_service import (
        criar_confirmacao,
    )

    confirmacao = await criar_confirmacao(
        id_cliente=id_cliente,
        operacao="aumento_limite",
        dados_operacao={"novo_limite": str(novo_limite)},
    )
    logger.info(
        "aumento_limite_pendente_confirmacao",
        id_cliente=id_cliente,
        novo_limite=str(novo_limite),
    )
    return {
        "aprovado": False,
        "requer_confirmacao": True,
        "url_confirmacao": confirmacao["url"],
        "token_confirmacao": confirmacao["token"],
        "mensagem": (
            f"Para confirmar o aumento para R$ {novo_limite:.2f}, abra o link e digite sua senha."
        ),
    }


# ── Atualização de score (entrevista) ────────────────────────────


async def processar_atualizar_score(
    *,
    id_cliente: str,
    renda: Decimal,
    tipo_emprego: str,
    despesas_mensais: Decimal,
    dependentes: int,
    tem_dividas: str,
) -> dict[str, Any]:
    if renda < 0 or despesas_mensais < 0 or dependentes < 0:
        return {"sucesso": False, "mensagem": "Valores não podem ser negativos."}

    emprego = _normalizar(tipo_emprego)
    dividas = _normalizar(tem_dividas)
    if emprego not in _PESO_EMPREGO:
        return {
            "sucesso": False,
            "mensagem": "Tipo de emprego inválido (formal, autonomo ou desempregado).",
        }
    if dividas not in _PESO_DIVIDAS:
        return {"sucesso": False, "mensagem": "Informe se possui dívidas: sim ou nao."}

    termo_financeiro = float(renda) / (float(despesas_mensais) + 1) * _PESO_RENDA
    bonus_dep = _PESO_DEPENDENTES.get(dependentes, 30)
    novo_score = int(
        max(
            0,
            min(
                1000,
                termo_financeiro + _PESO_EMPREGO[emprego] + bonus_dep + _PESO_DIVIDAS[dividas],
            ),
        )
    )

    async with fabrica_sessao() as sessao:
        ok = await repo_atualizar_score(sessao, id_cliente, novo_score)
        if not ok:
            return {"sucesso": False, "mensagem": "Cliente não encontrado."}

    logger.info(
        "score_atualizado",
        id_cliente=id_cliente,
        novo_score=novo_score,
        renda=float(renda),
    )
    return {
        "sucesso": True,
        "novo_score": novo_score,
        "mensagem": f"Score atualizado: {novo_score}.",
    }


# Re-export para silenciar lint sobre uso da config
_ = configuracao_gateway
