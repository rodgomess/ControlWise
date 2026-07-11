from datetime import date
from urllib.parse import urlparse

import pandas as pd
import streamlit as st

from src.services.supabase import SupabaseClient
from ui.styles import render_page_hero


CURRENCY_COLUMNS = [
    "purchase_price",
    "plating_price",
    "selling_price",
    "profit",
]

DATE_COLUMNS = [
    "insert_date",
    "updated_date",
]

EDITABLE_CATEGORIES = [
    "Anel",
    "Brinco",
    "Colar",
    "Conjunto",
    "Pingente",
    "Pulseira",
    "Tornozeleira",
    "Outro",
]

OPTIONAL_TEXT_FIELDS = {
    "supplier_name",
    "supplier_link",
}

FLOAT_FIELDS = {
    "purchase_price",
    "plating_price",
    "selling_price",
}

INTEGER_FIELDS = {
    "amount",
    "plating_classification",
}

if "catalog_table_version" not in st.session_state:
    st.session_state["catalog_table_version"] = 0

@st.cache_resource
def get_supabase_client() -> SupabaseClient:
    return SupabaseClient()


@st.cache_data(ttl=60, show_spinner=False)
def load_products() -> list[dict]:
    client = get_supabase_client()
    return client.load_products() or []

def prepare_products_dataframe(products: list[dict]) -> pd.DataFrame:
    expected_columns = [
        "id",
        "name",
        "category",
        "amount",
        "purchase_price",
        "plating_price",
        "selling_price",
        "profit",
        "supplier_name",
        "supplier_link",
        "insert_date",
        "updated_date",
        "plating_classification",
    ]

    dataframe = pd.DataFrame(products)

    for column in expected_columns:
        if column not in dataframe.columns:
            dataframe[column] = None

    dataframe = dataframe[expected_columns].copy()

    for column in CURRENCY_COLUMNS:
        dataframe[column] = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        ).fillna(0.0)

    dataframe["plating_classification"] = pd.to_numeric(
        dataframe["plating_classification"],
        errors="coerce",
    ).astype("Int64")

    dataframe["amount"] = (
        pd.to_numeric(
            dataframe["amount"],
            errors="coerce",
        )
        .fillna(0)
        .astype(int)
    )

    for column in DATE_COLUMNS:
        dataframe[column] = pd.to_datetime(
            dataframe[column],
            errors="coerce",
            utc=True,
        ).dt.tz_convert("America/Sao_Paulo")

    dataframe["name"] = dataframe["name"].fillna("")
    dataframe["category"] = dataframe["category"].fillna("Sem categoria")
    dataframe["supplier_name"] = dataframe["supplier_name"].fillna(
        "Não informado"
    )
    dataframe["supplier_link"] = dataframe["supplier_link"].fillna("")

    return dataframe


def currency_br(value: float) -> str:
    return (
        f"R$ {value:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def safe_range(
    series: pd.Series,
    *,
    decimals: int = 2,
) -> tuple[float, float]:
    minimum = round(float(series.min()), decimals)
    maximum = round(float(series.max()), decimals)

    if minimum == maximum:
        maximum = round(maximum + 0.01, decimals)

    return minimum, maximum

def is_valid_url(value: str) -> bool:
    """
    Valida URLs opcionais.

    Um campo vazio é considerado válido porque o link do fornecedor
    não é obrigatório.
    """
    if not value:
        return True

    parsed_url = urlparse(value)

    return (
        parsed_url.scheme in {"http", "https"}
        and bool(parsed_url.netloc)
    )


def normalize_product_value(
    field: str,
    value,
):
    """
    Normaliza valores antes da comparação e antes do envio ao banco.
    """

    if field in OPTIONAL_TEXT_FIELDS:
        if value is None:
            return None

        normalized_value = str(value).strip()

        if normalized_value in {"", "Não informado"}:
            return None

        return normalized_value

    if field in FLOAT_FIELDS:
        return round(float(value or 0), 2)

    if field in INTEGER_FIELDS:
        return int(value or 0)

    if value is None:
        return ""

    return str(value).strip()


