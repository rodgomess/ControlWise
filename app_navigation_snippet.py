# No app.py, remova a página separada "Cadastrar produto"
# e deixe o catálogo como a página principal de produtos.

product_pages = [
    st.Page(
        "views/product_catalog.py",
        title="Catálogo de produtos",
        icon="📦",
        default=True,
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
        "Produtos": product_pages,
        "Fornecedores": supplier_pages,
    }
)

navigation.run()
