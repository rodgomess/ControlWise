import streamlit as st

from ui.brand import render_app_logo
from ui.styles import apply_global_styles


st.set_page_config(
    page_title="ControlWise",
    page_icon="💎",
    layout="wide",
    # initial_sidebar_state="expanded",
    initial_sidebar_state=320
)

apply_global_styles()
render_app_logo()

pages = [
    st.Page(
        "views/product_form.py",
        title="Cadastrar produto",
        icon="➕",
        default=True,
    ),
    st.Page(
        "views/product_catalog.py",
        title="Catálogo de produtos",
        icon="📦",
    ),
]

navigation = st.navigation(
    {
        "Produtos": pages,
    }
)

navigation.run()