def build_update_payload(
    original_product: dict,
    edited_product: dict,
) -> dict:
    """
    Cria um payload contendo o ID e somente os campos alterados.
    """

    payload = {
        "id": str(original_product["id"]),
    }

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


def validate_edited_product(
    name: str,
    amount: int,
    purchase_price: float,
    plating_price: float,
    selling_price: float,
    supplier_link: str,
) -> list[str]:
    errors: list[str] = []

    if not name.strip():
        errors.append("Informe o nome do produto.")

    if amount < 0:
        errors.append(
            "A quantidade em estoque não pode ser negativa."
        )

    if purchase_price < 0:
        errors.append(
            "O preço de compra não pode ser negativo."
        )

    if plating_price < 0:
        errors.append(
            "O custo do banho não pode ser negativo."
        )

    if selling_price <= 0:
        errors.append(
            "O preço de venda deve ser maior que zero."
        )

    total_cost = purchase_price + plating_price

    if selling_price < total_cost:
        errors.append(
            "O preço de venda está abaixo do custo total da peça."
        )

    if not is_valid_url(supplier_link.strip()):
        errors.append(
            "O link do fornecedor deve começar com "
            "http:// ou https://."
        )

    return errors

@st.dialog(
    "Editar produto",
    width="medium",
    icon=":material/edit:",
)
def edit_product_dialog(product: dict) -> None:
    product_id = str(product["id"])

    current_name = str(product.get("name") or "")
    current_category = str(
        product.get("category") or "Outro"
    )

    current_amount = int(product.get("amount") or 0)

    current_purchase_price = float(
        product.get("purchase_price") or 0
    )

    current_plating_price = float(
        product.get("plating_price") or 0
    )

    current_selling_price = float(
        product.get("selling_price") or 0
    )

    current_plating_classification = int(
        product.get("plating_classification") or 1
    )

    current_supplier_name = str(
        product.get("supplier_name") or ""
    )

    if current_supplier_name == "Não informado":
        current_supplier_name = ""

    current_supplier_link = str(
        product.get("supplier_link") or ""
    )

    category_options = EDITABLE_CATEGORIES.copy()

    if current_category not in category_options:
        category_options.insert(0, current_category)

    category_index = category_options.index(
        current_category
    )

    st.caption(f"ID do produto: `{product_id}`")

    st.markdown(
        f"""
        **Produto selecionado:** {current_name}

        Altere os campos necessários e confirme para salvar.
        """
    )

    with st.form(
        f"edit_product_form_{product_id}",
    ):
        name = st.text_input(
            "Nome da peça",
            value=current_name,
        )

        category_column, amount_column = st.columns(
            [1.4, 0.6]
        )

        with category_column:
            category = st.selectbox(
                "Categoria",
                options=category_options,
                index=category_index,
            )

        with amount_column:
            amount = st.number_input(
                "Quantidade",
                min_value=0,
                value=current_amount,
                step=1,
            )

        st.divider()

        purchase_column, plating_column, selling_column = (
            st.columns(3)
        )

        with purchase_column:
            purchase_price = st.number_input(
                "Preço de compra",
                min_value=0.00,
                value=current_purchase_price,
                step=0.50,
                format="%.2f",
            )

        with plating_column:
            plating_price = st.number_input(
                "Custo do banho",
                min_value=0.00,
                value=current_plating_price,
                step=0.50,
                format="%.2f",
            )

        with selling_column:
            selling_price = st.number_input(
                "Preço de venda",
                min_value=0.00,
                value=current_selling_price,
                step=0.50,
                format="%.2f",
            )

        total_cost = purchase_price + plating_price
        estimated_profit = selling_price - total_cost

        st.info(
            (
                f"Custo total: {currency_br(total_cost)} · "
                f"Lucro estimado: "
                f"{currency_br(estimated_profit)}"
            ),
            icon="💰",
        )

        st.divider()

        plating_classification = st.slider(
            "Classificação do banho",
            min_value=1,
            max_value=5,
            value=current_plating_classification,
        )

        supplier_name = st.text_input(
            "Nome do fornecedor",
            value=current_supplier_name,
        )

        supplier_link = st.text_input(
            "Link no fornecedor",
            value=current_supplier_link,
            placeholder="https://fornecedor.com/produto",
        )

        submitted = st.form_submit_button(
            "Salvar alterações",
            icon=":material/save:",
            type="primary",
            width="stretch",
        )

    if not submitted:
        return

    validation_errors = validate_edited_product(
        name=name,
        amount=int(amount),
        purchase_price=float(purchase_price),
        plating_price=float(plating_price),
        selling_price=float(selling_price),
        supplier_link=supplier_link,
    )

    if validation_errors:
        for error in validation_errors:
            st.error(error)

        return

    edited_product = {
        "name": name,
        "category": category,
        "amount": int(amount),
        "purchase_price": float(purchase_price),
        "plating_price": float(plating_price),
        "selling_price": float(selling_price),
        "plating_classification": int(
            plating_classification
        ),
        "supplier_name": supplier_name,
        "supplier_link": supplier_link,
    }

    update_payload = build_update_payload(
        original_product=product,
        edited_product=edited_product,
    )

    # Quando há somente o ID, nenhum campo foi alterado.
    if len(update_payload) == 1:
        st.info(
            "Nenhuma alteração foi identificada.",
            icon="ℹ️",
        )
        return

    try:
        with st.spinner("Salvando alterações..."):
            supabase.update_product(update_payload['id'], update_payload)

        st.cache_data.clear()

        st.session_state["catalog_update_message"] = (
            f'Produto "{name.strip()}" atualizado com sucesso.'
        )

        # Troca a chave da tabela e elimina a seleção anterior.
        st.session_state["catalog_table_version"] += 1

        st.rerun(scope="app")

    except Exception as error:
        st.error(
            "Não foi possível atualizar o produto. "
            "Verifique a conexão com o Supabase."
        )

        with st.expander("Detalhes técnicos"):
            st.exception(error)

