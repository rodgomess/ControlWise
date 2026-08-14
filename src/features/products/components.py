from __future__ import annotations

import pandas as pd
import streamlit as st

from src.shared.data_access import get_supabase_client, load_product_image_urls
from src.shared.formatters import integer_value, text_value
from src.features.products.images import clear_pending_product_image, renew_product_image_cache

supabase = get_supabase_client()

def request_product_image_deletion(
    confirmation_key: str,
) -> None:
    st.session_state[confirmation_key] = True


def cancel_product_image_deletion(
    confirmation_key: str,
) -> None:
    st.session_state[confirmation_key] = False


def render_delete_product_image_zone(
    *,
    product_id: str,
    product_name: str,
    mode: str,
    has_image: bool,
) -> None:
    # Chave usada apenas para controlar a exibição da confirmação.
    confirmation_state_key = (
        f"delete_product_image_confirmation_state_{product_id}"
    )
    if not has_image:
        st.session_state.pop(
            confirmation_state_key,
            None,
        )

    st.markdown("##### Remover foto atual")

    deletion_requested = st.session_state.get(
        confirmation_state_key,
        False,
    )

    if not deletion_requested:
        st.button(
            "Deletar foto",
            key=f"delete_product_image_button_{product_id}",
            icon=":material/hide_image:",
            width="stretch",
            disabled=not has_image,
            on_click=request_product_image_deletion,
            args=(confirmation_state_key,),
        )

        if not has_image:
            st.caption(
                "Este produto não possui uma foto para remover."
            )

        return

    st.warning(
        (
            f'A foto de “{product_name}” será removida. '
            "O cadastro do produto será mantido."
        ),
        icon="⚠️",
    )

    cancel_column, confirm_column = st.columns(2)

    with cancel_column:
        st.button(
            "Cancelar",
            key=f"cancel_delete_product_image_button_{product_id}",
            icon=":material/close:",
            width="stretch",
            on_click=cancel_product_image_deletion,
            args=(confirmation_state_key,),
        )

    with confirm_column:
        confirm_delete_image = st.button(
            "Confirmar exclusão da foto",
            key=f"confirm_delete_product_image_button_{product_id}",
            icon=":material/delete_forever:",
            width="stretch",
        )

    if not confirm_delete_image:
        return

    try:
        with st.spinner("Removendo foto..."):
            supabase.delete_product_images(product_id)

        st.session_state.pop(
            confirmation_state_key,
            None,
        )

        clear_pending_product_image(
            mode,
            product_id,
        )

        load_product_image_urls.clear()
        st.cache_data.clear()
        renew_product_image_cache()

        st.session_state["catalog_update_message"] = (
            f'Foto do produto "{product_name}" removida com sucesso.'
        )

        st.session_state["catalog_update_message_level"] = (
            "success"
        )

        st.session_state["catalog_table_version"] += 1

        st.rerun()

    except Exception as error:
        st.error(
            "Não foi possível remover a foto do produto."
        )

        with st.expander("Detalhes técnicos"):
            st.exception(error)


def request_product_deletion(
    confirmation_key: str,
) -> None:
    st.session_state[confirmation_key] = True


def cancel_product_deletion(
    confirmation_key: str,
) -> None:
    st.session_state[confirmation_key] = False


def render_delete_product_zone(
    product_id: str,
    product_name: str,
    has_product_image: bool,
) -> None:
    confirmation_key = (
        f"delete_product_confirmation_state_{product_id}"
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
            key=f"delete_product_button_{product_id}",
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
            key=f"cancel_delete_product_{product_id}",
            icon=":material/close:",
            width="stretch",
            on_click=cancel_product_deletion,
            args=(confirmation_key,),
        )

    with confirm_column:
        confirm_delete = st.button(
            "Confirmar deleção",
            key=f"confirm_delete_product_{product_id}",
            icon=":material/delete_forever:",
            width="stretch",
        )

    if not confirm_delete:
        return

    try:
        with st.spinner("Deletando produto..."):
            supabase.delete_product(product_id)

            if has_product_image:
                try:
                    supabase.delete_product_images(product_id)
                except Exception:
                    # O registro já foi excluído. Uma falha isolada
                    # na limpeza do Storage não deve recriar o produto.
                    pass

        st.session_state.pop(confirmation_key, None)

        load_product_image_urls.clear()
        st.cache_data.clear()

        st.session_state["catalog_update_message"] = (
            f'Produto "{product_name}" deletado com sucesso.'
        )
        st.session_state["catalog_update_message_level"] = "success"
        st.session_state["catalog_table_version"] += 1

        st.rerun()

    except Exception as error:
        st.error(
            "Não foi possível deletar o produto. "
            "Verifique a conexão com o Supabase."
        )

        with st.expander("Detalhes técnicos"):
            st.exception(error)


