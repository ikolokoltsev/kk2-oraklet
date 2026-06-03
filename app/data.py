import logging
import pandas as pd

logger = logging.getLogger(__name__)

_store: pd.DataFrame | None = None

def set_dataset(df: pd.DataFrame) -> None:
    global _store
    _store = df
    logger.info("Dataset stored: %d rows, %d columns", len(df), len(df.columns)),

def get_dataset() -> pd.DataFrame | None:
    return _store

def get_stats():
    return _store.describe(include="all").fillna("").to_dict()