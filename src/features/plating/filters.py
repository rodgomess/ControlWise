from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

def apply_supplier_filters(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    filtered = dataframe.copy()

    valid_insert_dates = dataframe[
        "insert_date"
    ].dropna()

    if valid_insert_dates.empty:
        minimum_date = date.today()
        maximum_date = date.today()
    else:
        minimum_date = valid_insert_dates.min().date()
        maximum_date = valid_insert_dates.max().date()

    with st.container(border=True):
        st.markdown(
            """
            <div class="filter-panel-title">
                Filtros de fornecedores
            </div>
            """,
            unsafe_allow_html=True,
        )

        search_column, contact_column = st.columns(2)

        with search_column:
            search_term = st.text_input(
                "Buscar fornecedor",
                placeholder=(
                    "Nome, código, número ou observação"
                ),
                icon=":material/search:",
                key="supplier_filter_search",
            )

        with contact_column:
            contact_filter = st.text_input(
                "Contato",
                placeholder="Telefone, e-mail ou outro contato",
                key="supplier_filter_contact",
            )

        date_column, sort_column, direction_column = (
            st.columns([1.3, 1, 1])
        )

        with date_column:
            selected_dates = st.date_input(
                "Período de cadastro",
                value=(minimum_date, maximum_date),
                min_value=minimum_date,
                max_value=maximum_date,
                format="DD/MM/YYYY",
                key="supplier_filter_dates",
            )

        sort_labels = {
            "supplier_number": "Número interno",
            "id_supplier": "Código do fornecedor",
            "supplier_name": "Nome do fornecedor",
            "insert_date": "Data de cadastro",
            "updated_date": "Última atualização",
        }

        with sort_column:
            sort_column_name = st.selectbox(
                "Ordenar por",
                options=list(sort_labels.keys()),
                index=2,
                format_func=lambda value: sort_labels[value],
                key="supplier_filter_sort",
            )

        with direction_column:
            sort_direction = st.radio(
                "Direção",
                options=[
                    "Crescente",
                    "Decrescente",
                ],
                horizontal=True,
                key="supplier_filter_direction",
            )

    if search_term.strip():
        normalized_search = (
            search_term.strip().casefold()
        )

        search_mask = pd.Series(
            False,
            index=filtered.index,
        )

        for column in [
            "id_supplier",
            "supplier_number",
            "supplier_name",
            "notes",
        ]:
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

    if contact_filter.strip():
        normalized_contact = (
            contact_filter.strip().casefold()
        )

        filtered = filtered[
            filtered["supplier_contact"]
            .astype(str)
            .str.casefold()
            .str.contains(
                normalized_contact,
                regex=False,
                na=False,
            )
        ]

    if (
        isinstance(selected_dates, (tuple, list))
        and len(selected_dates) == 2
    ):
        start_date, end_date = selected_dates

        filtered = filtered[
            filtered["insert_date"]
            .dt.date
            .between(
                start_date,
                end_date,
            )
        ]

    return filtered.sort_values(
        by=sort_column_name,
        ascending=sort_direction == "Crescente",
        na_position="last",
    )
