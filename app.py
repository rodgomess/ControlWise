import streamlit as st

from ui.brand import render_app_logo
from ui.styles import apply_global_styles


st.set_page_config(
    page_title="ControlWise",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="auto"
)

apply_global_styles()
render_app_logo()

pages = [
    st.Page(
        "views/product_catalog.py",
        title="Catálogo de produtos",
        icon="📦",
    ),
]

supplier_pages = [
    st.Page(
        "views/plating_suppliers.py",
        title="Fornecedores de banho",
        icon="🏭",
    ),
]

navigation = st.navigation(
    {
        "Produtos": pages,
        "Fornecedores": supplier_pages,
    }
)

navigation.run()
