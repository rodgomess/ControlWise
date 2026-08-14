from __future__ import annotations

import hashlib
import time

import streamlit as st

from ui.styles import render_page_hero
from src.shared.data_access import (
    get_supabase_client, load_plating_prices, load_plating_suppliers,
    load_product_image_urls, load_products,
)
from src.shared.formatters import currency_br, dataframe_for_export, integer_value, text_value
from src.features.products.filters import apply_filters
from src.features.products.images import add_product_image_urls, renew_product_image_cache
from src.features.products.service import (
    DATE_COLUMNS, build_plating_price_updates, enrich_products_with_plating_costs,
    prepare_plating_prices_dataframe, prepare_plating_suppliers_dataframe,
    prepare_products_dataframe,
)
from src.features.products.dialogs import product_form_dialog, product_image_dialog

if "catalog_table_version" not in st.session_state:
    st.session_state["catalog_table_version"] = 0
if "product_image_cache_token" not in st.session_state:
    st.session_state["product_image_cache_token"] = time.time_ns()

supabase = get_supabase_client()


# Página


render_page_hero(
    eyebrow="CATÁLOGO · VISÃO GERAL",
    title="Catálogo de produtos",
    description=(
        "Consulte, filtre, cadastre e edite os produtos do estoque "
        "em uma única página."
    ),
)

update_message = st.session_state.pop(
    "catalog_update_message",
    None,
)
update_message_level = st.session_state.pop(
    "catalog_update_message_level",
    "success",
)

if update_message:
    if update_message_level == "warning":
        st.warning(update_message, icon="⚠️")
    else:
        st.success(update_message, icon="✅")

try:
    with st.spinner(
        "Carregando produtos, fornecedores e preços de banho..."
    ):
        products = load_products()
        plating_suppliers = load_plating_suppliers()
        plating_prices = load_plating_prices()

except Exception as error:
    st.error(
        "Não foi possível carregar os dados do Supabase. "
        "Verifique a conexão e tente novamente."
    )

    with st.expander("Detalhes técnicos"):
        st.exception(error)

    st.stop()



# Estado sem produtos


if not products:
    create_column, refresh_column, empty_column = st.columns(
        [0.20, 0.18, 0.62]
    )

    with create_column:
        create_clicked = st.button(
            "Novo produto",
            icon=":material/add_circle:",
            type="primary",
            width="stretch",
        )

    with refresh_column:
        refresh_clicked = st.button(
            "Atualizar dados",
            icon=":material/refresh:",
            width="stretch",
        )

    if refresh_clicked:
        st.cache_data.clear()
        st.rerun()

    if create_clicked:
        product_form_dialog(mode="create")

    st.info(
        "Nenhum produto foi encontrado. Cadastre a primeira peça.",
        icon="ℹ️",
    )
    st.stop()


try:
    products_dataframe = prepare_products_dataframe(products)
    plating_suppliers_dataframe = (
        prepare_plating_suppliers_dataframe(
            plating_suppliers
        )
    )
    plating_prices_dataframe = (
        prepare_plating_prices_dataframe(
            plating_prices
        )
    )

    products_dataframe = enrich_products_with_plating_costs(
        products_dataframe,
        plating_suppliers_dataframe,
        plating_prices_dataframe,
    )

    plating_updates = build_plating_price_updates(
        products_dataframe
    )

    if plating_updates:
        supabase.update_list_products(plating_updates)
        load_products.clear()

except Exception as error:
    st.error(
        "Não foi possível calcular os custos de banho dos produtos."
    )

    with st.expander("Detalhes técnicos"):
        st.exception(error)

    st.stop()

missing_price_match = products_dataframe[
    products_dataframe["id_supplier_plating"].ne("")
    & products_dataframe["plating_metal"].ne("")
    & ~products_dataframe["has_plating_match"]
]

if not missing_price_match.empty:
    st.warning(
        (
            f"{len(missing_price_match)} produto(s) não encontraram "
            "preço para a combinação de fornecedor, metal e "
            "classificação."
        ),
        icon="⚠️",
    )

products_dataframe = products_dataframe.drop(
    columns=[
        "_plating_metal_key",
        "_stored_plating_price",
        "_stored_plating_company_name",
        "matched_plating_company_name",
        "calculated_plating_price",
    ],
    errors="ignore",
)

filtered_dataframe = apply_filters(products_dataframe)


# Métricas

total_products = len(filtered_dataframe)
total_amount = int(filtered_dataframe["amount"].sum())

total_cost = (
    (
        filtered_dataframe["purchase_price"]
        + filtered_dataframe["plating_price"]
    )
    * filtered_dataframe["amount"]
).sum()

