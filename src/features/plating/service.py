from __future__ import annotations

import pandas as pd

SUPPLIER_COLUMNS = [
    "id_supplier", "supplier_number", "supplier_name", "supplier_contact",
    "notes", "insert_date", "updated_date",
]
PLATING_PRICE_COLUMNS = ["id_supplier", "plating_metal", "plating_classification", "plating_cost"]
DATE_COLUMNS = ["insert_date", "updated_date"]
EDITABLE_FIELDS = ["supplier_name", "supplier_contact", "notes"]

def prepare_suppliers_dataframe(
    suppliers: list[dict],
) -> pd.DataFrame:
    dataframe = pd.DataFrame(suppliers)

    for column in SUPPLIER_COLUMNS:
        if column not in dataframe.columns:
            dataframe[column] = None

    dataframe = dataframe[SUPPLIER_COLUMNS].copy()

    dataframe["supplier_number"] = pd.to_numeric(
        dataframe["supplier_number"],
        errors="coerce",
    ).astype("Int64")

    for column in DATE_COLUMNS:
        dataframe[column] = pd.to_datetime(
            dataframe[column],
            errors="coerce",
            utc=True,
        ).dt.tz_convert("America/Sao_Paulo")

    text_columns = [
        "id_supplier",
        "supplier_name",
        "supplier_contact",
        "notes",
    ]

    for column in text_columns:
        dataframe[column] = (
            dataframe[column]
            .fillna("")
            .astype(str)
        )

    return dataframe


def prepare_plating_prices_dataframe(
    prices: list[dict],
) -> pd.DataFrame:
    dataframe = pd.DataFrame(prices)

    for column in PLATING_PRICE_COLUMNS:
        if column not in dataframe.columns:
            dataframe[column] = None

    dataframe = dataframe[
        PLATING_PRICE_COLUMNS
    ].copy()

    dataframe["id_supplier"] = (
        dataframe["id_supplier"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    dataframe["plating_metal"] = (
        dataframe["plating_metal"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    dataframe["plating_classification"] = (
        pd.to_numeric(
            dataframe["plating_classification"],
            errors="coerce",
        )
        .astype("Int64")
    )

    dataframe["plating_cost"] = (
        pd.to_numeric(
            dataframe["plating_cost"],
            errors="coerce",
        )
        .fillna(0.0)
    )

    return dataframe


def normalize_supplier_value(
    field: str,
    value,
):
    if value is None or pd.isna(value):
        value = None

    if field in {
        "supplier_name",
        "supplier_contact",
        "notes",
    }:
        normalized_value = str(
            value or ""
        ).strip()

        if (
            field in {"supplier_contact", "notes"}
            and not normalized_value
        ):
            return None

        return normalized_value

    return value


def build_update_payload(
    original_supplier: dict,
    edited_supplier: dict,
) -> dict:
    """
    Retorna somente os campos realmente alterados.

    O id_supplier é enviado separadamente para
    update_suppliers_plating().
    """
    payload: dict = {}

    for field in EDITABLE_FIELDS:
        original_value = normalize_supplier_value(
            field,
            original_supplier.get(field),
        )

        edited_value = normalize_supplier_value(
            field,
            edited_supplier.get(field),
        )

        if original_value != edited_value:
            payload[field] = edited_value

    return payload


def validate_supplier(
    supplier_name: str,
) -> list[str]:
    errors: list[str] = []

    if not supplier_name.strip():
        errors.append(
            "Informe o nome do fornecedor."
        )

    return errors


def validate_plating_price(
    *,
    id_supplier: str,
    plating_metal: str,
    plating_classification: int,
    plating_cost: float,
) -> list[str]:
    errors: list[str] = []

    if not id_supplier:
        errors.append(
            "Selecione o fornecedor."
        )

    if not plating_metal.strip():
        errors.append(
            "Informe o metal do banho."
        )

    if plating_cost < 0:
        errors.append(
            "O preço por grama não pode ser negativo."
        )

    return errors


def normalize_plating_price_value(
    field: str,
    value,
):
    if field in {
        "id_supplier",
        "plating_metal",
    }:
        return str(value or "").strip()

    if field == "plating_classification":
        return int(value or 1)

    if field == "plating_cost":
        return round(float(value or 0), 2)

    return value


def build_plating_price_update_payload(
    original_price: dict,
    edited_price: dict,
) -> dict:
    payload: dict = {}

    fields = [
        "id_supplier",
        "plating_metal",
        "plating_classification",
        "plating_cost",
    ]

    for field in fields:
        original_value = normalize_plating_price_value(
            field,
            original_price.get(field),
        )

        edited_value = normalize_plating_price_value(
            field,
            edited_price.get(field),
        )

        if original_value != edited_value:
            payload[field] = edited_value

    return payload
