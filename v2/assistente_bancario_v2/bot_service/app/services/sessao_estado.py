"""Estado de sessão por session_id (em memória) — máquina de estados de autenticação.

Usa `cachetools.TTLCache` para evitar leak de memória: sessões que não foram
tocadas em 1h são automaticamente removidas. Capacidade máxima é 1024 sessões
simultâneas (LRU).

Etapas:
- INICIO: aguardando saudação ou ID
- AGUARDANDO_ID: esperando o cliente enviar o ID
- AGUARDANDO_OTP: OTP enviado, esperando o código
- AUTENTICADO: passou da Triagem, mensagens daqui em diante vão ao Team
"""

from __future__ import annotations

from enum import Enum
from threading import RLock
from typing import Any

from cachetools import TTLCache


class Etapa(str, Enum):
    INICIO = "INICIO"
    AGUARDANDO_ID = "AGUARDANDO_ID"
    AGUARDANDO_OTP = "AGUARDANDO_OTP"
    AUTENTICADO = "AUTENTICADO"


_TTL_SEGUNDOS = 60 * 60       # 1h sem atividade → expira
_CAPACIDADE_MAXIMA = 1024     # max 1024 sessões simultâneas

_lock = RLock()
_estado: TTLCache[str, dict[str, Any]] = TTLCache(
    maxsize=_CAPACIDADE_MAXIMA, ttl=_TTL_SEGUNDOS
)


def _slot(session_id: str) -> dict[str, Any]:
    if session_id not in _estado:
        _estado[session_id] = {
            "etapa": Etapa.INICIO.value,
            "id_cliente": None,
            "nome": None,
            "tentativas_otp": 0,
        }
    return _estado[session_id]


def get(session_id: str) -> dict[str, Any]:
    """Retorna uma cópia do estado da sessão."""
    with _lock:
        return dict(_slot(session_id))


def set_kv(session_id: str, chave: str, valor: Any) -> None:
    """Atualiza uma chave do estado da sessão."""
    with _lock:
        _slot(session_id)[chave] = valor


def set_etapa(session_id: str, etapa: Etapa) -> None:
    """Avança a sessão para uma nova etapa."""
    with _lock:
        _slot(session_id)["etapa"] = etapa.value


def etapa(session_id: str) -> Etapa:
    """Etapa atual da sessão."""
    return Etapa(get(session_id)["etapa"])


def autenticado(session_id: str) -> bool:
    return etapa(session_id) == Etapa.AUTENTICADO


def cliente_id(session_id: str) -> str | None:
    return get(session_id).get("id_cliente")


def nome(session_id: str) -> str | None:
    return get(session_id).get("nome")


def marcar_autenticado(session_id: str, id_cliente: str, nome_cliente: str) -> None:
    """Conclui o login: etapa=AUTENTICADO + grava cliente/nome."""
    with _lock:
        slot = _slot(session_id)
        slot["etapa"] = Etapa.AUTENTICADO.value
        slot["id_cliente"] = id_cliente
        slot["nome"] = nome_cliente
        slot["tentativas_otp"] = 0


def limpar(session_id: str) -> None:
    """Remove a sessão do cache."""
    with _lock:
        _estado.pop(session_id, None)