def apply_filters(dataframe: pd.DataFrame) -> pd.DataFrame:
    filtered = dataframe.copy()

    with st.container(border=True):
        st.markdown(
            '<div class="filter-panel-title">Filtros do catálogo</div>',
            unsafe_allow_html=True,
        )

        search_column, category_column, rating_column = st.columns(
            [1.5, 1, 1]
        )

        with search_column:
            search_term = st.text_input(
                "Buscar produto ou fornecedor",
                placeholder="Digite um nome, categoria ou fornecedor",
                icon=":material/search:",
            )

        with category_column:
            category_options = sorted(
                dataframe["category"].dropna().unique().tolist()
            )

            selected_categories = st.multiselect(
                "Categorias",
                options=category_options,
                placeholder="Todas as categorias",
            )

        with rating_column:
            rating_options = sorted(
                dataframe["plating_classification"]
                .dropna()
                .astype(int)
                .unique()
                .tolist()
            )

            selected_ratings = st.multiselect(
                "Classificação do banho",
                options=rating_options,
                placeholder="Todos os níveis",
                format_func=lambda value: f"Nível {value}",
            )

        price_min, price_max = safe_range(dataframe["selling_price"])
        profit_min, profit_max = safe_range(dataframe["profit"])
        cost_min, cost_max = safe_range(dataframe["purchase_price"])
        
        amount_min = int(dataframe["amount"].min())
        amount_max = int(dataframe["amount"].max())

        if amount_min == amount_max:
            amount_max = amount_min + 1
        
        price_column, cost_column, profit_column, amount_column  = st.columns(4)

        with price_column:
            selected_price_range = st.slider(
                "Faixa de preço de venda",
                min_value=price_min,
                max_value=price_max,
                value=(price_min, price_max),
                step=0.50,
                format="R$ %.2f",
            )

        with cost_column:
            selected_cost_range = st.slider(
                "Faixa de preço de compra",
                min_value=cost_min,
                max_value=cost_max,
                value=(cost_min, cost_max),
                step=0.50,
                format="R$ %.2f",
            )

        with profit_column:
            selected_profit_range = st.slider(
                "Faixa de lucro",
                min_value=profit_min,
                max_value=profit_max,
                value=(profit_min, profit_max),
                step=0.50,
                format="R$ %.2f",
            )

        with amount_column:
            selected_amount_range = st.slider(
                "Quantidade em estoque",
                min_value=amount_min,
                max_value=amount_max,
                value=(amount_min, amount_max),
                step=1,
            )

        date_column, sort_column, direction_column = st.columns(
            [1.4, 1, 0.8]
        )

        valid_insert_dates = dataframe["insert_date"].dropna()

        if valid_insert_dates.empty:
            minimum_date = date.today()
            maximum_date = date.today()
        else:
            minimum_date = valid_insert_dates.min().date()
            maximum_date = valid_insert_dates.max().date()

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
            "amount": "Quantidade em estoque",
            "selling_price": "Preço de venda",
            "purchase_price": "Preço de compra",
            "profit": "Lucro",
            "plating_classification": "Classificação do banho",
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

    if search_term:
        normalized_search = search_term.strip().casefold()

        search_mask = (
            filtered["name"].astype(str).str.casefold().str.contains(
                normalized_search,
                regex=False,
                na=False,
            )
            | filtered["category"].astype(str).str.casefold().str.contains(
                normalized_search,
                regex=False,
                na=False,
            )
            | filtered["supplier_name"]
            .astype(str)
            .str.casefold()
            .str.contains(
                normalized_search,
                regex=False,
                na=False,
            )
        )

        filtered = filtered[search_mask]

    if selected_categories:
        filtered = filtered[
            filtered["category"].isin(selected_categories)
        ]

    if selected_ratings:
        filtered = filtered[
            filtered["plating_classification"].isin(selected_ratings)
        ]

    filtered = filtered[
        filtered["selling_price"].between(*selected_price_range)
        & filtered["purchase_price"].between(*selected_cost_range)
        & filtered["profit"].between(*selected_profit_range)
        & filtered["amount"].between(*selected_amount_range)
    ]

    if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
        start_date, end_date = selected_dates

        filtered = filtered[
            filtered["insert_date"].dt.date.between(
                start_date,
                end_date,
            )
        ]

    filtered = filtered.sort_values(
        by=sort_column_name,
        ascending=sort_direction == "Crescente",
        na_position="last",
    )

    return filtered


