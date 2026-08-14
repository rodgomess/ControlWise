from __future__ import annotations

import pandas as pd

from src.shared.formatters import (
    float_value, integer_value, is_missing, text_value,
)

CURRENCY_COLUMNS = ["purchase_price", "plating_price", "selling_price", "profit"]
DATE_COLUMNS = ["insert_date", "updated_date"]
EDITABLE_CATEGORIES = ["Anel", "Brinco", "Colar", "Conjunto", "Pingente", "Pulseira", "Tornozeleira", "Outro"]
EXPECTED_COLUMNS = [
    "id", "name", "category", "weight", "base_metal", "target_gender",
    "id_supplier_plating", "plating_company_name", "plating_metal", "amount",
    "purchase_price", "plating_price", "selling_price", "profit",
    "supplier_product_id", "supplier_name", "supplier_contact",
    "insert_date", "updated_date", "plating_classification",
]
PLATING_SUPPLIER_COLUMNS = ["id_supplier", "supplier_name"]
PLATING_PRICE_COLUMNS = ["id_supplier", "plating_metal", "plating_classification", "plating_cost"]
OPTIONAL_TEXT_FIELDS = {
    "base_metal", "target_gender", "id_supplier_plating", "plating_company_name",
    "plating_metal", "supplier_product_id", "supplier_name", "supplier_contact",
}
FLOAT_FIELDS = {"weight", "purchase_price", "plating_price", "selling_price"}
INTEGER_FIELDS = {"amount"}
TEXT_COLUMNS = [
    "id", "name", "category", "base_metal", "target_gender",
    "id_supplier_plating", "plating_company_name", "plating_metal",
    "supplier_product_id", "supplier_name", "supplier_contact",
]

def prepare_products_dataframe(products: list[dict]) -> pd.DataFrame:
    dataframe = pd.DataFrame(products)

    for column in EXPECTED_COLUMNS:
        if column not in dataframe.columns:
            dataframe[column] = None

    dataframe = dataframe[EXPECTED_COLUMNS].copy()

    for column in CURRENCY_COLUMNS:
        dataframe[column] = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        ).fillna(0.0)

    dataframe["weight"] = pd.to_numeric(
        dataframe["weight"],
        errors="coerce",
    ).fillna(0.0)

    dataframe["amount"] = (
        pd.to_numeric(
            dataframe["amount"],
            errors="coerce",
        )
        .fillna(0)
        .astype(int)
    )

    dataframe["plating_classification"] = (
        pd.to_numeric(
            dataframe["plating_classification"],
            errors="coerce",
        )
        .astype("Int64")
    )

    for column in DATE_COLUMNS:
        dataframe[column] = pd.to_datetime(
            dataframe[column],
            errors="coerce",
            utc=True,
        ).dt.tz_convert("America/Sao_Paulo")

    for column in TEXT_COLUMNS:
        dataframe[column] = dataframe[column].fillna("")

    dataframe["category"] = dataframe["category"].replace(
        "",
        "Sem categoria",
    )

    dataframe["supplier_name"] = dataframe["supplier_name"].replace(
        "",
        "Não informado",
    )

    return dataframe


