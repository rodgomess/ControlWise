import streamlit as st


def apply_global_styles() -> None:
    st.markdown(
        """
        <style>
            :root {
                --cw-brown-950: #2f231e;
                --cw-brown-900: #3f3029;
                --cw-brown-700: #725948;
                --cw-brown-600: #80644f;
                --cw-brown-100: #eadfd7;
                --cw-cream-50: #f8f6f3;
                --cw-cream-100: #f3eee9;
                --cw-white: #ffffff;
                --cw-text: #443832;
                --cw-muted: #7f7169;
                --cw-border: #e8e0da;
                --cw-green: #2e7d5b;
                --cw-red: #b54a4a;
            }

            .stApp {
                background:
                    radial-gradient(
                        circle at 90% 5%,
                        rgba(128, 100, 79, 0.08),
                        transparent 24rem
                    ),
                    var(--cw-cream-50);
            }

            [data-testid="stHeader"] {
                background: transparent;
            }

            [data-testid="stMainBlockContainer"] {
                max-width: 1380px;
                padding-top: 2rem;
                padding-bottom: 4rem;
            }

            /* Sidebar */
            [data-testid="stSidebar"] {
                background:
                    linear-gradient(
                        180deg,
                        var(--cw-brown-950) 0%,
                        var(--cw-brown-900) 100%
                    );
                border-right: 1px solid rgba(255, 255, 255, 0.08);
            }

            [data-testid="stSidebar"] > div:first-child {
                padding-top: 1rem;
            }

            [data-testid="stSidebar"] * {
                color: #f9f5f2;
            }

            [data-testid="stSidebarNav"] {
                padding-top: 0.1rem;
            }

            [data-testid="stSidebarNav"] span {
                font-weight: 600;
            }

            [data-testid="stSidebarNav"] a {
                border-radius: 10px;
                margin-bottom: 0.25rem;
            }

            [data-testid="stSidebarNav"] a:hover {
                background: rgba(255, 255, 255, 0.09);
            }

            [data-testid="stSidebarNav"] a[aria-current="page"] {
                background: rgba(255, 255, 255, 0.14);
                box-shadow: inset 3px 0 0 #d5bda9;
            }

            .controlwise-brand-content {
                padding-top: 0.75rem;
            }

            .controlwise-brand-name {
                font-size: 1.18rem;
                line-height: 1.05;
                font-weight: 750;
                letter-spacing: -0.03em;
                color: #ffffff;
            }

            .controlwise-brand-name span {
                color: #d8c4b3;
            }

            .controlwise-brand-tagline {
                max-width: 130px;
                margin-top: 0.35rem;
                font-size: 0.65rem;
                line-height: 1.3;
                color: #cbbdb4 !important;
            }

            .controlwise-menu-label {
                margin: 1.2rem 0 0.45rem 0.45rem;
                font-size: 0.66rem;
                font-weight: 700;
                letter-spacing: 0.14em;
                color: #a99a91 !important;
            }

            [data-testid="stSidebar"] [data-testid="stImage"] {
                display: flex;
                align-items: center;
                justify-content: center;
            }

            [data-testid="stSidebar"] [data-testid="stImage"] img {
                object-fit: contain;
            }

            .controlwise-brand-name {
                font-size: 1.28rem;
                line-height: 1.05;
                font-weight: 750;
                letter-spacing: -0.03em;
                color: #ffffff;
            }

            .controlwise-brand-name span {
                color: #d8c4b3;
            }

            .controlwise-brand-tagline {
                margin-top: 0.3rem;
                font-size: 0.68rem;
                color: #cbbdb4 !important;
                letter-spacing: 0.02em;
            }

            .controlwise-menu-label {
                margin: 0.2rem 0 0.45rem 0.45rem;
                font-size: 0.66rem;
                font-weight: 700;
                letter-spacing: 0.14em;
                color: #a99a91 !important;
            }

            /* Cabeçalhos */
            .page-hero {
                padding: 1.75rem 1.9rem;
                margin-bottom: 1.45rem;
                border-radius: 20px;
                background:
                    linear-gradient(
                        135deg,
                        var(--cw-brown-900) 0%,
                        var(--cw-brown-700) 100%
                    );
                box-shadow: 0 12px 30px rgba(63, 48, 41, 0.16);
            }

            .page-hero__eyebrow {
                margin-bottom: 0.4rem;
                font-size: 0.72rem;
                font-weight: 700;
                letter-spacing: 0.13em;
                color: #d9c8bb;
            }

            .page-hero h1 {
                margin: 0;
                color: #ffffff;
                font-size: clamp(1.75rem, 3vw, 2.4rem);
                line-height: 1.1;
                letter-spacing: -0.035em;
            }

            .page-hero p {
                max-width: 750px;
                margin: 0.65rem 0 0;
                color: #eadfd7;
                font-size: 0.97rem;
                line-height: 1.55;
            }

            /* Cards */
            .section-heading {
                margin: 0.2rem 0 0.9rem;
            }

            .section-heading__title {
                font-size: 1.05rem;
                font-weight: 750;
                color: var(--cw-brown-900);
            }

            .section-heading__description {
                margin-top: 0.18rem;
                color: var(--cw-muted);
                font-size: 0.87rem;
            }

            div[data-testid="stForm"] {
                padding: 1.6rem;
                border: 1px solid var(--cw-border);
                border-radius: 18px;
                background: rgba(255, 255, 255, 0.95);
                box-shadow: 0 6px 24px rgba(65, 49, 41, 0.06);
            }

            div[data-testid="stMetric"] {
                min-height: 112px;
                padding: 1rem 1.1rem;
                border: 1px solid var(--cw-border);
                border-radius: 16px;
                background: rgba(255, 255, 255, 0.94);
                box-shadow: 0 5px 18px rgba(65, 49, 41, 0.05);
            }

            [data-testid="stMetricLabel"] {
                color: var(--cw-muted);
            }

            [data-testid="stMetricValue"] {
                color: var(--cw-brown-900);
            }

            /* Inputs */
            div[data-baseweb="input"] > div,
            div[data-baseweb="select"] > div,
            div[data-testid="stNumberInput"] input {
                border-radius: 11px;
            }

            div[data-testid="stFormSubmitButton"] button,
            div[data-testid="stDownloadButton"] button {
                min-height: 46px;
                border: 0;
                border-radius: 11px;
                background:
                    linear-gradient(
                        135deg,
                        var(--cw-brown-600) 0%,
                        var(--cw-brown-900) 100%
                    );
                color: #ffffff;
                font-weight: 700;
                transition: transform 0.16s ease, box-shadow 0.16s ease;
            }

            div[data-testid="stFormSubmitButton"] button:hover,
            div[data-testid="stDownloadButton"] button:hover {
                transform: translateY(-1px);
                box-shadow: 0 7px 18px rgba(75, 57, 47, 0.23);
            }

            div[data-testid="stButton"] button {
                min-height: 42px;
                border-radius: 10px;
                border-color: var(--cw-border);
                color: var(--cw-brown-900);
                background: #ffffff;
            }

            .price-preview {
                margin: 0.7rem 0 1.15rem;
                padding: 0.95rem 1rem;
                border: 1px solid #e4d8cf;
                border-left: 4px solid var(--cw-brown-600);
                border-radius: 12px;
                background: var(--cw-cream-100);
                color: var(--cw-text);
            }

            .filter-panel-title {
                margin-bottom: 0.35rem;
                color: var(--cw-brown-900);
                font-size: 1rem;
                font-weight: 750;
            }

            .filter-result {
                margin: 0.15rem 0 0.85rem;
                color: var(--cw-muted);
                font-size: 0.86rem;
            }

            .footer-text {
                margin-top: 1.6rem;
                color: #94847a;
                text-align: center;
                font-size: 0.78rem;
            }

            hr {
                border-color: var(--cw-border) !important;
            }
            
            /* =========================================================
            Botões de exclusão
            ========================================================= */

            div[class*="st-key-delete_product_button_"] button,
            div[class*="st-key-confirm_delete_product_button_"] button,
            div[class*="st-key-delete_product_image_button_"] button,
            div[class*="st-key-confirm_delete_product_image_button_"] button {
                min-height: 42px;
                border: 1px solid #B42318 !important;
                border-radius: 10px;
                background: #B42318 !important;
                background-color: #B42318 !important;
                color: #FFFFFF !important;
                font-weight: 700 !important;
            }

            /* Mantém texto e ícone brancos */
            div[class*="st-key-delete_product_button_"] button *,
            div[class*="st-key-confirm_delete_product_button_"] button *,
            div[class*="st-key-delete_product_image_button_"] button *,
            div[class*="st-key-confirm_delete_product_image_button_"] button * {
                color: #FFFFFF !important;
                fill: #FFFFFF !important;
            }

            /* Hover */
            div[class*="st-key-delete_product_button_"] button:hover,
            div[class*="st-key-confirm_delete_product_button_"] button:hover,
            div[class*="st-key-delete_product_image_button_"] button:hover,
            div[class*="st-key-confirm_delete_product_image_button_"] button:hover {
                border-color: #912018 !important;
                background: #912018 !important;
                background-color: #912018 !important;
                color: #FFFFFF !important;
            }

            /* Foco */
            div[class*="st-key-delete_product_button_"] button:focus,
            div[class*="st-key-confirm_delete_product_button_"] button:focus,
            div[class*="st-key-delete_product_image_button_"] button:focus,
            div[class*="st-key-confirm_delete_product_image_button_"] button:focus {
                border-color: #912018 !important;
                background: #912018 !important;
                background-color: #912018 !important;
                color: #FFFFFF !important;
                box-shadow: 0 0 0 3px rgba(180, 35, 24, 0.22) !important;
            }

            /* Botão de deletar foto sem imagem */
            div[class*="st-key-delete_product_image_button_"] button:disabled {
                background: #ded8d3 !important;
                background-color: #ded8d3 !important;
                border-color: #d2cbc6 !important;
                color: #948a83 !important;
                opacity: 0.65 !important;
                cursor: not-allowed !important;
                box-shadow: none !important;
                transform: none !important;
            }

            div[class*="st-key-delete_product_image_button_"] button:disabled:hover {
                background: #ded8d3 !important;
                background-color: #ded8d3 !important;
                border-color: #d2cbc6 !important;
                color: #948a83 !important;
                box-shadow: none !important;
                transform: none !important;
            }

            div[class*="st-key-delete_product_image_button_"] button:disabled * {
                color: #948a83 !important;
                fill: #948a83 !important;
            }

            /* Botões de exclusão de fornecedor */
            div[class*="st-key-delete_supplier_button_"] button,
            div[class*="st-key-confirm_delete_supplier_button_"] button {
                min-height: 42px;
                border: 1px solid #B42318 !important;
                border-radius: 10px;
                background: #B42318 !important;
                background-color: #B42318 !important;
                color: #FFFFFF !important;
                font-weight: 700 !important;
            }

            div[class*="st-key-delete_supplier_button_"] button *,
            div[class*="st-key-confirm_delete_supplier_button_"] button * {
                color: #FFFFFF !important;
                fill: #FFFFFF !important;
            }

            div[class*="st-key-delete_supplier_button_"] button:hover,
            div[class*="st-key-confirm_delete_supplier_button_"] button:hover {
                border-color: #912018 !important;
                background: #912018 !important;
                background-color: #912018 !important;
                color: #FFFFFF !important;
            }

            div[class*="st-key-delete_supplier_button_"] button:focus,
            div[class*="st-key-confirm_delete_supplier_button_"] button:focus {
                border-color: #912018 !important;
                background: #912018 !important;
                background-color: #912018 !important;
                color: #FFFFFF !important;
                box-shadow:
                    0 0 0 3px rgba(180, 35, 24, 0.22) !important;
            }

            /* Exclusão de preços de banho */
            div[class*="st-key-delete_plating_price_button_"] button,
            div[class*="st-key-confirm_delete_plating_price_button_"] button {
                border: 1px solid #B42318 !important;
                background: #B42318 !important;
                background-color: #B42318 !important;
                color: #FFFFFF !important;
                font-weight: 700 !important;
            }

            div[class*="st-key-delete_plating_price_button_"] button *,
            div[class*="st-key-confirm_delete_plating_price_button_"] button * {
                color: #FFFFFF !important;
                fill: #FFFFFF !important;
            }

            div[class*="st-key-delete_plating_price_button_"] button:hover,
            div[class*="st-key-confirm_delete_plating_price_button_"] button:hover {
                border-color: #912018 !important;
                background: #912018 !important;
                background-color: #912018 !important;
                color: #FFFFFF !important;
            </style>
        """,
        unsafe_allow_html=True,
    )


def render_page_hero(
    eyebrow: str,
    title: str,
    description: str,
) -> None:
    st.markdown(
        f"""
        <section class="page-hero">
            <div class="page-hero__eyebrow">{eyebrow}</div>
            <h1>{title}</h1>
            <p>{description}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_section_heading(title: str, description: str) -> None:
    st.markdown(
        f"""
        <div class="section-heading">
            <div class="section-heading__title">{title}</div>
            <div class="section-heading__description">{description}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
