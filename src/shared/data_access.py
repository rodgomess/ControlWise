from __future__ import annotations

import streamlit as st

from src.services.supabase import SupabaseClient

@st.cache_resource
def get_supabase_client() -> SupabaseClient:
    return SupabaseClient()


@st.cache_data(ttl=60, show_spinner=False)
def load_products() -> list[dict]:
    client = get_supabase_client()
    return client.load_products() or []


@st.cache_data(ttl=60, show_spinner=False)
def load_plating_suppliers() -> list[dict]:
    client = get_supabase_client()
    return client.load_suppliers_plating() or []


@st.cache_data(ttl=60, show_spinner=False)
def load_plating_prices() -> list[dict]:
    client = get_supabase_client()
    return client.load_suppliers_plating_prices() or []


@st.cache_data(ttl=300, show_spinner=False)
def load_product_image_urls(
    product_id: str,
) -> dict[str, str | None]:
    """
    Busca as URLs da imagem original e da miniatura.

    Produtos sem imagem retornam valores nulos para evitar que
    uma falha de Storage interrompa o catálogo inteiro.
    """
    if not product_id:
        return {
            "original_url_image": None,
            "thumbnail_url_image": None,
        }

    try:
        client = get_supabase_client()
        urls = client.get_product_images_url(product_id) or {}

        return {
            "original_url_image": (
                urls.get("original_url_image") or None
            ),
            "thumbnail_url_image": (
                urls.get("thumbnail_url_image") or None
            ),
        }

    except Exception:
        return {
            "original_url_image": None,
            "thumbnail_url_image": None,
        }
