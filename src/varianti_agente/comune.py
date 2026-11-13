"""Piccole funzioni comuni agli script delle varianti dell'agente."""
import duckdb
import pandas as pd

from src.config import DAILY


def giorni_di_borsa() -> pd.DatetimeIndex:
    """Tutti i giorni di borsa dei prezzi giornalieri (dal 2006): serve per trovare il giorno di borsa prima di un segnale.
    Contiene anche giorni di test, ma gli script lo usano solo per guardare indietro dal segnale."""
    d = duckdb.sql(f"SELECT DISTINCT date FROM '{DAILY.as_posix()}' ORDER BY date").df()
    return pd.DatetimeIndex(pd.to_datetime(d.date))