def dataframe_for_export(dataframe: pd.DataFrame) -> pd.DataFrame:
    export_dataframe = dataframe.copy()

    for column in DATE_COLUMNS:
        export_dataframe[column] = export_dataframe[column].dt.strftime(
            "%d/%m/%Y %H:%M:%S"
        )

    return export_dataframe


supabase = get_supabase_client()

render_page_hero(
    eyebrow="CATÁLOGO · VISÃO GERAL",
    title="Catálogo de produtos",
    description=(
        "Consulte os produtos cadastrados, refine os resultados com filtros "
        "e acompanhe custos, preços, lucros e fornecedores."
    ),
)

update_message = st.session_state.pop(
    "catalog_update_message",
    None,
)

if update_message:
    st.success(
        update_message,
        icon="✅",
    )

refresh_column, empty_column = st.columns([0.18, 0.82])

with refresh_column:
    if st.button(
        "Atualizar dados",
        icon=":material/refresh:",
        width="stretch",
    ):
        st.cache_data.clear()
        st.rerun()

try:
    with st.spinner("Carregando produtos..."):
        products = load_products()

except Exception as error:
    st.error(
        "Não foi possível carregar os produtos do Supabase. "
        "Verifique a conexão e tente novamente."
    )

    with st.expander("Detalhes técnicos"):
        st.exception(error)

    st.stop()

if not products:
    st.info(
        "Nenhum produto foi encontrado. Cadastre a primeira peça na página "
        "“Cadastrar produto”.",
        icon="ℹ️",
    )
    st.stop()

products_dataframe = prepare_products_dataframe(products)
filtered_dataframe = apply_filters(products_dataframe)

