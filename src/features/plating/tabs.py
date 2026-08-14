from __future__ import annotations

import hashlib

import pandas as pd
import streamlit as st

from src.shared.data_access import load_plating_prices, load_plating_suppliers
from src.shared.formatters import currency_br, dataframe_for_export
from src.features.plating.dialogs import plating_price_form_dialog, supplier_form_dialog
from src.features.plating.filters import apply_supplier_filters
from src.features.plating.service import DATE_COLUMNS

def render_plating_prices_tab(
    prices_dataframe: pd.DataFrame,
    suppliers_dataframe: pd.DataFrame,
) -> None:
    st.markdown("### Preços e classificações")

    st.caption(
        "Valores por grama organizados por fornecedor, "
        "metal e classificação."
    )

    success_message = st.session_state.pop(
        "plating_prices_message",
        None,
    )

    if success_message:
        st.success(
            success_message,
            icon="✅",
        )

    has_suppliers = not suppliers_dataframe.empty

    if prices_dataframe.empty:
        create_column, refresh_column, empty_column = (
            st.columns([0.20, 0.18, 0.62])
        )

        with create_column:
            create_clicked = st.button(
                "Novo preço",
                icon=":material/add_circle:",
                type="primary",
                width="stretch",
                disabled=not has_suppliers,
                key="create_plating_price_empty",
            )

        with refresh_column:
            refresh_clicked = st.button(
                "Atualizar dados",
                icon=":material/refresh:",
                width="stretch",
                key="refresh_plating_prices_empty",
            )

        if refresh_clicked:
            load_plating_prices.clear()
            load_plating_suppliers.clear()

            st.session_state[
                "plating_prices_table_version"
            ] += 1

            st.rerun()

        if create_clicked:
            plating_price_form_dialog(
                mode="create",
                suppliers_dataframe=suppliers_dataframe,
                prices_dataframe=prices_dataframe,
            )

        if not has_suppliers:
            st.warning(
                "Cadastre pelo menos um fornecedor antes "
                "de adicionar preços.",
                icon="⚠️",
            )
        else:
            st.info(
                "Nenhum preço foi cadastrado ainda.",
                icon="ℹ️",
            )

        return

    supplier_names = (
        suppliers_dataframe[
            [
                "id_supplier",
                "supplier_name",
            ]
        ]
        .drop_duplicates(
            subset=["id_supplier"]
        )
    )

    display_dataframe = (
        prices_dataframe
        .merge(
            supplier_names,
            how="left",
            on="id_supplier",
            validate="many_to_one",
        )
        .reset_index(drop=True)
    )

    display_dataframe["supplier_name"] = (
        display_dataframe["supplier_name"]
        .fillna("Fornecedor não encontrado")
    )

    st.markdown(
        (
            '<div class="filter-result">'
            f"Exibindo <strong>{len(display_dataframe)}</strong> "
            "preços cadastrados."
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    action_placeholder = st.empty()

    st.caption(
        "Selecione uma linha para editar o preço."
    )

    signature_source = "|".join(
        display_dataframe.apply(
            lambda row: (
                f"{row['id_supplier']}|"
                f"{row['plating_metal']}|"
                f"{row['plating_classification']}"
            ),
            axis=1,
        )
    )

    table_signature = hashlib.md5(
        signature_source.encode("utf-8")
    ).hexdigest()[:10]

    table_key = (
        "plating_prices_table_"
        f"{st.session_state['plating_prices_table_version']}_"
        f"{table_signature}"
    )

    table_event = st.dataframe(
        display_dataframe,
        key=table_key,
        width="stretch",
        height=500,
        hide_index=True,
        placeholder="—",
        column_order=[
            "supplier_name",
            "id_supplier",
            "plating_metal",
            "plating_classification",
            "plating_cost",
        ],
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "supplier_name": st.column_config.TextColumn(
                "Fornecedor",
                width="large",
            ),
            "id_supplier": st.column_config.TextColumn(
                "Código",
                width="medium",
            ),
            "plating_metal": st.column_config.TextColumn(
                "Metal do banho",
                width="medium",
            ),
            "plating_classification": (
                st.column_config.NumberColumn(
                    "Classificação",
                    format="%d",
                    width="medium",
                )
            ),
            "plating_cost": (
                st.column_config.NumberColumn(
                    "Preço por grama",
                    format="R$ %.2f",
                    width="medium",
                )
            ),
        },
    )

    # ========================================================
    # Recupera a linha selecionada
    # ========================================================

    selected_price: dict | None = None
    selected_rows = table_event.selection.rows

    if selected_rows:
        selected_position = selected_rows[0]

        if selected_position < len(display_dataframe):
            selected_price = (
                display_dataframe
                .iloc[selected_position]
                .to_dict()
            )

    # ========================================================
    # Barra de ações
    # ========================================================

    with action_placeholder.container():
        (
            create_column,
            edit_column,
            refresh_column,
            selected_column,
        ) = st.columns([0.20, 0.20, 0.18, 0.42])

        with create_column:
            create_clicked = st.button(
                "Novo preço",
                icon=":material/add_circle:",
                type="primary",
                width="stretch",
                disabled=not has_suppliers,
                key="create_plating_price",
            )

        with edit_column:
            edit_clicked = st.button(
                "Editar preço",
                icon=":material/edit:",
                width="stretch",
                disabled=selected_price is None,
                key="edit_plating_price",
            )

        with refresh_column:
            refresh_clicked = st.button(
                "Atualizar dados",
                icon=":material/refresh:",
                width="stretch",
                key="refresh_plating_prices",
            )

        with selected_column:
            if selected_price:
                selected_supplier_name = str(
                    selected_price.get(
                        "supplier_name",
                        "",
                    )
                )

                selected_metal = str(
                    selected_price.get(
                        "plating_metal",
                        "",
                    )
                )

                selected_classification = int(
                    selected_price.get(
                        "plating_classification",
                        0,
                    )
                )

                selected_cost = float(
                    selected_price.get(
                        "plating_cost",
                        0,
                    )
                )

                st.markdown(
                    (
                        f"**Selecionado:** "
                        f"{selected_supplier_name}  \n"
                        f"{selected_metal} · "
                        f"Classe {selected_classification} · "
                        f"{currency_br(selected_cost)}/g"
                    )
                )
            else:
                st.caption(
                    "Selecione uma linha para habilitar a edição."
                )

    if refresh_clicked:
        load_plating_prices.clear()
        load_plating_suppliers.clear()

        st.session_state[
            "plating_prices_table_version"
        ] += 1

        st.rerun()

    if create_clicked:
        plating_price_form_dialog(
            mode="create",
            suppliers_dataframe=suppliers_dataframe,
            prices_dataframe=prices_dataframe,
        )

    elif edit_clicked and selected_price:
        plating_price_form_dialog(
            mode="edit",
            suppliers_dataframe=suppliers_dataframe,
            prices_dataframe=prices_dataframe,
            price=selected_price,
        )

    csv_data = display_dataframe.to_csv(
        index=False,
        sep=";",
        decimal=",",
    ).encode("utf-8-sig")

    download_column, empty_column = st.columns(
        [0.28, 0.72]
    )

    with download_column:
        st.download_button(
            "Baixar preços em CSV",
            data=csv_data,
            file_name="precos_banho_wisecontrol.csv",
            mime="text/csv",
            icon=":material/download:",
            width="stretch",
            key="download_plating_prices",
        )


def render_suppliers_tab(
    suppliers_dataframe: pd.DataFrame,
) -> None:
    st.markdown("### Fornecedores")

    st.caption(
        "Empresas responsáveis pelo banho das peças."
    )

    success_message = st.session_state.pop(
        "plating_suppliers_message",
        None,
    )

    if success_message:
        st.success(
            success_message,
            icon="✅",
        )

    # ========================================================
    # Estado sem fornecedores
    # ========================================================

    if suppliers_dataframe.empty:
        (
            create_column,
            refresh_column,
            empty_column,
        ) = st.columns([0.22, 0.18, 0.60])

        with create_column:
            create_clicked = st.button(
                "Novo fornecedor",
                icon=":material/add_business:",
                type="primary",
                width="stretch",
                key="supplier_tab_create_empty",
            )

        with refresh_column:
            refresh_clicked = st.button(
                "Atualizar dados",
                icon=":material/refresh:",
                width="stretch",
                key="supplier_tab_refresh_empty",
            )

        if refresh_clicked:
            load_plating_suppliers.clear()

            st.session_state[
                "plating_suppliers_table_version"
            ] += 1

            st.rerun()

        if create_clicked:
            supplier_form_dialog(
                mode="create",
            )

        st.info(
            "Nenhum fornecedor foi cadastrado ainda.",
            icon="ℹ️",
        )

        return

    # ========================================================
    # Filtros
    # ========================================================

    filtered_dataframe = apply_supplier_filters(
        suppliers_dataframe
    )

    st.markdown(
        (
            '<div class="filter-result">'
            f"Exibindo <strong>{len(filtered_dataframe)}</strong> "
            f"de <strong>{len(suppliers_dataframe)}</strong> "
            "fornecedores cadastrados."
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    # ========================================================
    # Nenhum resultado após os filtros
    # ========================================================

    if filtered_dataframe.empty:
        (
            create_column,
            refresh_column,
            empty_column,
        ) = st.columns([0.22, 0.18, 0.60])

        with create_column:
            create_clicked = st.button(
                "Novo fornecedor",
                icon=":material/add_business:",
                type="primary",
                width="stretch",
                key="supplier_tab_create_empty_filter",
            )

        with refresh_column:
            refresh_clicked = st.button(
                "Atualizar dados",
                icon=":material/refresh:",
                width="stretch",
                key="supplier_tab_refresh_empty_filter",
            )

        if refresh_clicked:
            load_plating_suppliers.clear()

            st.session_state[
                "plating_suppliers_table_version"
            ] += 1

            st.rerun()

        if create_clicked:
            supplier_form_dialog(
                mode="create",
            )

        st.warning(
            "Nenhum fornecedor corresponde aos filtros selecionados.",
            icon="⚠️",
        )

        return

    # ========================================================
    # Preparação da tabela
    # ========================================================

    display_dataframe = filtered_dataframe.copy()

    for column in DATE_COLUMNS:
        display_dataframe[column] = (
            display_dataframe[column]
            .dt.tz_localize(None)
        )

    column_order = [
        "id_supplier",
        "supplier_number",
        "supplier_name",
        "supplier_contact",
        "notes",
        "updated_date",
        "insert_date",
    ]

    action_placeholder = st.empty()

    st.caption(
        "Selecione uma linha para editar o fornecedor."
    )

    supplier_ids = "|".join(
        filtered_dataframe["id_supplier"].astype(str)
    )

    table_signature = hashlib.md5(
        supplier_ids.encode("utf-8")
    ).hexdigest()[:10]

    table_key = (
        "plating_suppliers_table_"
        f"{st.session_state['plating_suppliers_table_version']}_"
        f"{table_signature}"
    )

    table_event = st.dataframe(
        display_dataframe,
        key=table_key,
        width="stretch",
        height=500,
        hide_index=True,
        placeholder="—",
        column_order=column_order,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "supplier_number": st.column_config.NumberColumn(
                "Número",
                help="Número sequencial interno.",
                format="%d",
                width="small",
            ),
            "id_supplier": st.column_config.TextColumn(
                "Código",
                help="Identificador do fornecedor.",
                width="medium",
            ),
            "supplier_name": st.column_config.TextColumn(
                "Fornecedor",
                width="large",
            ),
            "supplier_contact": st.column_config.TextColumn(
                "Contato",
                width="medium",
            ),
            "notes": st.column_config.TextColumn(
                "Observações",
                width="large",
            ),
            "insert_date": st.column_config.DatetimeColumn(
                "Data de cadastro",
                format="DD/MM/YYYY HH:mm",
                width="medium",
            ),
            "updated_date": st.column_config.DatetimeColumn(
                "Última atualização",
                format="DD/MM/YYYY HH:mm",
                width="medium",
            ),
        },
    )

    # ========================================================
    # Linha selecionada
    # ========================================================

    selected_rows = table_event.selection.rows
    selected_supplier: dict | None = None

    if selected_rows:
        selected_position = selected_rows[0]

        if selected_position < len(filtered_dataframe):
            selected_supplier = (
                filtered_dataframe
                .iloc[selected_position]
                .to_dict()
            )

    # ========================================================
    # Barra de ações
    # ========================================================

    with action_placeholder.container():
        (
            create_column,
            edit_column,
            refresh_column,
            selected_column,
        ) = st.columns([0.20, 0.20, 0.18, 0.42])

        with create_column:
            create_clicked = st.button(
                "Novo fornecedor",
                icon=":material/add_business:",
                type="primary",
                width="stretch",
                key="supplier_tab_create",
            )

        with edit_column:
            edit_clicked = st.button(
                "Editar fornecedor",
                icon=":material/edit:",
                width="stretch",
                disabled=selected_supplier is None,
                key="supplier_tab_edit",
            )

        with refresh_column:
            refresh_clicked = st.button(
                "Atualizar dados",
                icon=":material/refresh:",
                width="stretch",
                key="supplier_tab_refresh",
            )

        with selected_column:
            if selected_supplier:
                selected_name = str(
                    selected_supplier.get(
                        "supplier_name",
                        "",
                    )
                )

                selected_id = str(
                    selected_supplier.get(
                        "id_supplier",
                        "",
                    )
                )

                st.markdown(
                    (
                        f"**Selecionado:** {selected_name}  \n"
                        f"Código: `{selected_id}`"
                    )
                )

            else:
                st.caption(
                    "Selecione uma linha para habilitar a edição."
                )

    if refresh_clicked:
        load_plating_suppliers.clear()

        st.session_state[
            "plating_suppliers_table_version"
        ] += 1

        st.rerun()

    if create_clicked:
        supplier_form_dialog(
            mode="create",
        )

    elif edit_clicked and selected_supplier:
        supplier_form_dialog(
            mode="edit",
            supplier=selected_supplier,
        )

    # ========================================================
    # Exportação
    # ========================================================

    csv_data = dataframe_for_export(
        filtered_dataframe
    ).to_csv(
        index=False,
        sep=";",
        decimal=",",
    ).encode("utf-8-sig")

    download_column, empty_column = st.columns(
        [0.28, 0.72]
    )

    with download_column:
        st.download_button(
            "Baixar fornecedores em CSV",
            data=csv_data,
            file_name="fornecedores_wisecontrol.csv",
            mime="text/csv",
            icon=":material/download:",
            width="stretch",
            key="supplier_tab_download",
        )
