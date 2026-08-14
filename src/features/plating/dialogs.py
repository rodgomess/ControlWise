from __future__ import annotations

import hashlib

import pandas as pd
import streamlit as st

from src.shared.data_access import get_supabase_client, load_plating_prices, load_plating_suppliers
from src.features.plating.service import (
    build_plating_price_update_payload, build_update_payload, validate_plating_price, validate_supplier,
)

supabase = get_supabase_client()

def request_supplier_deletion(
    confirmation_state_key: str,
) -> None:
    st.session_state[confirmation_state_key] = True


def cancel_supplier_deletion(
    confirmation_state_key: str,
) -> None:
    st.session_state[confirmation_state_key] = False


def render_delete_supplier_zone(
    supplier_id: str,
    supplier_name: str,
) -> None:
    confirmation_state_key = (
        f"delete_supplier_confirmation_state_{supplier_id}"
    )

    st.divider()
    st.markdown("#### Zona de perigo")

    st.caption(
        "A exclusão remove definitivamente o fornecedor "
        "do banco de dados."
    )

    deletion_requested = st.session_state.get(
        confirmation_state_key,
        False,
    )

    if not deletion_requested:
        st.button(
            "Deletar fornecedor",
            key=f"delete_supplier_button_{supplier_id}",
            icon=":material/delete:",
            width="stretch",
            on_click=request_supplier_deletion,
            args=(confirmation_state_key,),
        )
        return

    st.error(
        (
            f'Você realmente deseja deletar o fornecedor '
            f'“{supplier_name}”? Esta ação não poderá ser desfeita.'
        ),
        icon="⚠️",
    )

    cancel_column, confirm_column = st.columns(2)

    with cancel_column:
        st.button(
            "Cancelar",
            key=f"cancel_delete_supplier_button_{supplier_id}",
            icon=":material/close:",
            width="stretch",
            on_click=cancel_supplier_deletion,
            args=(confirmation_state_key,),
        )

    with confirm_column:
        confirm_delete = st.button(
            "Confirmar exclusão",
            key=f"confirm_delete_supplier_button_{supplier_id}",
            icon=":material/delete_forever:",
            width="stretch",
        )

    if not confirm_delete:
        return

    try:
        with st.spinner("Deletando fornecedor..."):
            supabase.delete_suppliers_plating(
                supplier_id
            )

            # Confirma se o registro realmente foi removido.
            remaining_suppliers = (
                supabase.load_suppliers_plating() or []
            )

            supplier_still_exists = any(
                str(item.get("id_supplier", "")).strip()
                == str(supplier_id).strip()
                for item in remaining_suppliers
            )

            if supplier_still_exists:
                raise RuntimeError(
                    "O Supabase não removeu o fornecedor. "
                    "Verifique as políticas RLS, a função de exclusão "
                    "e os vínculos com a tabela de preços."
                )

        st.session_state.pop(
            confirmation_state_key,
            None,
        )

        load_plating_suppliers.clear()
        load_plating_prices.clear()

        st.session_state["plating_suppliers_message"] = (
            f'Fornecedor "{supplier_name}" deletado com sucesso.'
        )

        st.session_state[
            "plating_suppliers_table_version"
        ] += 1

        st.session_state[
            "plating_prices_table_version"
        ] += 1

        st.rerun()

    except Exception as error:
        st.error(
            "Não foi possível deletar o fornecedor."
        )

        with st.expander("Detalhes técnicos"):
            st.exception(error)