total_sales_value = (
    filtered_dataframe["selling_price"]
    * filtered_dataframe["amount"]
).sum()

total_profit = (
    filtered_dataframe["profit"]
    * filtered_dataframe["amount"]
).sum()

(
    metric_product,
    metric_amount,
    metric_cost,
    metric_sales,
    metric_profit,
) = st.columns(5)

with metric_product:
    st.metric(
        "Produtos encontrados",
        f"{total_products:,}".replace(",", "."),
    )

with metric_amount:
    st.metric(
        "Unidades em estoque",
        f"{total_amount:,}".replace(",", "."),
    )

with metric_cost:
    st.metric(
        "Custo somado",
        currency_br(float(total_cost)),
    )

with metric_sales:
    st.metric(
        "Valor de venda somado",
        currency_br(float(total_sales_value)),
    )

with metric_profit:
    st.metric(
        "Lucro somado",
        currency_br(float(total_profit)),
    )

st.markdown(
    (
        '<div class="filter-result">'
        f"Exibindo <strong>{len(filtered_dataframe)}</strong> de "
        f"<strong>{len(products_dataframe)}</strong> produtos cadastrados."
        "</div>"
    ),
    unsafe_allow_html=True,
)

# Resultado vazio dos filtros
if filtered_dataframe.empty:
    create_column, refresh_column, empty_column = st.columns(
        [0.20, 0.18, 0.62]
    )

    with create_column:
        create_clicked = st.button(
            "Novo produto",
            icon=":material/add_circle:",
            type="primary",
            width="stretch",
            key="create_product_empty_result",
        )

    with refresh_column:
        refresh_clicked = st.button(
            "Atualizar dados",
            icon=":material/refresh:",
            width="stretch",
            key="refresh_product_empty_result",
        )

    if refresh_clicked:
        st.cache_data.clear()
        st.rerun()

    if create_clicked:
        product_form_dialog(mode="create")

    st.warning(
        "Nenhum produto corresponde aos filtros selecionados.",
        icon="⚠️",
    )
    st.stop()



# Tabela
filtered_dataframe = add_product_image_urls(
    filtered_dataframe
)

display_dataframe = filtered_dataframe.copy()

for column in DATE_COLUMNS:
    display_dataframe[column] = (
        display_dataframe[column].dt.tz_localize(None)
    )

column_order = [
    "thumbnail_url_image",
    "name",
    "category",
    "target_gender",
    "supplier_product_id",
    "amount",
    "weight",
    "base_metal",
    "selling_price",
    "profit",
    "purchase_price",
    "plating_company_name",
    "id_supplier_plating",
    "plating_metal",
    "plating_classification",
    "plating_cost_per_gram",
    "plating_price",
    "supplier_name",
    "supplier_contact",
    "insert_date",
    "updated_date",
    "id",
]

action_placeholder = st.empty()

st.caption(
    "Selecione uma linha da tabela para editar o produto."
)

product_ids = "|".join(
    filtered_dataframe["id"].astype(str)
)

table_signature = hashlib.md5(
    product_ids.encode("utf-8")
).hexdigest()[:10]

image_cache_token = st.session_state[
    "product_image_cache_token"
]

table_key = (
    "product_catalog_table_"
    f"{st.session_state['catalog_table_version']}_"
    f"{image_cache_token}_"
    f"{table_signature}"
)

