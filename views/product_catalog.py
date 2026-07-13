from __future__ import annotations

from datetime import date
import hashlib
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

EXPECTED_COLUMNS = [
    "id",
    "name",
    "category",
    "weight",
    "base_metal",
    "target_gender",
    "plating_company_name",
    "plating_metal",
    "amount",
    "purchase_price",
    "plating_price",
    "selling_price",
    "profit",
    "supplier_product_id",
    "supplier_name",
    "supplier_contact",
    "insert_date",
    "updated_date",
    "plating_classification",
]

OPTIONAL_TEXT_FIELDS = {
    "base_metal",
    "target_gender",
    "plating_company_name",
    "plating_metal",
    "supplier_product_id",
    "supplier_name",
    "supplier_contact",
}

FLOAT_FIELDS = {
    "weight",
    "purchase_price",
    "plating_price",
    "selling_price",
}

INTEGER_FIELDS = {
    "amount",
    "plating_classification",
}

TEXT_COLUMNS = [
    "id",
    "name",
    "category",
    "base_metal",
    "target_gender",
    "plating_company_name",
    "plating_metal",
    "supplier_product_id",
    "supplier_name",
    "supplier_contact",
]

if "catalog_table_version" not in st.session_state:
    st.session_state["catalog_table_version"] = 0


# ============================================================
# Supabase
# ============================================================

@st.cache_resource
def get_supabase_client() -> SupabaseClient:
    return SupabaseClient()


@st.cache_data(ttl=60, show_spinner=False)
def load_products() -> list[dict]:
    client = get_supabase_client()
    return client.load_products() or []


supabase = get_supabase_client()


# ============================================================
# Preparação e normalização dos dados
# ============================================================

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
        .fillna(1)
        .clip(lower=1, upper=20)
        .astype(int)
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


def currency_br(value: float) -> str:
    return (
        f"R$ {value:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def normalize_product_value(field: str, value):
    if field in OPTIONAL_TEXT_FIELDS:
        normalized_value = text_value(value).strip()

        if normalized_value in {"", "Não informado"}:
            return None

        return normalized_value

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
    plating_classification: int,
    supplier_contact: str,
) -> list[str]:
    errors: list[str] = []

    if not name.strip():
        errors.append("Informe o nome do produto.")

    if not category:
        errors.append("Selecione uma categoria.")

    if amount < 0:
        errors.append("A quantidade em estoque não pode ser negativa.")

    if weight < 0:
        errors.append("O peso da peça não pode ser negativo.")

    if purchase_price < 0:
        errors.append("O preço de compra não pode ser negativo.")

    if plating_price < 0:
        errors.append("O custo do banho não pode ser negativo.")

    if selling_price <= 0:
        errors.append("O preço de venda deve ser maior que zero.")

    total_cost = purchase_price + plating_price

    if selling_price < total_cost:
        errors.append(
            "O preço de venda está abaixo do custo total da peça."
        )

    if not 1 <= plating_classification <= 20:
        errors.append(
            "A classificação do banho deve estar entre 1 e 20."
        )

    return errors


# ============================================================
# Popup compartilhado: criar e editar
# ============================================================


def request_product_deletion(confirmation_key: str) -> None:
    """
    Exibe a etapa de confirmação da exclusão.
    """
    st.session_state[confirmation_key] = True


def cancel_product_deletion(confirmation_key: str) -> None:
    """
    Cancela a exclusão e esconde a confirmação.
    """
    st.session_state[confirmation_key] = False

