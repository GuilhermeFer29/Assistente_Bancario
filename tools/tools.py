from __future__ import annotations

from typing import Any, Dict

from services import (
    atualizar_limite_cliente,
    atualizar_score_cliente as atualizar_score_csv,
    buscar_cliente_por_cpf,
    limpar_cpf,
    normalizar_data,
    obter_limite_permitido_por_score,
    registrar_solicitacao_limite,
)


def _normalizar_texto(valor: str) -> str:
    if not isinstance(valor, str):
        return ""
    traducoes = {
        "ã": "a",
        "â": "a",
        "á": "a",
        "à": "a",
        "õ": "o",
        "ô": "o",
        "ó": "o",
        "ç": "c",
        "é": "e",
        "ê": "e",
        "í": "i",
        "ú": "u",
    }
    texto = valor.strip().lower()
    for antigo, novo in traducoes.items():
        texto = texto.replace(antigo, novo)
    return texto


def validando_cliente(cpf: str, dt_nascimento: str) -> Dict[str, Any]:
    cpf_limpo = limpar_cpf(cpf)
    data = normalizar_data(dt_nascimento)
    cliente = buscar_cliente_por_cpf(cpf_limpo)
    if not cliente or cliente["dt_nascimento"] != data:
        return {
            "status": "erro",
            "mensagem": "Os dados informados não conferem com nosso cadastro. Confira CPF e data de nascimento.",
        }
    return {
        "status": "ok",
        "nome": cliente["nome"],
        "score_credito": cliente["score_credito"],
        "mensagem": f"Cliente autenticado: {cliente['nome']} (score {cliente['score_credito']}).",
    }


def consultando_limite(cpf: str) -> Dict[str, Any]:
    cpf_limpo = limpar_cpf(cpf)
    cliente = buscar_cliente_por_cpf(cpf_limpo)
    if not cliente:
        return {
            "status": "erro",
            "mensagem": "Não localizamos seu cadastro. Confirme o CPF informado.",
        }
    return {
        "status": "ok",
        "nome": cliente["nome"],
        "limite_atual": cliente["limite_credito"],
        "mensagem": f"Limite atual disponível: R$ {cliente['limite_credito']:.2f}.",
    }


def solicitacao_de_limite(cpf: str, novo_limite: float) -> Dict[str, Any]:
    cpf_limpo = limpar_cpf(cpf)
    cliente = buscar_cliente_por_cpf(cpf_limpo)
    if not cliente:
        return {
            "status": "erro",
            "mensagem": "Não encontramos seu cadastro para processar a solicitação.",
        }

    try:
        novo_limite_float = float(novo_limite)
    except (TypeError, ValueError):
        return {
            "status": "erro",
            "mensagem": "O valor do novo limite precisa ser numérico.",
        }
    if novo_limite_float <= 0:
        return {
            "status": "erro",
            "mensagem": "O novo limite deve ser maior que zero.",
        }

    limite_permitido = obter_limite_permitido_por_score(cliente["score_credito"])
    if limite_permitido is None:
        return {
            "status": "erro",
            "mensagem": "Não conseguimos determinar o limite disponível para seu score.",
        }

    status = "rejeitado"
    if novo_limite_float <= limite_permitido:
        status = "aprovado"
        atualizar_limite_cliente(cpf_limpo, novo_limite_float)

    registrar_solicitacao_limite(
        cpf=cpf_limpo,
        limite_atual=cliente["limite_credito"],
        novo_limite=novo_limite_float,
        status=status,
    )

    if status == "aprovado":
        return {
            "status": "ok",
            "mensagem": (
                f"Solicitação aprovada! Seu novo limite é R$ {novo_limite_float:.2f}"
                f" (faixa permitida até R$ {limite_permitido:.2f})."
            ),
            "novo_limite": novo_limite_float,
            "limite_maximo_permitido": limite_permitido,
        }
    return {
        "status": "erro",
        "mensagem": (
            "Não foi possível aprovar o novo limite porque o valor solicitado"
            f" excede o máximo permitido para seu score (até R$ {limite_permitido:.2f})."
        ),
        "limite_maximo_permitido": limite_permitido,
    }


def atualizar_score_cliente(
    cpf: str,
    renda: float,
    tipo_emprego: str,
    despesas_mensais: float,
    dependentes: int,
    tem_dividas: str,
) -> Dict[str, Any]:
    peso_emprego = {"formal": 300, "autonomo": 200, "desempregado": 0}
    peso_dividas = {"sim": -100, "nao": 100}

    try:
        renda_float = float(renda)
        despesas_float = float(despesas_mensais)
        dependentes_int = int(dependentes)
    except (TypeError, ValueError):
        return {
            "status": "erro",
            "mensagem": "Renda, despesas e dependentes precisam ser numéricos.",
        }

    if renda_float < 0 or despesas_float < 0 or dependentes_int < 0:
        return {
            "status": "erro",
            "mensagem": "Nenhum dos valores pode ser negativo.",
        }

    emprego_normalizado = _normalizar_texto(tipo_emprego)
    dividas_normalizado = _normalizar_texto(tem_dividas)

    if emprego_normalizado not in peso_emprego:
        return {
            "status": "erro",
            "mensagem": (
                "Classifique o tipo de emprego em: formal, autonomo ou desempregado."
            ),
        }
    if dividas_normalizado not in peso_dividas:
        return {
            "status": "erro",
            "mensagem": "Informe se possui dívidas: 'sim' ou 'nao'.",
        }

    termo_financeiro = (renda_float / (despesas_float + 1)) * 30
    dependentes_bonus = {0: 100, 1: 80, 2: 60}.get(dependentes_int, 30)
    novo_score = int(
        min(
            1000,
            max(
                0,
                termo_financeiro
                + peso_emprego[emprego_normalizado]
                + peso_dividas[dividas_normalizado]
                + dependentes_bonus,
            ),
        )
    )

    cpf_limpo = limpar_cpf(cpf)
    cliente = buscar_cliente_por_cpf(cpf_limpo)
    if not cliente:
        return {
            "status": "erro",
            "mensagem": "Cliente não encontrado para atualizar o score.",
        }

    try:
        atualizar_score_csv(cpf_limpo, novo_score)
    except ValueError:
        return {
            "status": "erro",
            "mensagem": "Cliente não encontrado para atualizar o score.",
        }

    return {
        "status": "ok",
        "mensagem": f"Score atualizado com sucesso! Novo score: {novo_score}.",
        "novo_score": novo_score,
    }







    

    