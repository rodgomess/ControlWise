from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

def numeric_bounds(
    dataframe: pd.DataFrame,
    column: str,
    *,
    integer: bool = False,
):
    minimum = dataframe[column].min()
    maximum = dataframe[column].max()

    if pd.isna(minimum):
        minimum = 0

    if pd.isna(maximum):
        maximum = 0

    if integer:
        return int(minimum), int(maximum)

    return float(minimum), float(maximum)


def apply_text_filter(
    dataframe: pd.DataFrame,
    column: str,
    value: str,
) -> pd.DataFrame:
    normalized_value = value.strip().casefold()

    if not normalized_value:
        return dataframe

    return dataframe[
        dataframe[column]
        .astype(str)
        .str.casefold()
        .str.contains(
            normalized_value,
            regex=False,
            na=False,
        )
    ]


def apply_filters(dataframe: pd.DataFrame) -> pd.DataFrame:
    filtered = dataframe.copy()

    selling_min_default, selling_max_default = numeric_bounds(
        dataframe,
        "selling_price",
    )
    purchase_min_default, purchase_max_default = numeric_bounds(
        dataframe,
        "purchase_price",
    )
    plating_min_default, plating_max_default = numeric_bounds(
        dataframe,
        "plating_price",
    )
    profit_min_default, profit_max_default = numeric_bounds(
        dataframe,
        "profit",
    )
    amount_min_default, amount_max_default = numeric_bounds(
        dataframe,
        "amount",
        integer=True,
    )
    weight_min_default, weight_max_default = numeric_bounds(
        dataframe,
        "weight",
    )

    valid_insert_dates = dataframe["insert_date"].dropna()

    if valid_insert_dates.empty:
        minimum_date = date.today()
        maximum_date = date.today()
    else:
        minimum_date = valid_insert_dates.min().date()
        maximum_date = valid_insert_dates.max().date()

    with st.container(border=True):
        st.markdown(
            '<div class="filter-panel-title">Filtros do catálogo</div>',
            unsafe_allow_html=True,
        )

        search_column, category_column, gender_column = st.columns(
            [1.4, 1, 1]
        )

        with search_column:
            search_term = st.text_input(
                "Buscar produto, ID ou fornecedor",
                placeholder=(
                    "Nome, ID, fornecedor ou ID externo"
                ),
                icon=":material/search:",
            )

        with category_column:
            category_filter = st.text_input(
                "Categoria",
                placeholder="Ex.: Pulseira",
            )

        with gender_column:
            gender_filter = st.text_input(
                "Gênero / público-alvo",
                placeholder="Ex.: Feminino",
            )

        base_metal_column, plating_metal_column, company_column = (
            st.columns(3)
        )

        with base_metal_column:
            base_metal_filter = st.text_input(
                "Metal base",
                placeholder="Ex.: Latão",
            )

        with plating_metal_column:
            plating_metal_filter = st.text_input(
                "Metal do banho",
                placeholder="Ex.: Ouro 18k",
            )

        with company_column:
            plating_company_filter = st.text_input(
                "Empresa do banho",
                placeholder="Nome da empresa",
            )

        supplier_column, supplier_product_column = st.columns(2)

        with supplier_column:
            supplier_filter = st.text_input(
                "Fornecedor da peça",
                placeholder="Nome do fornecedor",
            )

        with supplier_product_column:
            supplier_product_filter = st.text_input(
                "ID do produto no fornecedor",
                placeholder="Ex.: PL-4587",
            )
        
        with st.expander("Filtros numéricos", expanded=False):
            sale_column, purchase_column, profit_column, amount_column = (
                st.columns(4)
            )
            with sale_column:
                selling_min = st.number_input(
                    "Preço de venda mínimo",
                    min_value=0.00,
                    value=max(selling_min_default, 0.0),
                    step=0.50,
                    format="%.2f",
                )
                selling_max = st.number_input(
                    "Preço de venda máximo",
                    min_value=0.00,
                    value=max(selling_max_default, 0.0),
                    step=0.50,
                    format="%.2f",
                )

            with purchase_column:
                purchase_min = st.number_input(
                    "Preço de compra mínimo",
                    min_value=0.00,
                    value=max(purchase_min_default, 0.0),
                    step=0.50,
                    format="%.2f",
                )
                purchase_max = st.number_input(
                    "Preço de compra máximo",
                    min_value=0.00,
                    value=max(purchase_max_default, 0.0),
                    step=0.50,
                    format="%.2f",
                )

            with profit_column:
                profit_min = st.number_input(
                    "Lucro mínimo",
                    value=float(profit_min_default),
                    step=0.50,
                    format="%.2f",
                )
                profit_max = st.number_input(
                    "Lucro máximo",
                    value=float(profit_max_default),
                    step=0.50,
                    format="%.2f",
                )

            with amount_column:
                amount_min = st.number_input(
                    "Quantidade mínima",
                    min_value=0,
                    value=max(amount_min_default, 0),
                    step=1,
                )
                amount_max = st.number_input(
                    "Quantidade máxima",
                    min_value=0,
                    value=max(amount_max_default, 0),
                    step=1,
                )

            plating_cost_column, weight_column, classification_column = (
                st.columns(3)
            )

            with plating_cost_column:
                plating_cost_min = st.number_input(
                    "Custo do banho mínimo",
                    min_value=0.00,
                    value=max(plating_min_default, 0.0),
                    step=0.50,
                    format="%.2f",
                )
                plating_cost_max = st.number_input(
                    "Custo do banho máximo",
                    min_value=0.00,
                    value=max(plating_max_default, 0.0),
                    step=0.50,
                    format="%.2f",
                )

            with weight_column:
                weight_min = st.number_input(
                    "Peso mínimo (g)",
                    min_value=0.00,
                    value=max(weight_min_default, 0.0),
                    step=0.10,
                    format="%.2f",
                )
                weight_max = st.number_input(
                    "Peso máximo (g)",
                    min_value=0.00,
                    value=max(weight_max_default, 0.0),
                    step=0.10,
                    format="%.2f",
                )

            with classification_column:
                classification_min = st.number_input(
                    "Classificação mínima",
                    min_value=1,
                    max_value=20,
                    value=1,
                    step=1,
                )
                classification_max = st.number_input(
                    "Classificação máxima",
                    min_value=1,
                    max_value=20,
                    value=20,
                    step=1,
                )

        date_column, sort_column, direction_column = st.columns(
            [1.4, 1, 0.8]
        )

        with date_column:
            selected_dates = st.date_input(
                "Período de cadastro",
                value=(minimum_date, maximum_date),
                min_value=minimum_date,
                max_value=maximum_date,
                format="DD/MM/YYYY",
            )

        sort_labels = {
            "insert_date": "Cadastro",
            "updated_date": "Última atualização",
            "name": "Nome da peça",
            "category": "Categoria",
            "target_gender": "Gênero / público-alvo",
            "amount": "Quantidade em estoque",
            "weight": "Peso",
            "selling_price": "Preço de venda",
            "purchase_price": "Preço de compra",
            "plating_price": "Custo do banho",
            "profit": "Lucro",
            "plating_classification": "Classificação do banho",
            "supplier_name": "Fornecedor",
            "plating_company_name": "Empresa do banho",
        }

        with sort_column:
            sort_column_name = st.selectbox(
                "Ordenar por",
                options=list(sort_labels.keys()),
                format_func=lambda value: sort_labels[value],
            )

        with direction_column:
            sort_direction = st.radio(
                "Direção",
                options=["Decrescente", "Crescente"],
                horizontal=True,
            )

    range_checks = [
        (selling_min, selling_max, "preço de venda"),
        (purchase_min, purchase_max, "preço de compra"),
        (plating_cost_min, plating_cost_max, "custo do banho"),
        (profit_min, profit_max, "lucro"),
        (amount_min, amount_max, "quantidade"),
        (weight_min, weight_max, "peso"),
        (
            classification_min,
            classification_max,
            "classificação",
        ),
    ]

    invalid_ranges = [
        label
        for minimum, maximum, label in range_checks
        if minimum > maximum
    ]

    if invalid_ranges:
        st.warning(
            "O valor mínimo não pode ser maior que o máximo em: "
            + ", ".join(invalid_ranges)
            + ".",
            icon="⚠️",
        )
        return filtered.iloc[0:0]

    if search_term.strip():
        normalized_search = search_term.strip().casefold()

        searchable_columns = [
            "id",
            "name",
            "category",
            "supplier_name",
            "supplier_product_id",
        ]

        search_mask = pd.Series(False, index=filtered.index)

        for column in searchable_columns:
            search_mask = (
                search_mask
                | filtered[column]
                .astype(str)
                .str.casefold()
                .str.contains(
                    normalized_search,
                    regex=False,
                    na=False,
                )
            )

        filtered = filtered[search_mask]

    text_filters = {
        "category": category_filter,
        "target_gender": gender_filter,
        "base_metal": base_metal_filter,
        "plating_metal": plating_metal_filter,
        "plating_company_name": plating_company_filter,
        "supplier_name": supplier_filter,
        "supplier_product_id": supplier_product_filter,
    }

    for column, value in text_filters.items():
        filtered = apply_text_filter(
            filtered,
            column,
            value,
        )

    filtered = filtered[
        filtered["selling_price"].between(
            float(selling_min),
            float(selling_max),
        )
        & filtered["purchase_price"].between(
            float(purchase_min),
            float(purchase_max),
        )
        & filtered["plating_price"].between(
            float(plating_cost_min),
            float(plating_cost_max),
        )
        & filtered["profit"].between(
            float(profit_min),
            float(profit_max),
        )
        & filtered["amount"].between(
            int(amount_min),
            int(amount_max),
        )
        & filtered["weight"].between(
            float(weight_min),
            float(weight_max),
        )
        & (
        filtered["plating_classification"].isna()
        | filtered["plating_classification"].between(
            int(classification_min),
            int(classification_max),
        )
)
    ]

    if (
        isinstance(selected_dates, (tuple, list))
        and len(selected_dates) == 2
    ):
        start_date, end_date = selected_dates

        filtered = filtered[
            filtered["insert_date"].dt.date.between(
                start_date,
                end_date,
            )
        ]

    return filtered.sort_values(
        by=sort_column_name,
        ascending=sort_direction == "Crescente",
        na_position="last",
    )
