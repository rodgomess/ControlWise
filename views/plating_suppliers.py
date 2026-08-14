from __future__ import annotations

import streamlit as st

from ui.styles import render_page_hero
from src.shared.data_access import load_plating_prices, load_plating_suppliers
from src.features.plating.service import prepare_plating_prices_dataframe, prepare_suppliers_dataframe
from src.features.plating.tabs import render_plating_prices_tab, render_suppliers_tab

if "plating_suppliers_table_version" not in st.session_state:
    st.session_state["plating_suppliers_table_version"] = 0
if "plating_prices_table_version" not in st.session_state:
    st.session_state["plating_prices_table_version"] = 0

# ============================================================
# Página
# ============================================================

render_page_hero(
    eyebrow="FORNECEDORES · BANHOS E ACABAMENTOS",
    title="Fornecedores de banho",
    description=(
        "Consulte e organize as empresas responsáveis pelos "
        "banhos e acabamentos das peças."
    ),
)

try:
    with st.spinner(
        "Carregando fornecedores e preços..."
    ):
        suppliers = load_plating_suppliers()
        plating_prices = load_plating_prices()

except Exception as error:
    st.error(
        "Não foi possível carregar os fornecedores "
        "e os preços do Supabase."
    )

    with st.expander("Detalhes técnicos"):
        st.exception(error)

    st.stop()


suppliers_dataframe = (
    prepare_suppliers_dataframe(
        suppliers
    )
)

plating_prices_dataframe = (
    prepare_plating_prices_dataframe(
        plating_prices
    )
)


suppliers_tab, prices_tab = st.tabs(
    [
        "Fornecedores",
        "Preços e classificações",
    ]
)


with suppliers_tab:
    render_suppliers_tab(
        suppliers_dataframe
    )


with prices_tab:
    render_plating_prices_tab(
        plating_prices_dataframe,
        suppliers_dataframe,
    )


st.markdown(
    """
    <div class="footer-text">
        WiseControl · Gestão inteligente de fornecedores
    </div>
    """,
    unsafe_allow_html=True,
)