@st.dialog(
    "Fornecedor de banho",
    width="medium",
    icon=":material/factory:",
)
def supplier_form_dialog(
    mode: str,
    supplier: dict | None = None,
) -> None:
    is_editing = mode == "edit"

    supplier = supplier or {}

    supplier_id = str(
        supplier.get("id_supplier") or ""
    )

    current_name = str(
        supplier.get("supplier_name") or ""
    )

    current_contact = str(
        supplier.get("supplier_contact") or ""
    )

    current_notes = str(
        supplier.get("notes") or ""
    )

    if is_editing:
        st.markdown("### Editar fornecedor")

        st.caption(
            f"Fornecedor selecionado: `{supplier_id}`"
        )

        st.write(
            "Altere os dados necessários e salve as modificações."
        )

    else:
        st.markdown("### Novo fornecedor")

        st.write(
            "Preencha os dados para cadastrar uma nova empresa "
            "responsável pelo banho das peças."
        )

    form_key = (
        f"plating_supplier_form_{mode}_{supplier_id or 'new'}"
    )

    with st.form(form_key):
        supplier_name = st.text_input(
            "Nome do fornecedor",
            value=current_name,
            placeholder="Ex.: Banhos Dourados São Paulo",
        )

        supplier_contact = st.text_input(
            "Contato do fornecedor",
            value=current_contact,
            placeholder="Ex.: (11) 99999-1234",
        )

        notes = st.text_area(
            "Observações",
            value=current_notes,
            placeholder=(
                "Informações adicionais sobre o fornecedor."
            ),
        )

        submit_label = (
            "Salvar alterações"
            if is_editing
            else "Cadastrar fornecedor"
        )

        submit_icon = (
            ":material/save:"
            if is_editing
            else ":material/add_business:"
        )

        submitted = st.form_submit_button(
            submit_label,
            icon=submit_icon,
            type="primary",
            width="stretch",
        )

    if is_editing:
        render_delete_supplier_zone(
            supplier_id=supplier_id,
            supplier_name=current_name,
        )

    if not submitted:
        return

    validation_errors = validate_supplier(
        supplier_name=supplier_name
    )

    if validation_errors:
        for error in validation_errors:
            st.error(error)

        return

    supplier_data = {
        "supplier_name": supplier_name.strip(),
        "supplier_contact": (
            supplier_contact.strip() or None
        ),
        "notes": notes.strip() or None,
    }

    try:
        with st.spinner("Salvando fornecedor..."):
            if is_editing:
                update_payload = build_update_payload(
                    original_supplier=supplier,
                    edited_supplier=supplier_data,
                )

                if not update_payload:
                    st.info(
                        "Nenhuma alteração foi identificada.",
                        icon="ℹ️",
                    )
                    return

                supabase.update_suppliers_plating(
                    supplier_id,
                    update_payload,
                )

                success_message = (
                    f'Fornecedor "{supplier_name.strip()}" '
                    f"atualizado com sucesso."
                )

            else:
                supabase.insert_suppliers_plating(
                    supplier_data
                )

                success_message = (
                    f'Fornecedor "{supplier_name.strip()}" '
                    f"cadastrado com sucesso."
                )

        st.cache_data.clear()

        st.session_state[
            "plating_suppliers_message"
        ] = success_message

        # Altera a chave da tabela para remover a seleção anterior.
        st.session_state[
            "plating_suppliers_table_version"
        ] += 1

        # Fecha o popup e recarrega a aplicação.
        st.rerun()

    except Exception as error:
        action = (
            "atualizar"
            if is_editing
            else "cadastrar"
        )

        st.error(
            f"Não foi possível {action} o fornecedor. "
            "Verifique a conexão com o Supabase."
        )

        with st.expander("Detalhes técnicos"):
            st.exception(error)


def request_plating_price_deletion(
    confirmation_state_key: str,
) -> None:
    st.session_state[confirmation_state_key] = True


def cancel_plating_price_deletion(
    confirmation_state_key: str,
) -> None:
    st.session_state[confirmation_state_key] = False


