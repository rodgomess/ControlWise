from __future__ import annotations

import pandas as pd

DATE_COLUMNS = ["insert_date", "updated_date"]

def is_missing(value) -> bool:
    if value is None:
        return True

    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def text_value(value) -> str:
    if is_missing(value):
        return ""

    return str(value)


def integer_value(value, default: int = 0) -> int:
    if is_missing(value):
        return default

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def float_value(value, default: float = 0.0) -> float:
    if is_missing(value):
        return default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def currency_br(
    value: float | None,
) -> str:
    if value is None or is_missing(value):
        return "R$ 0,00"

    return (
        f"R$ {float(value):,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def dataframe_for_export(dataframe: pd.DataFrame) -> pd.DataFrame:
    export_dataframe = dataframe.copy()
    for column in DATE_COLUMNS:
        if column in export_dataframe.columns:
            export_dataframe[column] = export_dataframe[column].dt.strftime("%d/%m/%Y %H:%M:%S")
    return export_dataframe
