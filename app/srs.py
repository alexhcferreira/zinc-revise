"""Regras da revisão espaçada (funções puras)."""
from __future__ import annotations

from datetime import date, timedelta

ETAPA_MANUTENCAO = 6


def intervalo(etapa: int, intervalos: list[int], manutencao: int) -> int:
    """Dias até a próxima revisão para um tópico na etapa informada."""
    if etapa >= len(intervalos):
        return manutencao
    return intervalos[etapa]


def proxima_etapa(etapa: int, pct: float, limiar_avancar: int, limiar_repetir: int,
                  max_etapa: int = ETAPA_MANUTENCAO) -> int:
    """>= limiar_avancar avança; entre os limiares repete; abaixo volta para a etapa 0."""
    if pct >= limiar_avancar:
        return min(etapa + 1, max_etapa)
    if pct >= limiar_repetir:
        return etapa
    return 0


def agendar(data_revisao: date, etapa: int, acertos: int, total: int, cfg: dict) -> tuple[int, date]:
    """Retorna (nova_etapa, proxima_data). Intervalos contam da data em que a revisão foi feita."""
    intervalos = cfg["intervalos"]
    max_etapa = len(intervalos)
    pct = 100.0 * acertos / total if total else 0.0
    nova = proxima_etapa(etapa, pct, cfg["limiar_avancar"], cfg["limiar_repetir"], max_etapa)
    dias = intervalo(nova, intervalos, cfg["intervalo_manutencao"])
    return nova, data_revisao + timedelta(days=dias)


def questoes_por_revisao(etapa: int, cfg: dict) -> int:
    return cfg["questoes_primeira"] if etapa == 0 else cfg["questoes_demais"]


def nome_etapa(etapa: int, max_etapa: int = ETAPA_MANUTENCAO) -> str:
    if etapa >= max_etapa:
        return "manutenção"
    return f"etapa {etapa}"