def render_delete_plating_price_zone(
    *,
    id_supplier: str,
    plating_metal: str,
    plating_classification: int,
    supplier_name: str,
) -> None:
    composite_key = (
        f"{id_supplier}|"
        f"{plating_metal}|"
        f"{plating_classification}"
    )

    key_hash = hashlib.md5(
        composite_key.encode("utf-8")
    ).hexdigest()[:12]

    confirmation_state_key = (
        f"delete_plating_price_confirmation_{key_hash}"
    )

    st.divider()
    st.markdown("#### Zona de perigo")

    st.caption(
        "A exclusão remove definitivamente esta regra de preço."
    )

    deletion_requested = st.session_state.get(
        confirmation_state_key,
        False,
    )

    if not deletion_requested:
        st.button(
            "Deletar preço",
            key=f"delete_plating_price_button_{key_hash}",
            icon=":material/delete:",
            width="stretch",
            on_click=request_plating_price_deletion,
            args=(confirmation_state_key,),
        )
        return

    st.error(
        (
            f"Você realmente deseja excluir o preço de "
            f"“{plating_metal}”, classe "
            f"{plating_classification}, do fornecedor "
            f"“{supplier_name}”?"
        ),
        icon="⚠️",
    )

    cancel_column, confirm_column = st.columns(2)

    with cancel_column:
        st.button(
            "Cancelar",
            key=f"cancel_plating_price_button_{key_hash}",
            icon=":material/close:",
            width="stretch",
            on_click=cancel_plating_price_deletion,
            args=(confirmation_state_key,),
        )

    with confirm_column:
        confirm_delete = st.button(
            "Confirmar exclusão",
            key=f"confirm_delete_plating_price_button_{key_hash}",
            icon=":material/delete_forever:",
            width="stretch",
        )

    if not confirm_delete:
        return

    try:
        with st.spinner("Excluindo preço..."):
            supabase.delete_suppliers_plating_prices(
                id_supplier,
                plating_metal,
                plating_classification,
            )

            remaining_prices = (
                supabase.load_suppliers_plating_prices()
                or []
            )

            price_still_exists = any(
                (
                    str(
                        item.get(
                            "id_supplier",
                            "",
                        )
                    ).strip()
                    == str(id_supplier).strip()
                )
                and (
                    str(
                        item.get(
                            "plating_metal",
                            "",
                        )
                    ).strip().casefold()
                    == str(
                        plating_metal
                    ).strip().casefold()
                )
                and (
                    int(
                        item.get(
                            "plating_classification",
                            0,
                        )
                        or 0
                    )
                    == int(plating_classification)
                )
                for item in remaining_prices
            )

            if price_still_exists:
                raise RuntimeError(
                    "O Supabase não removeu o preço."
                )

        st.session_state.pop(
            confirmation_state_key,
            None,
        )

        load_plating_prices.clear()

        st.session_state[
            "plating_prices_message"
        ] = "Preço excluído com sucesso."

        st.session_state[
            "plating_prices_table_version"
        ] += 1

        st.rerun()

    except Exception as error:
        st.error(
            "Não foi possível excluir o preço."
        )

        with st.expander("Detalhes técnicos"):
            st.exception(error)