table_event = st.dataframe(
    display_dataframe,
    key=table_key,
    width="stretch",
    hide_index=True,
    height=540,
    column_order=column_order,
    on_select="rerun",
    selection_mode="single-row",
    column_config={
        "thumbnail_url_image": st.column_config.ImageColumn(
            "Foto",
            help=(
                "Miniatura do produto. Dê duplo clique para ampliar "
                "ou selecione a linha e use o botão Ver foto."
            ),
            width=90,
            pinned=True,
        ),
        "id": st.column_config.TextColumn(
            "ID do produto",
            help="Identificador único do produto no banco.",
            width="medium",
        ),
        "name": st.column_config.TextColumn(
            "Nome da peça",
            width="medium",
            pinned=False,
        ),
        "category": st.column_config.TextColumn(
            "Categoria",
            width="medium",
        ),
        "target_gender": st.column_config.TextColumn(
            "Gênero",
            width="medium",
        ),
        "supplier_product_id": st.column_config.TextColumn(
            "ID do produto do fornecedor",
            width="medium",
        ),
        "amount": st.column_config.NumberColumn(
            "Quantidade",
            help="Quantidade atual disponível em estoque.",
            format="%d",
            width="small",
        ),
        "weight": st.column_config.NumberColumn(
            "Peso",
            help="Peso unitário da peça em gramas.",
            format="%.2f g",
            width="small",
        ),
        "base_metal": st.column_config.TextColumn(
            "Metal base",
            help="Metal da peça base.",
            width="medium",
        ),
        "purchase_price": st.column_config.NumberColumn(
            "Preço de compra",
            format="R$ %.2f",
            width="small",
        ),
        "plating_metal": st.column_config.TextColumn(
            "Metal do banho",
            help="Metal usado no banho da peça.",
            width="medium",
        ),
        "plating_company_name": st.column_config.TextColumn(
            "Empresa do banho",
            help="Empresa responsável por banhar a peça.",
            width="large",
        ),
        "id_supplier_plating": st.column_config.TextColumn(
            "Código do fornecedor do banho",
            width="medium",
        ),
        "plating_cost_per_gram": st.column_config.NumberColumn(
            "Preço do banho por grama",
            format="R$ %.2f",
            width="medium",
        ),
        "plating_price": st.column_config.NumberColumn(
            "Custo do banho",
            format="R$ %.2f",
            width="small",
        ),
        "selling_price": st.column_config.NumberColumn(
            "Preço de venda",
            format="R$ %.2f",
            width="small",
        ),
        "profit": st.column_config.NumberColumn(
            "Lucro",
            format="R$ %.2f",
            width="small",
        ),
        "supplier_name": st.column_config.TextColumn(
            "Fornecedor",
            width="medium",
        ),
        "supplier_contact": st.column_config.TextColumn(
            "Contato fornecedor",
            width="medium",
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
        "plating_classification": st.column_config.NumberColumn(
            "Classificação do banho",
            help="Classificação numérica",
            format="%d",
            width="medium",
        ),
    },
)


# Linha selecionada e barra de ações

selected_rows = table_event.selection.rows
selected_product: dict | None = None

if selected_rows:
    selected_position = selected_rows[0]

    if selected_position < len(filtered_dataframe):
        selected_product = (
            filtered_dataframe
            .iloc[selected_position]
            .to_dict()
        )

with action_placeholder.container():
    (
        create_column,
        edit_column,
        view_image_column,
        refresh_column,
        selected_column,
    ) = st.columns([0.16, 0.16, 0.14, 0.16, 0.38])

    with create_column:
        create_clicked = st.button(
            "Novo produto",
            icon=":material/add_circle:",
            type="primary",
            width="stretch",
        )

    with edit_column:
        edit_clicked = st.button(
            "Editar produto",
            icon=":material/edit:",
            width="stretch",
            disabled=selected_product is None,
        )

    selected_original_url = ""
    selected_thumbnail_url = ""

    if selected_product:
        selected_original_url = text_value(
            selected_product.get("original_url_image")
        ).strip()

        selected_thumbnail_url = text_value(
            selected_product.get("thumbnail_url_image")
        ).strip()

    selected_has_image = bool(
        selected_original_url or selected_thumbnail_url
    )

    with view_image_column:
        view_image_clicked = st.button(
            "Ver foto",
            icon=":material/photo:",
            width="stretch",
            disabled=not selected_has_image,
        )

    with refresh_column:
        refresh_clicked = st.button(
            "Atualizar dados",
            icon=":material/refresh:",
            width="stretch",
        )

    with selected_column:
        if selected_product:
            selected_name = text_value(
                selected_product.get("name")
            )
            selected_id = text_value(
                selected_product.get("id")
            )
            selected_amount = integer_value(
                selected_product.get("amount")
            )

            image_status = (
                "com foto"
                if selected_has_image
                else "sem foto"
            )

            st.markdown(
                (
                    f"**Selecionado:** {selected_name}  \n"
                    f"ID: `{selected_id}` · "
                    f"Estoque: **{selected_amount} unidades** · "
                    f"{image_status}"
                )
            )
        else:
            st.caption(
                "Selecione uma linha para habilitar as ações."
            )

if refresh_clicked:
    load_product_image_urls.clear()
    st.cache_data.clear()

    renew_product_image_cache()

    st.session_state["catalog_table_version"] += 1

    st.rerun()

if create_clicked:
    product_form_dialog(mode="create")

elif edit_clicked and selected_product:
    product_form_dialog(
        mode="edit",
        product=selected_product,
    )

elif (
    view_image_clicked
    and selected_product
    and selected_has_image
):
    product_image_dialog(selected_product)

# Exportação
csv_data = dataframe_for_export(filtered_dataframe).to_csv(
    index=False,
    sep=";",
    decimal=",",
).encode("utf-8-sig")

download_column, spacer_column = st.columns([0.25, 0.75])

with download_column:
    st.download_button(
        "Baixar resultados em CSV",
        data=csv_data,
        file_name="produtos_controlwise.csv",
        mime="text/csv",
        icon=":material/download:",
        width="stretch",
    )