total_products = len(filtered_dataframe)
total_cost = (
    filtered_dataframe["purchase_price"]
    + filtered_dataframe["plating_price"]
).sum()
total_sales_value = filtered_dataframe["selling_price"].sum()
total_profit = filtered_dataframe["profit"].sum()

total_amount = int(filtered_dataframe["amount"].sum())

metric_product, metric_amount, metric_cost, metric_sales, metric_profit = st.columns(5)

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
        currency_br(total_cost),
    )

with metric_sales:
    st.metric(
        "Valor de venda somado",
        currency_br(total_sales_value),
    )

with metric_profit:
    st.metric(
        "Lucro somado",
        currency_br(total_profit),
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

if filtered_dataframe.empty:
    st.warning(
        "Nenhum produto corresponde aos filtros selecionados.",
        icon="⚠️",
    )
    st.stop()

display_dataframe = filtered_dataframe.copy()

# As datas são exibidas sem informação técnica de timezone,
# mas já foram convertidas para o horário de São Paulo.
for column in DATE_COLUMNS:
    display_dataframe[column] = display_dataframe[column].dt.tz_localize(None)

column_order = [
    "name",
    "category",
    "amount",
    "selling_price",
    "profit",
    "purchase_price",
    "plating_price",
    "plating_classification",
    "supplier_name",
    "supplier_link",
    "insert_date",
    "updated_date",
    "id",
]

st.caption(
    "Selecione uma linha da tabela para editar o produto."
)

edit_action_placeholder = st.empty()

table_event = st.dataframe(
    display_dataframe,
    key=(
        "product_catalog_table_"
        f"{st.session_state['catalog_table_version']}"
    ),
    width="stretch",
    hide_index=True,
    height=540,
    column_order=column_order,
    on_select="rerun",
    selection_mode="single-row",
    column_config={
        "id": st.column_config.TextColumn(
            "ID do produto",
            help="Identificador único do produto no banco.",
            width="large",
        ),
        "name": st.column_config.TextColumn(
            "Nome da peça",
            width="large",
            pinned=True,
        ),
        "category": st.column_config.TextColumn(
            "Categoria",
            width="medium",
        ),
        "amount": st.column_config.NumberColumn(
            "Quantidade",
            help="Quantidade atual disponível em estoque.",
            format="%d",
            width="small",
        ),
        "purchase_price": st.column_config.NumberColumn(
            "Preço de compra",
            format="R$ %.2f",
            width="small",
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
        "supplier_link": st.column_config.LinkColumn(
            "Página no fornecedor",
            display_text="Abrir produto",
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
        "plating_classification": (
            st.column_config.ProgressColumn(
                "Nível do banho",
                help="Classificação de 1 a 5.",
                min_value=1,
                max_value=5,
                format="%d",
                width="medium",
            )
        ),
    },
)

selected_rows = table_event.selection.rows

with edit_action_placeholder.container():
    if selected_rows:
        selected_position = selected_rows[0]

        if selected_position < len(filtered_dataframe):
            selected_product = (
                filtered_dataframe
                .iloc[selected_position]
                .to_dict()
            )

            action_column, product_column = st.columns(
                [0.23, 0.77],
                vertical_alignment="center",
            )

            with action_column:
                edit_clicked = st.button(
                    "Editar produto",
                    icon=":material/edit:",
                    type="primary",
                    width="stretch",
                )

            with product_column:
                selected_name = selected_product.get(
                    "name",
                    "",
                )

                selected_amount = int(
                    selected_product.get("amount") or 0
                )

                st.markdown(
                    (
                        f"**Selecionado:** {selected_name}  \n"
                        f"Estoque atual: "
                        f"**{selected_amount} unidades**"
                    )
                )

            if edit_clicked:
                edit_product_dialog(selected_product)

    else:
        st.info(
            "Clique em uma linha para habilitar a edição.",
            icon=":material/touch_app:",
        )

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

# st.markdown(
#     '<div class="footer-text">ControlWise · Gestão inteligente de produtos</div>',
#     unsafe_allow_html=True,
# )
