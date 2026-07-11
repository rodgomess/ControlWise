from urllib.parse import urlparse

import streamlit as st

from src.services.supabase import SupabaseClient
from ui.styles import render_page_hero, render_section_heading


@st.cache_resource
def get_supabase_client() -> SupabaseClient:
    return SupabaseClient()


def format_currency(value: float) -> str:
    return (
        f"R$ {value:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def is_valid_url(value: str) -> bool:
    if not value:
        return True

    parsed_url = urlparse(value)
    return parsed_url.scheme in {"http", "https"} and bool(parsed_url.netloc)


def validate_product(
    name: str,
    category: str | None,
    purchase_price: float,
    plating_price: float,
    selling_price: float,
    supplier_link: str,
) -> list[str]:
    errors: list[str] = []

    if not name.strip():
        errors.append("Informe o nome do produto.")

    if not category:
        errors.append("Selecione uma categoria.")

    if selling_price <= 0:
        errors.append("O preço de venda deve ser maior que zero.")

    total_cost = purchase_price + plating_price

    if selling_price < total_cost:
        errors.append(
            "O preço de venda está abaixo do custo total da peça."
        )

    if not is_valid_url(supplier_link.strip()):
        errors.append(
            "O link do fornecedor deve ser uma URL válida iniciada por "
            "http:// ou https://."
        )

    return errors


supabase = get_supabase_client()

render_page_hero(
    eyebrow="CATÁLOGO · NOVA PEÇA",
    title="Cadastrar novo produto",
    description=(
        "Inclua uma nova peça no catálogo da WiseControl com seus custos, "
        "preço de venda, acabamento e dados do fornecedor."
    ),
)

with st.form("new_product_form", clear_on_submit=True):
    render_section_heading(
        "Identificação da peça",
        "Defina um nome claro e a categoria usada para organizar o catálogo.",
    )

    product_name = st.text_input(
        "Nome da peça",
        placeholder="Ex.: Pulseira Aurora Dourada",
        help="Use um nome que facilite a busca e a identificação da peça.",
    )

    category = st.selectbox(
        "Categoria",
        options=[
            "Anel",
            "Brinco",
            "Colar",
            "Conjunto",
            "Pingente",
            "Pulseira",
            "Tornozeleira",
            "Outro",
        ],
        index=None,
        placeholder="Selecione a categoria da peça",
    )

    st.divider()

    render_section_heading(
        "Custos e preço",
        "Informe o custo de aquisição, o custo do banho e o valor de venda.",
    )

    purchase_column, plating_column, selling_column = st.columns(3)

    with purchase_column:
        purchase_price = st.number_input(
            "Preço de compra",
            min_value=0.00,
            value=0.00,
            step=0.50,
            format="%.2f",
        )

    with plating_column:
        plating_price = st.number_input(
            "Custo do banho",
            min_value=0.00,
            value=0.00,
            step=0.50,
            format="%.2f",
        )

    with selling_column:
        selling_price = st.number_input(
            "Preço de venda",
            min_value=0.00,
            value=0.00,
            step=1.00,
            format="%.2f",
        )

    total_cost = purchase_price + plating_price
    estimated_profit = selling_price - total_cost
    profit_margin = (
        (estimated_profit / selling_price) * 100
        if selling_price > 0
        else 0
    )

    st.markdown(
        f"""
        <div class="price-preview">
            <strong>Custo total:</strong> {format_currency(total_cost)}
            &nbsp;&nbsp;·&nbsp;&nbsp;
            <strong>Lucro estimado:</strong>
            {format_currency(estimated_profit)}
            &nbsp;&nbsp;·&nbsp;&nbsp;
            <strong>Margem:</strong> {profit_margin:.1f}%
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    render_section_heading(
        "Banho e acabamento",
        "Classifique a qualidade ou durabilidade do banho aplicado à peça.",
    )

    plating_classification = st.slider(
        "Classificação do banho",
        min_value=1,
        max_value=5,
        value=3,
        help="1 representa acabamento básico e 5 representa premium.",
    )

    plating_labels = {
        1: "Básico",
        2: "Regular",
        3: "Bom",
        4: "Superior",
        5: "Premium",
    }

    st.caption(
        f"Nível selecionado: {plating_classification} — "
        f"{plating_labels[plating_classification]}"
    )

    st.divider()

    render_section_heading(
        "Fornecedor",
        "Registre a origem da peça para facilitar compras e reposições.",
    )

    supplier_name = st.text_input(
        "Nome do fornecedor",
        placeholder="Ex.: Joias Horizonte",
    )

    supplier_link = st.text_input(
        "Link da peça no fornecedor",
        placeholder="https://fornecedor.com/produto",
    )

    submitted = st.form_submit_button(
        "Cadastrar produto",
        icon=":material/add_circle:",
        width="stretch",
    )

if submitted:
    validation_errors = validate_product(
        name=product_name,
        category=category,
        purchase_price=purchase_price,
        plating_price=plating_price,
        selling_price=selling_price,
        supplier_link=supplier_link,
    )

    if validation_errors:
        for error in validation_errors:
            st.error(error)
    else:
        product_data = {
            "name": product_name.strip(),
            "category": category,
            "purchase_price": float(purchase_price),
            "plating_price": float(plating_price),
            "selling_price": float(selling_price),
            "plating_classification": int(plating_classification),
            "supplier_name": supplier_name.strip() or None,
            "supplier_link": supplier_link.strip() or None,
        }

        try:
            supabase.insert_product(product_data)
            st.cache_data.clear()

            st.success(
                f'Produto "{product_data["name"]}" cadastrado com sucesso!',
                icon="✅",
            )

            with st.expander("Ver dados enviados ao banco"):
                st.json(product_data)

        except Exception as error:
            st.error(
                "Não foi possível cadastrar o produto. "
                "Verifique a conexão com o Supabase."
            )

            with st.expander("Detalhes técnicos"):
                st.exception(error)

# st.markdown(
#     '<div class="footer-text">ControlWise · Gestão inteligente de produtos</div>',
#     unsafe_allow_html=True,
# )