def render_delete_product_zone(
    product_id: str,
    product_name: str,
) -> None:
    """
    Renderiza a zona de exclusão com confirmação em duas etapas.
    """

    confirmation_key = (
        f"confirm_delete_product_{product_id}"
    )

    st.divider()

    st.markdown("#### Zona de perigo")

    st.caption(
        "A exclusão remove definitivamente o produto do banco de dados."
    )

    deletion_requested = st.session_state.get(
        confirmation_key,
        False,
    )

    if not deletion_requested:
        st.button(
            "Deletar Registro",
            key="delete_product_button",
            icon=":material/delete:",
            width="stretch",
            on_click=request_product_deletion,
            args=(confirmation_key,),
        )

        return

    st.error(
        (
            f'Você realmente deseja deletar o produto '
            f'“{product_name}”? Esta ação não poderá ser desfeita.'
        ),
        icon="⚠️",
    )

    cancel_column, confirm_column = st.columns(2)

    with cancel_column:
        st.button(
            "Cancelar",
            key="cancel_delete_product_button",
            icon=":material/close:",
            width="stretch",
            on_click=cancel_product_deletion,
            args=(confirmation_key,),
        )

    with confirm_column:
        confirm_delete = st.button(
            "Confirmar deleção",
            key="confirm_delete_product_button",
            icon=":material/delete_forever:",
            width="stretch",
        )

    if not confirm_delete:
        return

    try:
        with st.spinner("Deletando produto..."):
            supabase.delete_product(product_id)

        # Remove o estado da confirmação.
        st.session_state.pop(
            confirmation_key,
            None,
        )

        # Limpa o cache de load_products().
        st.cache_data.clear()

        # Exibe a mensagem depois que o popup fechar.
        st.session_state["catalog_update_message"] = (
            f'Produto "{product_name}" deletado com sucesso.'
        )

        # Altera a chave da tabela e remove a seleção anterior.
        st.session_state["catalog_table_version"] += 1

        # Fecha o popup e recarrega o catálogo.
        st.rerun(scope="app")

    except Exception as error:
        st.error(
            "Não foi possível deletar o produto. "
            "Verifique a conexão com o Supabase."
        )

        with st.expander("Detalhes técnicos"):
            st.exception(error)

