"""Gateway client — Protocol + duas implementações (in_process e http).

A escolha é feita por `configuracao_bot.gateway_transport`. Os agentes
nunca precisam saber qual transporte está ativo.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Protocol

import httpx
import structlog

from assistente_bancario_v2.bot_service.app.core.config import configuracao_bot

_logger = structlog.get_logger("gateway_client")


def _normalizar_payload(obj: Any) -> Any:
    """Converte recursivamente Decimal/date/datetime em str/iso para JSON."""
    if isinstance(obj, dict):
        return {k: _normalizar_payload(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalizar_payload(v) for v in obj]
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    return obj


class GatewayClient(Protocol):
    """Contrato de acesso ao banking_gateway."""

    async def consultar_cliente(self, id_cliente: str) -> dict[str, Any] | None: ...

    async def consultar_saldo(self, id_cliente: str) -> dict[str, Any] | None: ...

    async def consultar_contas(
        self,
        id_cliente: str,
        tipo: str,
        data_inicio: date | None = None,
        data_fim: date | None = None,
    ) -> dict[str, Any] | None: ...

    async def consultar_limite(self, id_cliente: str) -> dict[str, Any] | None: ...

    async def solicitar_aumento_limite(
        self, id_cliente: str, novo_limite: Decimal
    ) -> dict[str, Any]: ...

    async def atualizar_score(
        self,
        id_cliente: str,
        renda: Decimal,
        tipo_emprego: str,
        despesas_mensais: Decimal,
        dependentes: int,
        tem_dividas: str,
    ) -> dict[str, Any]: ...

    async def iniciar_otp(self, id_cliente: str) -> dict[str, Any]: ...

    async def validar_otp(self, id_cliente: str, codigo: str) -> dict[str, Any]: ...

    async def criar_confirmacao(
        self, id_cliente: str, operacao: str, dados_operacao: dict[str, Any]
    ) -> dict[str, Any]: ...

    async def criar_transacao(self, **kwargs: Any) -> dict[str, Any]: ...

    async def pagar_conta_existente(
        self, id_cliente: str, id_conta: str
    ) -> dict[str, Any]: ...

    async def fechar(self) -> None: ...


# ── Implementação HTTP ─────────────────────────────────────────────


class HttpGatewayClient:
    """Cliente HTTP reutilizando uma conexão por instância."""

    def __init__(self, base_url: str | None = None, timeout: float = 10.0) -> None:
        self._base_url = base_url or configuracao_bot.gateway_url
        headers = {"X-Internal-Token": configuracao_bot.internal_api_token}
        self._http = httpx.AsyncClient(
            base_url=self._base_url, timeout=timeout, headers=headers
        )

    async def fechar(self) -> None:
        await self._http.aclose()

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """GET ao gateway. Retorna None apenas em 404; demais erros são logados e retornam None.

        Distingue 'recurso inexistente' (404) de 'gateway indisponível' nos logs.
        """
        try:
            r = await self._http.get(path, params=params)
        except httpx.TimeoutException:
            _logger.error("gateway_get_timeout", path=path)
            return None
        except httpx.ConnectError as exc:
            _logger.error("gateway_get_indisponivel", path=path, erro=str(exc))
            return None
        except httpx.HTTPError as exc:
            _logger.error("gateway_get_http_error", path=path, erro=str(exc))
            return None

        if r.status_code == 404:
            return None
        if r.is_success:
            return r.json()  # type: ignore[no-any-return]
        _logger.error("gateway_get_status", path=path, status=r.status_code, body=r.text[:200])
        return None

    async def _post(self, path: str, json: dict[str, Any]) -> dict[str, Any]:
        """POST ao gateway. Converte Decimal/date e trata erros sem propagar exceções."""
        payload = _normalizar_payload(json)
        try:
            r = await self._http.post(path, json=payload)
        except httpx.TimeoutException:
            _logger.error("gateway_post_timeout", path=path)
            return {"erro": "Tempo de resposta excedido. Tente novamente."}
        except httpx.ConnectError as exc:
            _logger.error("gateway_post_indisponivel", path=path, erro=str(exc))
            return {"erro": "Serviço indisponível no momento."}
        except httpx.HTTPError as exc:
            _logger.error("gateway_post_http_error", path=path, erro=str(exc))
            return {"erro": "Falha de comunicação com o serviço bancário."}

        if r.is_success:
            return r.json()  # type: ignore[no-any-return]

        # Tenta extrair detalhe do gateway
        try:
            body = r.json()
        except Exception:  # noqa: BLE001
            body = {"detail": r.text[:200]}
        _logger.warning("gateway_post_status", path=path, status=r.status_code, body=body)
        return {"erro": body.get("detail", f"Erro HTTP {r.status_code}")}

    async def consultar_cliente(self, id_cliente: str) -> dict[str, Any] | None:
        return await self._get(f"/clientes/{id_cliente}")

    async def consultar_saldo(self, id_cliente: str) -> dict[str, Any] | None:
        return await self._get(f"/saldo/{id_cliente}")

    async def consultar_contas(
        self,
        id_cliente: str,
        tipo: str,
        data_inicio: date | None = None,
        data_fim: date | None = None,
    ) -> dict[str, Any] | None:
        params: dict[str, Any] = {"tipo": tipo}
        if data_inicio:
            params["data_inicio"] = data_inicio.isoformat()
        if data_fim:
            params["data_fim"] = data_fim.isoformat()
        return await self._get(f"/contas/{id_cliente}", params=params)

    async def consultar_limite(self, id_cliente: str) -> dict[str, Any] | None:
        return await self._get(f"/credito/limite/{id_cliente}")

    async def solicitar_aumento_limite(
        self, id_cliente: str, novo_limite: Decimal
    ) -> dict[str, Any]:
        return await self._post(
            "/credito/solicitar-aumento",
            {"id_cliente": id_cliente, "novo_limite": str(novo_limite)},
        )

    async def atualizar_score(
        self,
        id_cliente: str,
        renda: Decimal,
        tipo_emprego: str,
        despesas_mensais: Decimal,
        dependentes: int,
        tem_dividas: str,
    ) -> dict[str, Any]:
        return await self._post(
            "/credito/atualizar-score",
            {
                "id_cliente": id_cliente,
                "renda": str(renda),
                "tipo_emprego": tipo_emprego,
                "despesas_mensais": str(despesas_mensais),
                "dependentes": dependentes,
                "tem_dividas": tem_dividas,
            },
        )

    async def iniciar_otp(self, id_cliente: str) -> dict[str, Any]:
        return await self._post("/otp/iniciar", {"id_cliente": id_cliente})

    async def validar_otp(self, id_cliente: str, codigo: str) -> dict[str, Any]:
        return await self._post(
            "/otp/validar", {"id_cliente": id_cliente, "codigo": codigo}
        )

    async def criar_confirmacao(
        self, id_cliente: str, operacao: str, dados_operacao: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._post(
            "/confirmacao/criar",
            {
                "id_cliente": id_cliente,
                "operacao": operacao,
                "dados_operacao": dados_operacao,
            },
        )

    async def criar_transacao(self, **kwargs: Any) -> dict[str, Any]:
        return await self._post("/transacao", kwargs)

    async def pagar_conta_existente(
        self, id_cliente: str, id_conta: str
    ) -> dict[str, Any]:
        return await self._post(
            "/contas/pagar", {"id_cliente": id_cliente, "id_conta": id_conta}
        )


# ── Implementação in-process ───────────────────────────────────────


class InProcessGatewayClient:
    """Chama as funções do gateway diretamente, sem rede.

    Útil em dev e em testes — atravessa breakpoint, evita overhead.
    Cada chamada abre uma sessão própria via fabrica_sessao().
    """

    async def fechar(self) -> None:
        return None

    async def consultar_cliente(self, id_cliente: str) -> dict[str, Any] | None:
        from assistente_bancario_v2.banking_gateway.app.db.database import fabrica_sessao
        from assistente_bancario_v2.banking_gateway.app.db.repositorio import buscar_cliente

        async with fabrica_sessao() as sessao:
            cliente = await buscar_cliente(sessao, id_cliente)
        if cliente is None:
            return None
        return {
            "id_cliente": cliente.id_cliente,
            "nome": cliente.nome,
            "email": cliente.email,
            "telefone": cliente.telefone,
            "confiavel": cliente.confiavel,
            "ativo": cliente.ativo,
        }

    async def consultar_saldo(self, id_cliente: str) -> dict[str, Any] | None:
        from assistente_bancario_v2.banking_gateway.app.db.database import fabrica_sessao
        from assistente_bancario_v2.banking_gateway.app.db.repositorio import (
            buscar_cliente,
            buscar_saldo,
        )

        async with fabrica_sessao() as sessao:
            cliente = await buscar_cliente(sessao, id_cliente)
            if cliente is None:
                return None
            saldo = await buscar_saldo(sessao, id_cliente)
            if saldo is None:
                return None
            return {
                "id_cliente": saldo.id_cliente,
                "nome": cliente.nome,
                "saldo_disponivel": float(saldo.saldo_disponivel),
                "saldo_bloqueado": float(saldo.saldo_bloqueado),
                "moeda": "BRL",
                "atualizado_em": saldo.atualizado_em.isoformat(),
            }

    async def consultar_contas(
        self,
        id_cliente: str,
        tipo: str,
        data_inicio: date | None = None,
        data_fim: date | None = None,
    ) -> dict[str, Any] | None:
        from assistente_bancario_v2.banking_gateway.app.db.database import fabrica_sessao
        from assistente_bancario_v2.banking_gateway.app.db.repositorio import (
            buscar_cliente,
            listar_contas,
        )

        async with fabrica_sessao() as sessao:
            cliente = await buscar_cliente(sessao, id_cliente)
            if cliente is None:
                return None
            contas = await listar_contas(
                sessao,
                id_cliente=id_cliente,
                tipo=tipo,
                data_inicio=data_inicio,
                data_fim=data_fim,
            )
            # IMPORTANTE: serializar DENTRO do contexto da sessão para evitar
            # MissingGreenlet/DetachedInstanceError nos campos lazy.
            contas_dict = [
                {
                    "id_conta": c.id_conta,
                    "id_cliente": c.id_cliente,
                    "descricao": c.descricao,
                    "valor": float(c.valor),
                    "data_vencimento": c.data_vencimento.isoformat(),
                    "status": c.status,
                    "tipo": c.tipo,
                    "nome_pagador": c.nome_pagador,
                    "data_prevista": c.data_prevista.isoformat() if c.data_prevista else None,
                }
                for c in contas
            ]

        total_valor = sum(c["valor"] for c in contas_dict)  # type: ignore[misc]
        return {
            "contas": contas_dict,
            "total": len(contas_dict),
            "total_valor": float(total_valor),
        }

    async def consultar_limite(self, id_cliente: str) -> dict[str, Any] | None:
        from assistente_bancario_v2.banking_gateway.app.db.database import fabrica_sessao
        from assistente_bancario_v2.banking_gateway.app.db.repositorio import buscar_cliente

        async with fabrica_sessao() as sessao:
            cliente = await buscar_cliente(sessao, id_cliente)
        if cliente is None:
            return None
        return {
            "id_cliente": cliente.id_cliente,
            "nome": cliente.nome,
            "limite_atual": float(cliente.limite_credito),
            "score": cliente.score_credito,
        }

    async def solicitar_aumento_limite(
        self, id_cliente: str, novo_limite: Decimal
    ) -> dict[str, Any]:
        # Implementação completa virá na Fase 6 — placeholder funcional
        from assistente_bancario_v2.banking_gateway.app.services.credito_service import (
            processar_solicitacao_aumento,
        )

        return await processar_solicitacao_aumento(id_cliente, novo_limite)

    async def atualizar_score(
        self,
        id_cliente: str,
        renda: Decimal,
        tipo_emprego: str,
        despesas_mensais: Decimal,
        dependentes: int,
        tem_dividas: str,
    ) -> dict[str, Any]:
        from assistente_bancario_v2.banking_gateway.app.services.credito_service import (
            processar_atualizar_score,
        )

        return await processar_atualizar_score(
            id_cliente=id_cliente,
            renda=renda,
            tipo_emprego=tipo_emprego,
            despesas_mensais=despesas_mensais,
            dependentes=dependentes,
            tem_dividas=tem_dividas,
        )

    async def iniciar_otp(self, id_cliente: str) -> dict[str, Any]:
        from assistente_bancario_v2.banking_gateway.app.services.otp_service import (
            iniciar_otp,
        )

        return await iniciar_otp(id_cliente)

    async def validar_otp(self, id_cliente: str, codigo: str) -> dict[str, Any]:
        from assistente_bancario_v2.banking_gateway.app.services.otp_service import (
            validar_otp,
        )

        return await validar_otp(id_cliente, codigo)

    async def criar_confirmacao(
        self, id_cliente: str, operacao: str, dados_operacao: dict[str, Any]
    ) -> dict[str, Any]:
        from assistente_bancario_v2.banking_gateway.app.services.confirmacao_service import (
            criar_confirmacao,
        )

        return await criar_confirmacao(id_cliente, operacao, dados_operacao)

    async def criar_transacao(self, **kwargs: Any) -> dict[str, Any]:
        from assistente_bancario_v2.banking_gateway.app.services.transacao_service import (
            criar_transacao,
        )

        return await criar_transacao(**kwargs)

    async def pagar_conta_existente(
        self, id_cliente: str, id_conta: str
    ) -> dict[str, Any]:
        from assistente_bancario_v2.banking_gateway.app.services.pagamento_service import (
            iniciar_pagamento_conta,
        )

        return await iniciar_pagamento_conta(id_cliente, id_conta)


# ── Factory ────────────────────────────────────────────────────────


_singleton: GatewayClient | None = None


def obter_gateway_client() -> GatewayClient:
    """Retorna o gateway client global, criando-o conforme `gateway_transport`."""
    global _singleton
    if _singleton is None:
        if configuracao_bot.gateway_transport == "http":
            _singleton = HttpGatewayClient()
        else:
            _singleton = InProcessGatewayClient()
    return _singleton


def resetar_gateway_client() -> None:
    """Reset do singleton (usado em testes)."""
    global _singleton
    _singleton = None