def clear_plating_metal_and_classification(
    metal_key: str,
    classification_key: str,
) -> None:
    st.session_state.pop(metal_key, None)
    st.session_state.pop(classification_key, None)


def clear_plating_classification(
    classification_key: str,
) -> None:
    st.session_state.pop(classification_key, None)


def render_plating_selectors(
    *,
    mode: str,
    product_id: str,
    product: dict,
    suppliers_dataframe: pd.DataFrame,
    prices_dataframe: pd.DataFrame,
) -> tuple[str | None, str | None, int | None]:
    current_supplier_id = text_value(
        product.get("id_supplier_plating")
    ).strip()
    current_metal = text_value(
        product.get("plating_metal")
    ).strip()
    current_classification_value = integer_value(
        product.get("plating_classification"),
        default=0,
    )
    current_classification = (
        current_classification_value
        if current_classification_value > 0
        else None
    )

    context = (
        f"{mode}_{product_id or 'new'}_"
        f"{st.session_state.get('catalog_table_version', 0)}"
    )

    supplier_key = f"product_plating_supplier_{context}"
    metal_key = f"product_plating_metal_{context}"
    classification_key = (
        f"product_plating_classification_{context}"
    )

    supplier_options_dataframe = (
        suppliers_dataframe[
            ["id_supplier", "supplier_name"]
        ]
        .drop_duplicates(subset=["id_supplier"])
        .sort_values("supplier_name")
    )

    supplier_name_by_id = dict(
        zip(
            supplier_options_dataframe["id_supplier"],
            supplier_options_dataframe["supplier_name"],
        )
    )

    supplier_ids = (
        supplier_options_dataframe["id_supplier"]
        .dropna()
        .astype(str)
        .tolist()
    )
    supplier_options: list[str | None] = [None, *supplier_ids]

    if supplier_key not in st.session_state:
        st.session_state[supplier_key] = (
            current_supplier_id
            if current_supplier_id in supplier_ids
            else None
        )

    if st.session_state.get(supplier_key) not in supplier_options:
        st.session_state[supplier_key] = None

    supplier_column, metal_column, classification_column = st.columns(
        [1.3, 1, 0.8]
    )

    with supplier_column:
        id_supplier_plating = st.selectbox(
            "Fornecedor responsável pelo banho",
            options=supplier_options,
            key=supplier_key,
            format_func=lambda supplier_id: (
                "Selecione um fornecedor"
                if supplier_id is None
                else (
                    f"{supplier_name_by_id.get(supplier_id, '')} "
                    f"· {supplier_id}"
                )
            ),
            on_change=clear_plating_metal_and_classification,
            args=(metal_key, classification_key),
        )

    supplier_prices = prices_dataframe[
        prices_dataframe["id_supplier"].eq(
            text_value(id_supplier_plating).strip()
        )
    ]

    metal_values = sorted(
        supplier_prices["plating_metal"]
        .dropna()
        .astype(str)
        .str.strip()
        .loc[lambda series: series.ne("")]
        .unique()
        .tolist()
    )
    metal_options: list[str | None] = [None, *metal_values]

    if metal_key not in st.session_state:
        use_current_metal = (
            id_supplier_plating == current_supplier_id
            and current_metal in metal_values
        )
        st.session_state[metal_key] = (
            current_metal if use_current_metal else None
        )

    if st.session_state.get(metal_key) not in metal_options:
        st.session_state[metal_key] = None

    with metal_column:
        plating_metal = st.selectbox(
            "Metal do banho",
            options=metal_options,
            key=metal_key,
            disabled=id_supplier_plating is None,
            format_func=lambda metal: (
                "Selecione o metal"
                if metal is None
                else metal
            ),
            on_change=clear_plating_classification,
            args=(classification_key,),
        )

    matching_metal_prices = supplier_prices[
        supplier_prices["_plating_metal_key"].eq(
            text_value(plating_metal).strip().casefold()
        )
    ]

    classification_values = sorted(
        matching_metal_prices["plating_classification"]
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )
    classification_options: list[int | None] = [
        None,
        *classification_values,
    ]

    if classification_key not in st.session_state:
        use_current_classification = (
            id_supplier_plating == current_supplier_id
            and plating_metal == current_metal
            and current_classification in classification_values
        )
        st.session_state[classification_key] = (
            current_classification
            if use_current_classification
            else None
        )

    if (
        st.session_state.get(classification_key)
        not in classification_options
    ):
        st.session_state[classification_key] = None

    with classification_column:
        plating_classification = st.selectbox(
            "Classificação",
            options=classification_options,
            key=classification_key,
            disabled=(
                id_supplier_plating is None
                or plating_metal is None
            ),
            format_func=lambda classification: (
                "Selecione a classe"
                if classification is None
                else f"Classe {classification}"
            ),
        )

    return (
        id_supplier_plating,
        plating_metal,
        plating_classification,
    )