@st.dialog(
    "Preço e classificação",
    width="medium",
    icon=":material/payments:",
)
def plating_price_form_dialog(
    mode: str,
    suppliers_dataframe: pd.DataFrame,
    prices_dataframe: pd.DataFrame,
    price: dict | None = None,
) -> None:
    is_editing = mode == "edit"
    price = price or {}

    original_supplier_id = str(
        price.get("id_supplier") or ""
    ).strip()

    original_metal = str(
        price.get("plating_metal") or ""
    ).strip()

    original_classification = int(
        price.get("plating_classification") or 1
    )

    current_cost = float(
        price.get("plating_cost") or 0
    )

    supplier_options_dataframe = (
        suppliers_dataframe[
            [
                "id_supplier",
                "supplier_name",
            ]
        ]
        .drop_duplicates(
            subset=["id_supplier"]
        )
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
        .astype(str)
        .tolist()
    )

    supplier_options = [
        "",
        *supplier_ids,
    ]

    current_supplier_index = (
        supplier_options.index(
            original_supplier_id
        )
        if original_supplier_id
        in supplier_options
        else 0
    )

    if is_editing:
        st.markdown("### Editar preço")

        st.caption(
            (
                f"Chave atual: `{original_supplier_id}` · "
                f"`{original_metal}` · "
                f"`{original_classification}`"
            )
        )
    else:
        st.markdown("### Cadastrar preço")

    composite_key = (
        f"{original_supplier_id}|"
        f"{original_metal}|"
        f"{original_classification}"
    )

    key_hash = hashlib.md5(
        composite_key.encode("utf-8")
    ).hexdigest()[:12]

    form_key = (
        f"plating_price_form_{mode}_{key_hash}"
    )

    with st.form(form_key):
        id_supplier = st.selectbox(
            "Fornecedor",
            options=supplier_options,
            index=current_supplier_index,
            format_func=lambda supplier_id: (
                "Selecione um fornecedor"
                if not supplier_id
                else (
                    f"{supplier_name_by_id.get(supplier_id, '')} "
                    f"· {supplier_id}"
                )
            ),
        )

        plating_metal = st.text_input(
            "Metal do banho",
            value=original_metal,
            placeholder="Ex.: Ouro 18k",
        )

        classification_column, cost_column = (
            st.columns(2)
        )

        with classification_column:
            plating_classification = (
                st.number_input(
                    "Classificação",
                    min_value=1,
                    max_value=20,
                    value=original_classification,
                    step=1,
                )
            )

        with cost_column:
            plating_cost = st.number_input(
                "Preço por grama",
                min_value=0.00,
                value=current_cost,
                step=0.10,
                format="%.2f",
            )

        submitted = st.form_submit_button(
            (
                "Salvar alterações"
                if is_editing
                else "Cadastrar preço"
            ),
            icon=(
                ":material/save:"
                if is_editing
                else ":material/add_circle:"
            ),
            type="primary",
            width="stretch",
        )

    if is_editing:
        supplier_name = supplier_name_by_id.get(
            original_supplier_id,
            original_supplier_id,
        )

        render_delete_plating_price_zone(
            id_supplier=original_supplier_id,
            plating_metal=original_metal,
            plating_classification=(
                original_classification
            ),
            supplier_name=supplier_name,
        )

    if not submitted:
        return

    validation_errors = validate_plating_price(
        id_supplier=id_supplier,
        plating_metal=plating_metal,
        plating_classification=int(
            plating_classification
        ),
        plating_cost=float(plating_cost),
    )

    if validation_errors:
        for error in validation_errors:
            st.error(error)

        return

    normalized_supplier_id = str(
        id_supplier
    ).strip()

    normalized_metal = (
        plating_metal.strip()
    )

    selected_classification = int(
        plating_classification
    )

    duplicate_mask = (
        prices_dataframe["id_supplier"]
        .astype(str)
        .str.strip()
        .eq(normalized_supplier_id)
        &
        prices_dataframe["plating_metal"]
        .astype(str)
        .str.strip()
        .str.casefold()
        .eq(normalized_metal.casefold())
        &
        prices_dataframe[
            "plating_classification"
        ]
        .eq(selected_classification)
        .fillna(False)
    )

    if is_editing:
        original_row_mask = (
            prices_dataframe["id_supplier"]
            .astype(str)
            .str.strip()
            .eq(original_supplier_id)
            &
            prices_dataframe["plating_metal"]
            .astype(str)
            .str.strip()
            .str.casefold()
            .eq(original_metal.casefold())
            &
            prices_dataframe[
                "plating_classification"
            ]
            .eq(original_classification)
            .fillna(False)
        )

        duplicate_mask = (
            duplicate_mask
            & ~original_row_mask
        )

    if duplicate_mask.any():
        st.error(
            (
                "Já existe um preço cadastrado para essa "
                "combinação de fornecedor, metal e "
                "classificação."
            ),
            icon="⚠️",
        )
        return

    price_data = {
        "id_supplier": normalized_supplier_id,
        "plating_metal": normalized_metal,
        "plating_classification": (
            selected_classification
        ),
        "plating_cost": round(
            float(plating_cost),
            2,
        ),
    }

    try:
        with st.spinner("Salvando preço..."):
            if is_editing:
                update_payload = (
                    build_plating_price_update_payload(
                        original_price=price,
                        edited_price=price_data,
                    )
                )

                if not update_payload:
                    st.info(
                        "Nenhuma alteração foi identificada.",
                        icon="ℹ️",
                    )
                    return

                supabase.update_suppliers_plating_prices(
                    original_supplier_id,
                    original_metal,
                    original_classification,
                    update_payload,
                )

                success_message = (
                    "Preço atualizado com sucesso."
                )

            else:
                supabase.insert_suppliers_plating_prices(
                    price_data
                )

                success_message = (
                    "Preço cadastrado com sucesso."
                )

        load_plating_prices.clear()

        st.session_state[
            "plating_prices_message"
        ] = success_message

        st.session_state[
            "plating_prices_table_version"
        ] += 1

        st.rerun()

    except Exception as error:
        action = (
            "atualizar"
            if is_editing
            else "cadastrar"
        )

        st.error(
            f"Não foi possível {action} o preço. "
            "Verifique se essa combinação já existe."
        )

        with st.expander("Detalhes técnicos"):
            st.exception(error)