@st.dialog(
    "Produto",
    width="large",
    icon=":material/inventory_2:",
)
def product_form_dialog(
    mode: str,
    product: dict | None = None,
) -> None:
    is_editing = mode == "edit"
    product = product or {}

    product_id = text_value(product.get("id")).strip()
    current_name = text_value(product.get("name"))
    current_category = text_value(product.get("category"))

    if current_category == "Sem categoria":
        current_category = ""

    current_weight = float_value(product.get("weight"))
    current_base_metal = text_value(product.get("base_metal"))
    current_target_gender = text_value(product.get("target_gender"))
    current_plating_company_name = text_value(
        product.get("plating_company_name")
    )
    current_plating_metal = text_value(product.get("plating_metal"))
    current_amount = integer_value(product.get("amount"))
    current_purchase_price = float_value(product.get("purchase_price"))
    current_plating_price = float_value(product.get("plating_price"))
    current_selling_price = float_value(product.get("selling_price"))
    current_supplier_product_id = text_value(
        product.get("supplier_product_id")
    )
    current_supplier_name = text_value(product.get("supplier_name"))
    current_supplier_contact = text_value(product.get("supplier_contact"))
    current_plating_classification = integer_value(
        product.get("plating_classification"),
        default=1,
    )
    current_plating_classification = min(
        max(current_plating_classification, 1),
        20,
    )

    if current_supplier_name == "Não informado":
        current_supplier_name = ""

    category_options = EDITABLE_CATEGORIES.copy()

    if current_category and current_category not in category_options:
        category_options.insert(0, current_category)

    category_index = (
        category_options.index(current_category)
        if current_category
        else None
    )

    if is_editing:
        st.markdown("### Editar produto")
        st.caption(f"ID do produto: `{product_id}`")
        st.write(
            "Altere os campos necessários e confirme para salvar."
        )
    else:
        st.markdown("### Novo produto")
        st.write(
            "Preencha os dados para cadastrar uma nova peça no estoque."
        )

    form_key = f"product_form_{mode}_{product_id or 'new'}"

    with st.form(form_key):
        st.markdown("#### Identificação e estoque")

        name_column, category_column = st.columns([1.5, 1])

        with name_column:
            name = st.text_input(
                "Nome da peça",
                value=current_name,
                placeholder="Ex.: Pulseira Aurora Dourada",
            )

        with category_column:
            category = st.selectbox(
                "Categoria",
                options=category_options,
                index=category_index,
                placeholder="Selecione uma categoria",
            )

        amount_column, weight_column, gender_column = st.columns(3)

        with amount_column:
            amount = st.number_input(
                "Quantidade em estoque",
                min_value=0,
                value=current_amount,
                step=1,
            )

        with weight_column:
            weight = st.number_input(
                "Peso unitário (g)",
                min_value=0.00,
                value=current_weight,
                step=0.10,
                format="%.2f",
            )

        with gender_column:
            target_gender = st.text_input(
                "Gênero / público-alvo",
                value=current_target_gender,
                placeholder="Ex.: Feminino ou Unissex",
            )

        base_metal = st.text_input(
            "Metal base da peça",
            value=current_base_metal,
            placeholder="Ex.: Latão, cobre ou aço inox",
        )

        st.divider()
        st.markdown("#### Custos e preço")

        purchase_column, plating_column, selling_column = st.columns(3)

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

        total_cost = float(purchase_price) + float(plating_price)
        estimated_profit = float(selling_price) - total_cost
        profit_margin = (
            estimated_profit / float(selling_price) * 100
            if selling_price > 0
            else 0
        )

        st.markdown(
            f"""
            <div class="price-preview">
                <strong>Custo total:</strong> {currency_br(total_cost)}
                &nbsp;&nbsp;·&nbsp;&nbsp;
                <strong>Lucro estimado:</strong>
                {currency_br(estimated_profit)}
                &nbsp;&nbsp;·&nbsp;&nbsp;
                <strong>Margem:</strong> {profit_margin:.1f}%
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.divider()
        st.markdown("#### Fornecedor da peça")

        supplier_column, supplier_product_column = st.columns(2)

        with supplier_column:
            supplier_name = st.text_input(
                "Nome do fornecedor",
                value=current_supplier_name,
                placeholder="Ex.: Joias Horizonte",
            )

        with supplier_product_column:
            supplier_product_id = st.text_input(
                "ID do produto no fornecedor",
                value=current_supplier_product_id,
                placeholder="Ex.: PL-4587",
            )

        supplier_contact = st.text_input(
            "Contato do fornecedor",
            value=current_supplier_contact,
            placeholder="https://fornecedor.com/produto",
        )

        st.divider()
        st.markdown("#### Banho e acabamento")

        company_column, metal_column, classification_column = st.columns(
            [1.3, 1, 0.7]
        )

        with company_column:
            plating_company_name = st.text_input(
                "Empresa responsável pelo banho",
                value=current_plating_company_name,
                placeholder="Ex.: Banhos Dourados São Paulo",
            )

        with metal_column:
            plating_metal = st.text_input(
                "Metal do banho",
                value=current_plating_metal,
                placeholder="Ex.: Ouro 18k",
            )

        with classification_column:
            plating_classification = st.number_input(
                "Classificação",
                min_value=1,
                max_value=20,
                value=current_plating_classification,
                step=1,
                help="Classificação numérica de 1 a 20.",
            )

        submit_label = (
            "Salvar alterações"
            if is_editing
            else "Cadastrar produto"
        )
        
        submit_icon = (
            ":material/save:"
            if is_editing
            else ":material/add_circle:"
        )

        submitted = st.form_submit_button(
            submit_label,
            icon=submit_icon,
            type="primary",
            width="stretch",
        )

    if is_editing:
        render_delete_product_zone(
            product_id=product_id,
            product_name=current_name,
        )
        
    if not submitted:
        return

    validation_errors = validate_product(
        name=name,
        category=category,
        amount=int(amount),
        weight=float(weight),
        purchase_price=float(purchase_price),
        plating_price=float(plating_price),
        selling_price=float(selling_price),
        plating_classification=int(plating_classification),
        supplier_contact=supplier_contact,
    )

    if validation_errors:
        for error in validation_errors:
            st.error(error)
        return

    product_data = {
        "name": name.strip(),
        "category": category,
        "weight": round(float(weight), 2),
        "base_metal": base_metal.strip() or None,
        "target_gender": target_gender.strip() or None,
        "plating_company_name": (
            plating_company_name.strip() or None
        ),
        "plating_metal": plating_metal.strip() or None,
        "amount": int(amount),
        "purchase_price": round(float(purchase_price), 2),
        "plating_price": round(float(plating_price), 2),
        "selling_price": round(float(selling_price), 2),
        "supplier_product_id": (
            supplier_product_id.strip() or None
        ),
        "supplier_name": supplier_name.strip() or None,
        "supplier_contact": supplier_contact.strip() or None,
        "plating_classification": int(plating_classification),
    }

    try:
        with st.spinner("Salvando produto..."):
            if is_editing:
                update_payload = build_update_payload(
                    original_product=product,
                    edited_product=product_data,
                )

                if not update_payload:
                    st.info(
                        "Nenhuma alteração foi identificada.",
                        icon="ℹ️",
                    )
                    return

                # Mantém a assinatura utilizada no seu código:
                # update_product(id_do_produto, campos_alterados)
                supabase.update_product(
                    product_id,
                    update_payload,
                )

                success_message = (
                    f'Produto "{name.strip()}" atualizado com sucesso.'
                )
            else:
                supabase.insert_product(product_data)

                success_message = (
                    f'Produto "{name.strip()}" cadastrado com sucesso.'
                )

        st.cache_data.clear()
        st.session_state["catalog_update_message"] = success_message
        st.session_state["catalog_table_version"] += 1
        st.rerun()

    except Exception as error:
        action = "atualizar" if is_editing else "cadastrar"

        st.error(
            f"Não foi possível {action} o produto. "
            "Verifique a conexão com o Supabase."
        )

        with st.expander("Detalhes técnicos"):
            st.exception(error)


# ============================================================
# Filtros — somente texto e número, sem sliders
# ============================================================

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
        & filtered["plating_classification"].between(
            int(classification_min),
            int(classification_max),
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


def dataframe_for_export(dataframe: pd.DataFrame) -> pd.DataFrame:
    export_dataframe = dataframe.copy()

    for column in DATE_COLUMNS:
        export_dataframe[column] = export_dataframe[column].dt.strftime(
            "%d/%m/%Y %H:%M:%S"
        )

    return export_dataframe


# ============================================================
# Página
# ============================================================

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

if update_message:
    st.success(update_message, icon="✅")

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


# ============================================================
# Estado sem produtos
# ============================================================

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


products_dataframe = prepare_products_dataframe(products)
filtered_dataframe = apply_filters(products_dataframe)


# ============================================================
# Métricas — mantidas conforme seu código
# ============================================================

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


# ============================================================
# Resultado vazio dos filtros
# ============================================================

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


# ============================================================
# Tabela
# ============================================================

display_dataframe = filtered_dataframe.copy()

for column in DATE_COLUMNS:
    display_dataframe[column] = (
        display_dataframe[column].dt.tz_localize(None)
    )

column_order = [
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
    "plating_metal",
    "plating_price",
    "plating_classification",
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

table_key = (
    "product_catalog_table_"
    f"{st.session_state['catalog_table_version']}_"
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
            help="Classificação numérica de 1 a 20.",
            format="%d",
            width="medium",
        ),
    },
)


# ============================================================
# Linha selecionada e barra de ações
# ============================================================

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
        refresh_column,
        selected_column,
    ) = st.columns([0.18, 0.18, 0.17, 0.47])

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

            st.markdown(
                (
                    f"**Selecionado:** {selected_name}  \n"
                    f"ID: `{selected_id}` · "
                    f"Estoque atual: **{selected_amount} unidades**"
                )
            )
        else:
            st.caption(
                "Selecione uma linha para habilitar a edição."
            )

if refresh_clicked:
    st.cache_data.clear()
    st.session_state["catalog_table_version"] += 1
    st.rerun()

if create_clicked:
    product_form_dialog(mode="create")

elif edit_clicked and selected_product:
    product_form_dialog(
        mode="edit",
        product=selected_product,
    )


# ============================================================
# Exportação
# ============================================================

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