def prepare_plating_suppliers_dataframe(
    suppliers: list[dict],
) -> pd.DataFrame:
    dataframe = pd.DataFrame(suppliers)

    for column in PLATING_SUPPLIER_COLUMNS:
        if column not in dataframe.columns:
            dataframe[column] = None

    dataframe = dataframe[PLATING_SUPPLIER_COLUMNS].copy()

    dataframe["id_supplier"] = (
        dataframe["id_supplier"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    dataframe["supplier_name"] = (
        dataframe["supplier_name"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    return dataframe.drop_duplicates(
        subset=["id_supplier"],
        keep="last",
    )


def prepare_plating_prices_dataframe(
    prices: list[dict],
) -> pd.DataFrame:
    dataframe = pd.DataFrame(prices)

    for column in PLATING_PRICE_COLUMNS:
        if column not in dataframe.columns:
            dataframe[column] = None

    dataframe = dataframe[PLATING_PRICE_COLUMNS].copy()

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

    dataframe["plating_classification"] = pd.to_numeric(
        dataframe["plating_classification"],
        errors="coerce",
    ).astype("Int64")

    dataframe["plating_cost"] = pd.to_numeric(
        dataframe["plating_cost"],
        errors="coerce",
    )

    dataframe["_plating_metal_key"] = (
        dataframe["plating_metal"]
        .str.casefold()
    )

    duplicate_mask = dataframe.duplicated(
        subset=[
            "id_supplier",
            "_plating_metal_key",
            "plating_classification",
        ],
        keep=False,
    )

    if duplicate_mask.any():
        duplicated = dataframe.loc[
            duplicate_mask,
            [
                "id_supplier",
                "plating_metal",
                "plating_classification",
            ],
        ].to_dict(orient="records")

        raise ValueError(
            "Existem preços duplicados para a combinação de "
            "fornecedor, metal e classificação: "
            f"{duplicated}"
        )

    return dataframe


def enrich_products_with_plating_costs(
    products_dataframe: pd.DataFrame,
    suppliers_dataframe: pd.DataFrame,
    prices_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    products = products_dataframe.copy()
    suppliers = suppliers_dataframe.copy()
    prices = prices_dataframe.copy()

    products["id_supplier_plating"] = (
        products["id_supplier_plating"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    products["plating_metal"] = (
        products["plating_metal"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    products["_plating_metal_key"] = (
        products["plating_metal"]
        .str.casefold()
    )

    products["_stored_plating_price"] = products[
        "plating_price"
    ]
    products["_stored_plating_company_name"] = products[
        "plating_company_name"
    ]

    prices = prices.merge(
        suppliers,
        how="left",
        on="id_supplier",
        validate="many_to_one",
    )

    prices = prices.rename(
        columns={
            "id_supplier": "id_supplier_plating",
            "supplier_name": "matched_plating_company_name",
            "plating_cost": "plating_cost_per_gram",
        }
    )

    products = products.merge(
        prices[
            [
                "id_supplier_plating",
                "_plating_metal_key",
                "plating_classification",
                "plating_cost_per_gram",
                "matched_plating_company_name",
            ]
        ],
        how="left",
        on=[
            "id_supplier_plating",
            "_plating_metal_key",
            "plating_classification",
        ],
        validate="many_to_one",
    )

    products["has_plating_match"] = products[
        "plating_cost_per_gram"
    ].notna()

    products["calculated_plating_price"] = (
        products["weight"]
        * products["plating_cost_per_gram"]
    ).round(2)

    match_mask = products["has_plating_match"]

    products.loc[
        match_mask,
        "plating_price",
    ] = products.loc[
        match_mask,
        "calculated_plating_price",
    ]

    products.loc[
        match_mask,
        "plating_company_name",
    ] = products.loc[
        match_mask,
        "matched_plating_company_name",
    ]

    products["profit"] = (
        products["selling_price"]
        - products["purchase_price"]
        - products["plating_price"]
    ).round(2)

    return products


def build_plating_price_updates(
    dataframe: pd.DataFrame,
) -> list[dict]:
    matched = dataframe[
        dataframe["has_plating_match"]
        & dataframe["id"].notna()
    ].copy()

    stored_price = pd.to_numeric(
        matched["_stored_plating_price"],
        errors="coerce",
    )
    calculated_price = pd.to_numeric(
        matched["calculated_plating_price"],
        errors="coerce",
    )

    price_changed = (
        stored_price.isna()
        | stored_price.sub(calculated_price).abs().gt(0.009)
    )

    stored_company = (
        matched["_stored_plating_company_name"]
        .fillna("")
        .astype(str)
        .str.strip()
    )
    matched_company = (
        matched["matched_plating_company_name"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    company_changed = stored_company.ne(matched_company)
    changed = matched[price_changed | company_changed]

    updates: list[dict] = []

    for _, row in changed.iterrows():
        update = {
            "id": str(row["id"]),
            "plating_price": round(
                float(row["calculated_plating_price"]),
                2,
            ),
        }

        company_name = text_value(
            row.get("matched_plating_company_name")
        ).strip()

        if company_name:
            update["plating_company_name"] = company_name

        updates.append(update)

    return updates


def find_plating_price_row(
    prices_dataframe: pd.DataFrame,
    id_supplier: str | None,
    plating_metal: str | None,
    plating_classification: int | None,
) -> pd.DataFrame:
    if (
        not id_supplier
        or not plating_metal
        or plating_classification is None
    ):
        return prices_dataframe.iloc[0:0]

    return prices_dataframe[
        prices_dataframe["id_supplier"].eq(
            str(id_supplier).strip()
        )
        & prices_dataframe["_plating_metal_key"].eq(
            str(plating_metal).strip().casefold()
        )
        & prices_dataframe["plating_classification"].eq(
            int(plating_classification)
        )
    ]


def normalize_product_value(field: str, value):
    if field in OPTIONAL_TEXT_FIELDS:
        normalized_value = text_value(value).strip()

        if normalized_value in {"", "Não informado"}:
            return None

        return normalized_value

    if field == "plating_classification":
        if is_missing(value):
            return None

        return int(value)

    if field in FLOAT_FIELDS:
        return round(float_value(value), 2)
    
    if field in INTEGER_FIELDS:
        return integer_value(value)

    return text_value(value).strip()


def build_update_payload(
    original_product: dict,
    edited_product: dict,
) -> dict:
    """Retorna apenas os campos que realmente foram alterados."""
    payload: dict = {}

    for field, edited_value in edited_product.items():
        original_value = original_product.get(field)

        normalized_original = normalize_product_value(
            field,
            original_value,
        )
        normalized_edited = normalize_product_value(
            field,
            edited_value,
        )

        if normalized_original != normalized_edited:
            payload[field] = normalized_edited

    return payload


def validate_product(
    *,
    name: str,
    category: str | None,
    amount: int,
    weight: float,
    purchase_price: float,
    plating_price: float,
    selling_price: float,
    id_supplier_plating: str | None,
    plating_metal: str | None,
    plating_classification: int | None,
    has_plating_match: bool,
) -> list[str]:
    errors: list[str] = []

    if not name.strip():
        errors.append("Informe o nome do produto.")

    if not category:
        errors.append("Selecione uma categoria.")

    if amount < 0:
        errors.append(
            "A quantidade em estoque não pode ser negativa."
        )

    if weight < 0:
        errors.append(
            "O peso da peça não pode ser negativo."
        )

    if purchase_price < 0:
        errors.append(
            "O preço de compra não pode ser negativo."
        )

    if selling_price <= 0:
        errors.append(
            "O preço de venda deve ser maior que zero."
        )

    plating_fields = [
        bool(id_supplier_plating),
        bool(plating_metal),
        plating_classification is not None,
    ]

    has_any_plating_field = any(plating_fields)
    has_all_plating_fields = all(plating_fields)

    # O banho é opcional, mas não pode ficar parcialmente preenchido.
    if has_any_plating_field and not has_all_plating_fields:
        errors.append(
            "Para informar o banho, selecione fornecedor, "
            "metal e classificação."
        )

    # Só exige correspondência de preço quando o banho foi preenchido.
    if has_all_plating_fields:
        if not 1 <= int(plating_classification):
            errors.append(
                "A classificação do banho deve ser maior que 1"
            )

        if not has_plating_match:
            errors.append(
                "Não existe preço cadastrado para a combinação de "
                "fornecedor, metal e classificação selecionada."
            )

    if plating_price < 0:
        errors.append(
            "O custo do banho não pode ser negativo."
        )

    total_cost = purchase_price + plating_price

    if selling_price < total_cost:
        errors.append(
            "O preço de venda está abaixo do custo total da peça."
        )

    return errors
