from __future__ import annotations

from io import BytesIO

import pandas as pd
import streamlit as st

from src.shared.data_access import (
    get_supabase_client, load_plating_prices, load_plating_suppliers,
    load_product_image_urls, load_products,
)
from src.shared.formatters import currency_br, float_value, integer_value, is_missing, text_value
from src.features.products.components import (
    render_delete_product_image_zone, render_delete_product_zone, render_plating_selectors,
)
from src.features.products.images import (
    clear_pending_product_image, render_product_image_editor, renew_product_image_cache,
    upload_product_image_versions, extract_inserted_product_id,
)
from src.features.products.service import (
    EDITABLE_CATEGORIES, build_update_payload, find_plating_price_row,
    prepare_plating_prices_dataframe, prepare_plating_suppliers_dataframe, validate_product,
)

supabase = get_supabase_client()

@st.dialog(
    "Produto",
    width="large",
    icon=":material/inventory_2:",
)
def product_form_dialog(
    mode: str,
    product: dict | None = None,
) -> None:
    is_editing = mode == "edit"
    product = product or {}

    product_id = text_value(product.get("id")).strip()
    current_name = text_value(product.get("name"))
    current_category = text_value(product.get("category"))

    if current_category == "Sem categoria":
        current_category = ""

    current_weight = float_value(product.get("weight"))
    current_base_metal = text_value(product.get("base_metal"))
    current_target_gender = text_value(product.get("target_gender"))
    current_amount = integer_value(product.get("amount"))
    current_purchase_price = float_value(
        product.get("purchase_price")
    )
    current_selling_price = float_value(
        product.get("selling_price")
    )
    current_supplier_product_id = text_value(
        product.get("supplier_product_id")
    )
    current_supplier_name = text_value(
        product.get("supplier_name")
    )
    current_supplier_contact = text_value(
        product.get("supplier_contact")
    )

    current_original_url = text_value(
        product.get("original_url_image")
    ).strip()
    current_thumbnail_url = text_value(
        product.get("thumbnail_url_image")
    ).strip()

    has_product_image = bool(
        current_original_url or current_thumbnail_url
    )

    if current_supplier_name == "Não informado":
        current_supplier_name = ""

    category_options = EDITABLE_CATEGORIES.copy()

    if current_category and current_category not in category_options:
        category_options.insert(0, current_category)

    category_index = (
        category_options.index(current_category)
        if current_category
        else None
    )

    if is_editing:
        st.markdown("### Editar produto")
        st.caption(f"ID do produto: `{product_id}`")
        st.write(
            "Altere os campos necessários e confirme para salvar."
        )
    else:
        st.markdown("### Novo produto")
        st.write(
            "Preencha os dados para cadastrar uma nova peça no estoque."
        )

    (
        pending_main_image,
        pending_thumbnail_image,
    ) = render_product_image_editor(
        mode=mode,
        product_id=product_id,
        current_original_url=current_original_url,
        current_thumbnail_url=current_thumbnail_url,
    )

    if is_editing:
        render_delete_product_image_zone(
            product_id=product_id,
            product_name=current_name,
            mode=mode,
            has_image=has_product_image,
        )

    try:
        suppliers_dataframe = prepare_plating_suppliers_dataframe(
            load_plating_suppliers()
        )
        prices_dataframe = prepare_plating_prices_dataframe(
            load_plating_prices()
        )
    except Exception as error:
        st.error(
            "Não foi possível carregar os fornecedores e preços "
            "de banho."
        )
        with st.expander("Detalhes técnicos"):
            st.exception(error)
        return

    context = (
        f"{mode}_{product_id or 'new'}_"
        f"{st.session_state.get('catalog_table_version', 0)}"
    )

    st.divider()
    st.markdown("#### Custos, peso, banho e preço")

    with st.container(border=True):
        # ========================================================
        # Peso e preços principais
        # ========================================================

        weight_column, purchase_column, selling_column = st.columns(3)

        with weight_column:
            weight = st.number_input(
                "Peso unitário (g)",
                min_value=0.00,
                value=current_weight,
                step=0.10,
                format="%.2f",
                key=f"product_weight_{context}",
            )

        with purchase_column:
            purchase_price = st.number_input(
                "Preço de compra",
                min_value=0.00,
                value=current_purchase_price,
                step=0.50,
                format="%.2f",
                key=f"product_purchase_price_{context}",
            )

        with selling_column:
            selling_price = st.number_input(
                "Preço de venda",
                min_value=0.00,
                value=current_selling_price,
                step=0.50,
                format="%.2f",
                key=f"product_selling_price_{context}",
            )

        st.divider()
        st.markdown("##### Banho e acabamento — opcional")

        # ========================================================
        # Seletores de fornecedor, metal e classificação
        # ========================================================

        (
            id_supplier_plating,
            plating_metal,
            plating_classification,
        ) = render_plating_selectors(
            mode=mode,
            product_id=product_id,
            product=product,
            suppliers_dataframe=suppliers_dataframe,
            prices_dataframe=prices_dataframe,
        )

        selected_price_rows = find_plating_price_row(
            prices_dataframe,
            id_supplier_plating,
            plating_metal,
            plating_classification,
        )

        plating_fields = [
            bool(id_supplier_plating),
            bool(plating_metal),
            plating_classification is not None,
        ]

        has_any_plating_selection = any(plating_fields)
        has_plating_selection = all(plating_fields)

        plating_cost_per_gram: float | None = None
        plating_company_name = ""
        plating_price = 0.0

        # ========================================================
        # Calcula automaticamente o banho
        # ========================================================

        if len(selected_price_rows) == 1:
            selected_price = selected_price_rows.iloc[0]

            raw_plating_cost = selected_price.get(
                "plating_cost"
            )

            if not is_missing(raw_plating_cost):
                plating_cost_per_gram = float(
                    raw_plating_cost
                )

                plating_price = round(
                    float(weight)
                    * plating_cost_per_gram,
                    2,
                )

                supplier_match = suppliers_dataframe[
                    suppliers_dataframe["id_supplier"].eq(
                        text_value(
                            id_supplier_plating
                        ).strip()
                    )
                ]

                if not supplier_match.empty:
                    plating_company_name = text_value(
                        supplier_match.iloc[0][
                            "supplier_name"
                        ]
                    ).strip()

        has_plating_match = (
            plating_cost_per_gram is not None
        )

        # ========================================================
        # Status do cálculo do banho
        # ========================================================

        if has_plating_match:
            st.success(
                (
                    f"**Custo do banho calculado automaticamente:** "
                    f"{currency_br(plating_cost_per_gram)} por grama "
                    f"× {float(weight):.2f} g = "
                    f"**{currency_br(plating_price)}**  \n"
                    f"{plating_company_name} · "
                    f"{plating_metal} · "
                    f"Classe {plating_classification}"
                ),
                icon="✅",
            )

        elif has_any_plating_selection:
            if has_plating_selection:
                st.error(
                    (
                        "Não foi encontrado um preço para essa "
                        "combinação de fornecedor, metal e classificação."
                    ),
                    icon="⚠️",
                )
            else:
                st.warning(
                    (
                        "Para calcular o banho, complete os três campos: "
                        "fornecedor, metal e classificação."
                    ),
                    icon="⚠️",
                )

        else:
            st.info(
                (
                    "O banho é opcional. Sem banho selecionado, "
                    "o custo será considerado R$ 0,00."
                ),
                icon="ℹ️",
            )

        # ========================================================
        # Botão para calcular a prévia
        # ========================================================

        preview_state_key = (
            f"product_financial_preview_{context}"
        )

        pricing_signature = (
            round(float(weight), 4),
            round(float(purchase_price), 2),
            round(float(selling_price), 2),
            text_value(id_supplier_plating).strip(),
            text_value(plating_metal).strip().casefold(),
            integer_value(
                plating_classification,
                default=0,
            ),
            round(float(plating_price), 2),
        )

        calculate_clicked = st.button(
            "Calcular custos, lucro e margem",
            key=f"calculate_product_values_{context}",
            icon=":material/calculate:",
            type="primary",
            width="stretch",
        )

        if calculate_clicked:
            preview_errors: list[str] = []

            if (
                has_any_plating_selection
                and not has_plating_selection
            ):
                preview_errors.append(
                    "Complete fornecedor, metal e classificação "
                    "ou deixe os três campos vazios."
                )

            if (
                has_plating_selection
                and not has_plating_match
            ):
                preview_errors.append(
                    "Não existe preço cadastrado para a combinação "
                    "de banho selecionada."
                )

            if float(selling_price) <= 0:
                preview_errors.append(
                    "Informe um preço de venda maior que zero."
                )

            if preview_errors:
                st.session_state.pop(
                    preview_state_key,
                    None,
                )

                for error in preview_errors:
                    st.error(error)

            else:
                preview_total_cost = round(
                    float(purchase_price)
                    + float(plating_price),
                    2,
                )

                preview_profit = round(
                    float(selling_price)
                    - preview_total_cost,
                    2,
                )

                preview_margin = (
                    preview_profit
                    / float(selling_price)
                    * 100
                    if float(selling_price) > 0
                    else 0.0
                )

                st.session_state[preview_state_key] = {
                    "signature": pricing_signature,
                    "purchase_price": float(
                        purchase_price
                    ),
                    "plating_price": float(
                        plating_price
                    ),
                    "total_cost": preview_total_cost,
                    "selling_price": float(
                        selling_price
                    ),
                    "profit": preview_profit,
                    "margin": preview_margin,
                }

        # ========================================================
        # Exibe o resultado persistido
        # ========================================================

        preview_data = st.session_state.get(
            preview_state_key
        )

        if (
            preview_data
            and preview_data.get("signature")
            != pricing_signature
        ):
            st.session_state.pop(
                preview_state_key,
                None,
            )

            preview_data = None

            st.caption(
                (
                    "Os valores foram alterados. Clique novamente em "
                    "“Calcular custos, lucro e margem”."
                )
            )

        if preview_data:
            st.markdown("##### Resultado da simulação")

            (
                purchase_metric,
                plating_metric,
                total_metric,
            ) = st.columns(3)

            with purchase_metric:
                st.metric(
                    "Custo de compra",
                    currency_br(
                        preview_data["purchase_price"]
                    ),
                )

            with plating_metric:
                st.metric(
                    "Custo do banho",
                    currency_br(
                        preview_data["plating_price"]
                    ),
                )

            with total_metric:
                st.metric(
                    "Custo total",
                    currency_br(
                        preview_data["total_cost"]
                    ),
                )

            (
                selling_metric,
                profit_metric,
                margin_metric,
            ) = st.columns(3)

            with selling_metric:
                st.metric(
                    "Preço de venda",
                    currency_br(
                        preview_data["selling_price"]
                    ),
                )

            with profit_metric:
                st.metric(
                    "Lucro estimado",
                    currency_br(
                        preview_data["profit"]
                    ),
                )

            with margin_metric:
                st.metric(
                    "Margem estimada",
                    f"{preview_data['margin']:.1f}%",
                )

    form_key = f"product_form_{context}"

    with st.form(form_key):
        st.markdown("#### Identificação e estoque")

        name_column, category_column = st.columns([1.5, 1])

        with name_column:
            name = st.text_input(
                "Nome da peça",
                value=current_name,
                placeholder="Ex.: Pulseira Aurora Dourada",
            )

        with category_column:
            category = st.selectbox(
                "Categoria",
                options=category_options,
                index=category_index,
                placeholder="Selecione uma categoria",
            )

        amount_column, gender_column = st.columns(2)

        with amount_column:
            amount = st.number_input(
                "Quantidade em estoque",
                min_value=0,
                value=current_amount,
                step=1,
            )

        with gender_column:
            target_gender = st.text_input(
                "Gênero / público-alvo",
                value=current_target_gender,
                placeholder="Ex.: Feminino ou Unissex",
            )

        base_metal = st.text_input(
            "Metal base da peça",
            value=current_base_metal,
            placeholder="Ex.: Latão, cobre ou aço inox",
        )


        st.divider()
        st.markdown("#### Fornecedor da peça")

        supplier_column, supplier_product_column = st.columns(2)

        with supplier_column:
            supplier_name = st.text_input(
                "Nome do fornecedor",
                value=current_supplier_name,
                placeholder="Ex.: Joias Horizonte",
            )

        with supplier_product_column:
            supplier_product_id = st.text_input(
                "ID do produto no fornecedor",
                value=current_supplier_product_id,
                placeholder="Ex.: PL-4587",
            )

        supplier_contact = st.text_input(
            "Contato do fornecedor",
            value=current_supplier_contact,
            placeholder="Ex.: (11) 99999-1234",
        )

        submit_label = (
            "Salvar alterações"
            if is_editing
            else "Cadastrar produto"
        )
        submit_icon = (
            ":material/save:"
            if is_editing
            else ":material/add_circle:"
        )

        submitted = st.form_submit_button(
            submit_label,
            icon=submit_icon,
            type="primary",
            width="stretch",
        )

    if is_editing:
        render_delete_product_zone(
            product_id=product_id,
            product_name=current_name,
            has_product_image=has_product_image,
        )

    if not submitted:
        return

    validation_errors = validate_product(
        name=name,
        category=category,
        amount=int(amount),
        weight=float(weight),
        purchase_price=float(purchase_price),
        plating_price=float(plating_price),
        selling_price=float(selling_price),
        id_supplier_plating=id_supplier_plating,
        plating_metal=plating_metal,
        plating_classification=plating_classification,
        has_plating_match=has_plating_match,
    )

    if validation_errors:
        for error in validation_errors:
            st.error(error)
        return

    product_data = {
        "name": name.strip(),
        "category": category,
        "weight": round(float(weight), 2),
        "base_metal": base_metal.strip() or None,
        "target_gender": target_gender.strip() or None,

        "id_supplier_plating": (
            str(id_supplier_plating).strip()
            if has_plating_selection
            else None
        ),

        "plating_company_name": (
            plating_company_name
            if has_plating_selection
            else None
        ),

        "plating_metal": (
            str(plating_metal).strip()
            if has_plating_selection
            else None
        ),

        "plating_classification": (
            int(plating_classification)
            if has_plating_selection
            else None
        ),

        "plating_price": (
            round(float(plating_price), 2)
            if has_plating_match
            else 0.0
        ),

        "amount": int(amount),
        "purchase_price": round(
            float(purchase_price),
            2,
        ),
        "selling_price": round(
            float(selling_price),
            2,
        ),
        "supplier_product_id": (
            supplier_product_id.strip() or None
        ),
        "supplier_name": (
            supplier_name.strip() or None
        ),
        "supplier_contact": (
            supplier_contact.strip() or None
        ),
    }

    has_pending_image = bool(
        pending_main_image and pending_thumbnail_image
    )
    saved_product_id = product_id

    try:
        with st.spinner("Salvando produto..."):
            if is_editing:
                update_payload = build_update_payload(
                    original_product=product,
                    edited_product=product_data,
                )

                if not update_payload and not has_pending_image:
                    st.info(
                        "Nenhuma alteração foi identificada.",
                        icon="ℹ️",
                    )
                    return

                if update_payload:
                    supabase.update_product(
                        product_id,
                        update_payload,
                    )
            else:
                insert_response = supabase.insert_product(
                    product_data
                )

                if has_pending_image:
                    saved_product_id = extract_inserted_product_id(
                        insert_response
                    )

    except Exception as error:
        action = "atualizar" if is_editing else "cadastrar"

        st.error(
            f"Não foi possível {action} o produto. "
            "Verifique a conexão com o Supabase."
        )

        with st.expander("Detalhes técnicos"):
            st.exception(error)

        return

    image_upload_error: Exception | None = None

    if has_pending_image:
        try:
            with st.spinner("Enviando foto do produto..."):
                upload_product_image_versions(
                    saved_product_id,
                    pending_main_image,
                    pending_thumbnail_image,
                )
        except Exception as error:
            image_upload_error = error

    load_product_image_urls.clear()
    load_products.clear()
    st.cache_data.clear()

    renew_product_image_cache()

    clear_pending_product_image(
        mode,
        product_id,
    )

    st.session_state["catalog_table_version"] += 1

    if image_upload_error:
        st.session_state["catalog_update_message"] = (
            f'Produto "{name.strip()}" salvo, mas a foto não '
            "pôde ser enviada. Abra a edição e tente novamente."
        )
        st.session_state["catalog_update_message_level"] = "warning"
    else:
        action_message = (
            "atualizado" if is_editing else "cadastrado"
        )
        st.session_state["catalog_update_message"] = (
            f'Produto "{name.strip()}" '
            f"{action_message} com sucesso."
        )
        st.session_state["catalog_update_message_level"] = "success"

    st.rerun()


@st.dialog(
    "Foto do produto",
    width="large",
    icon=":material/photo:",
)
def product_image_dialog(
    product: dict,
) -> None:
    product_name = text_value(
        product.get("name")
    ).strip()

    original_url = text_value(
        product.get("original_url_image")
    ).strip()

    thumbnail_url = text_value(
        product.get("thumbnail_url_image")
    ).strip()

    image_url = original_url or thumbnail_url

    if not image_url:
        st.info(
            "Este produto não possui uma foto cadastrada.",
            icon="ℹ️",
        )
        return

    st.markdown(f"### {product_name}")

    left_column, image_column, right_column = st.columns(
        [1, 4, 1]
    )

    with image_column:
        st.image(
            image_url,
            caption="Imagem principal — 800 × 800",
            width=650,
        )
