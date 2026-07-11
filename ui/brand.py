import base64
from pathlib import Path

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOGO_PATH = PROJECT_ROOT / "assets" / "logo_wc.svg"


@st.cache_data
def build_horizontal_logo() -> str:
    """
    Cria uma logo horizontal com o símbolo WC e o nome ControlWise.

    O logo_wc.svg continua sendo carregado da pasta assets.
    """

    if not LOGO_PATH.exists():
        raise FileNotFoundError(
            f"Logo não encontrada em: {LOGO_PATH}"
        )

    logo_bytes = LOGO_PATH.read_bytes()
    logo_base64 = base64.b64encode(logo_bytes).decode("utf-8")

    return f"""
    <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 500 100"
        width="500"
        height="100"
    >
        <defs>
            <clipPath id="logo-clip">
                <rect
                    x="0"
                    y="0"
                    width="150"
                    height="200"
                    rx="4"
                />
            </clipPath>
        </defs>

        <g clip-path="url(#logo-clip)">
            <image
                href="data:image/svg+xml;base64,{logo_base64}"
                x="-40"
                y="-25"
                width="195"
                height="130"
                preserveAspectRatio="xMidYMid meet"
            />
        </g>

        <text
            x="123"
            y="65"
            fill="#F7F1ED"
            font-family="Arial, Helvetica, sans-serif"
            font-size="60"
            font-weight="700"
            letter-spacing="-1"
        >
            WiseControl
        </text>
    </svg>
    """.strip()


def render_app_logo() -> None:
    """Exibe a identidade ControlWise acima da navegação."""

    try:
        horizontal_logo = build_horizontal_logo()

        st.logo(
            horizontal_logo,
            size="large",
            icon_image=str(LOGO_PATH),
        )

    except FileNotFoundError as error:
        st.sidebar.error(str(error))