"""Serviços de acesso aos dados em CSV para o Banco Ágil."""

from __future__ import annotations

import datetime as _dt
import fcntl
import os
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_DATA_DIR = Path(os.getenv("AGNO_DATA_DIR", str(_DEFAULT_DATA_DIR)))
_DATA_DIR.mkdir(parents=True, exist_ok=True)
_CLIENTES_CSV = _DATA_DIR / "clientes.csv"
_SOLICITACOES_CSV = _DATA_DIR / "solicitacoes_aumento_limite.csv"
_SCORES_CSV = _DATA_DIR / "score_credito_base.csv"
_LOCK_DIR = _DATA_DIR / ".locks"
_LOCK_DIR.mkdir(parents=True, exist_ok=True)

_CLIENTES_COLS = [
    "cpf",
    "nome",
    "dt_nascimento",
    "score_credito",
    "renda_mensal",
    "limite_credito",
]
_SOLICITACOES_COLS = [
    "cpf_cliente",
    "data_hora_solicitacao",
    "limite_atual",
    "novo_limite_solicitado",
    "status_pedido",
]


def _ensure_csv(path: Path, columns: list[str]) -> None:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(columns=columns).to_csv(path, index=False)


for _csv_path, _cols in (
    (_CLIENTES_CSV, _CLIENTES_COLS),
    (_SOLICITACOES_CSV, _SOLICITACOES_COLS),
    (_SCORES_CSV, ["score_min", "score_max", "limite_maximo"]),
):
    _ensure_csv(_csv_path, _cols)


@contextmanager
def _locked_csv(path: Path):
    lock_path = _LOCK_DIR / f"{path.name}.lock"
    lock_path.touch(exist_ok=True)
    with open(lock_path, "r+") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)


def limpar_cpf(cpf: str) -> str:
    return re.sub(r"\D", "", str(cpf))


def normalizar_data(data_str: str) -> str:
    try:
        data_str = str(data_str).strip()
        dt = pd.to_datetime(data_str, dayfirst=True, errors="coerce")
        if pd.notna(dt):
            return dt.strftime("%Y-%m-%d")
        return data_str
    except Exception:
        return str(data_str)


def _carregar_clientes() -> pd.DataFrame:
    return pd.read_csv(_CLIENTES_CSV, dtype=str)


def buscar_cliente_por_cpf(cpf: str) -> Optional[Dict[str, Any]]:
    cpf_limpo = limpar_cpf(cpf)
    df_clientes = _carregar_clientes()
    cliente = df_clientes[df_clientes["cpf"] == cpf_limpo]
    if cliente.empty:
        return None

    row = cliente.iloc[0]
    try:
        score = float(row["score_credito"])
    except (TypeError, ValueError):
        score = None
    try:
        renda = float(row["renda_mensal"])
    except (TypeError, ValueError):
        renda = None
    try:
        limite = float(row["limite_credito"])
    except (TypeError, ValueError):
        limite = None

    return {
        "cpf": row["cpf"],
        "nome": str(row["nome"]).strip(),
        "dt_nascimento": row["dt_nascimento"],
        "score_credito": score,
        "renda_mensal": renda,
        "limite_credito": limite,
    }


def atualizar_limite_cliente(cpf: str, novo_limite: float) -> None:
    cpf_limpo = limpar_cpf(cpf)
    with _locked_csv(_CLIENTES_CSV):
        df_clientes = _carregar_clientes()
        mask = df_clientes["cpf"] == cpf_limpo
        if not mask.any():
            raise ValueError("Cliente não encontrado para atualização de limite.")
        df_clientes.loc[mask, "limite_credito"] = f"{float(novo_limite):.2f}"
        df_clientes.to_csv(_CLIENTES_CSV, index=False)


def atualizar_score_cliente(cpf: str, novo_score: int) -> None:
    cpf_limpo = limpar_cpf(cpf)
    with _locked_csv(_CLIENTES_CSV):
        df_clientes = _carregar_clientes()
        mask = df_clientes["cpf"] == cpf_limpo
        if not mask.any():
            raise ValueError("Cliente não encontrado para atualização de score.")
        df_clientes.loc[mask, "score_credito"] = str(int(novo_score))
        df_clientes.to_csv(_CLIENTES_CSV, index=False)


def registrar_solicitacao_limite(
    cpf: str,
    limite_atual: float,
    novo_limite: float,
    status: str,
) -> None:
    registro = {
        "cpf_cliente": limpar_cpf(cpf),
        "data_hora_solicitacao": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "limite_atual": float(limite_atual),
        "novo_limite_solicitado": float(novo_limite),
        "status_pedido": status,
    }
    with _locked_csv(_SOLICITACOES_CSV):
        df_solicitacoes = pd.read_csv(_SOLICITACOES_CSV)
        novo_registro = pd.DataFrame([registro])
        # Garantir que as colunas tenham os mesmos tipos antes do concat
        if df_solicitacoes.empty:
            df_solicitacoes = novo_registro
        else:
            df_solicitacoes = pd.concat(
                [df_solicitacoes, novo_registro], ignore_index=True
            )
        df_solicitacoes.to_csv(_SOLICITACOES_CSV, index=False)


def obter_limite_permitido_por_score(score: float) -> Optional[float]:
    if score is None:
        return None
    df_scores = pd.read_csv(_SCORES_CSV)
    for _, row in df_scores.iterrows():
        try:
            score_min = float(row["score_min"])
            score_max = float(row["score_max"])
            limite = float(row["limite_maximo"])
        except (TypeError, ValueError):
            continue
        if score_min <= score <= score_max:
            return limite
    return None
