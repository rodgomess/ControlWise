from __future__ import annotations

from datetime import date
import hashlib

import pandas as pd
import streamlit as st

from src.services.supabase import SupabaseClient
from ui.styles import render_page_hero


EXPECTED_COLUMNS = [
    "supplier_number",
    "id_supplier",
    "supplier_name",
    "plating_metal",
    "plating_classification",
    "plating_cost",
    "supplier_contact",
    "insert_date",
    "updated_date",
]

DATE_COLUMNS = [
    "insert_date",
    "updated_date",
]

EDITABLE_FIELDS = [
    "supplier_name",
    "plating_metal",
    "plating_classification",
    "plating_cost",
    "supplier_contact",
]


if "plating_suppliers_table_version" not in st.session_state:
    st.session_state["plating_suppliers_table_version"] = 0


# ============================================================
# Supabase
# ============================================================

@st.cache_resource
def get_supabase_client() -> SupabaseClient:
    return SupabaseClient()


@st.cache_data(ttl=60, show_spinner=False)
def load_plating_suppliers() -> list[dict]:
    client = get_supabase_client()

    return client.load_suppliers_plating() or []


supabase = get_supabase_client()


# ============================================================
# Preparação dos dados
# ============================================================

def prepare_suppliers_dataframe(
    suppliers: list[dict],
) -> pd.DataFrame:
    dataframe = pd.DataFrame(suppliers)

    for column in EXPECTED_COLUMNS:
        if column not in dataframe.columns:
            dataframe[column] = None

    dataframe = dataframe[EXPECTED_COLUMNS].copy()

    dataframe["supplier_number"] = pd.to_numeric(
        dataframe["supplier_number"],
        errors="coerce",
    ).astype("Int64")

    dataframe["plating_classification"] = pd.to_numeric(
        dataframe["plating_classification"],
        errors="coerce",
    ).astype("Int64")

    dataframe["plating_cost"] = pd.to_numeric(
        dataframe["plating_cost"],
        errors="coerce",
    ).fillna(0.0)

    for column in DATE_COLUMNS:
        dataframe[column] = pd.to_datetime(
            dataframe[column],
            errors="coerce",
            utc=True,
        ).dt.tz_convert("America/Sao_Paulo")

    text_columns = [
        "id_supplier",
        "supplier_name",
        "plating_metal",
        "supplier_contact",
    ]

    for column in text_columns:
        dataframe[column] = dataframe[column].fillna("")

    return dataframe


def currency_br(value: float) -> str:
    return (
        f"R$ {value:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def normalize_supplier_value(
    field: str,
    value,
):
    if value is None or pd.isna(value):
        value = None

    if field in {
        "supplier_name",
        "plating_metal",
        "supplier_contact",
    }:
        normalized_value = str(value or "").strip()

        if field == "supplier_contact" and not normalized_value:
            return None

        return normalized_value

    if field == "plating_classification":
        return int(value or 1)

    if field == "plating_cost":
        return round(float(value or 0), 2)

    return value


def build_update_payload(
    original_supplier: dict,
    edited_supplier: dict,
) -> dict:
    """
    Retorna somente os campos realmente alterados.

    O id_supplier é enviado separadamente para
    update_suppliers_plating().
    """
    payload: dict = {}

    for field in EDITABLE_FIELDS:
        original_value = normalize_supplier_value(
            field,
            original_supplier.get(field),
        )

        edited_value = normalize_supplier_value(
            field,
            edited_supplier.get(field),
        )

        if original_value != edited_value:
            payload[field] = edited_value

    return payload


def validate_supplier(
    supplier_name: str,
    plating_metal: str,
    plating_classification: int,
    plating_cost: float,
) -> list[str]:
    errors: list[str] = []

    if not supplier_name.strip():
        errors.append("Informe o nome do fornecedor.")

    if not plating_metal.strip():
        errors.append("Informe o metal ou tipo de banho.")

    if plating_classification < 1 or plating_classification > 5:
        errors.append(
            "A classificação do banho deve estar entre 1 e 5."
        )

    if plating_cost < 0:
        errors.append(
            "O custo do banho não pode ser negativo."
        )

    return errors


# ============================================================
# Popup compartilhado: criar e editar
# ============================================================

def request_product_deletion(confirmation_key: str) -> None:
    """
    Exibe a etapa de confirmação da exclusão.
    """
    st.session_state[confirmation_key] = True


def cancel_product_deletion(confirmation_key: str) -> None:
    """
    Cancela a exclusão e esconde a confirmação.
    """
    st.session_state[confirmation_key] = False

def render_delete_supplier_zone(
    supplier_id: str,
    supplier_name: str,
) -> None:
    """
    Renderiza a zona de exclusão com confirmação em duas etapas.
    """

    confirmation_key = (
        f"confirm_delete_product_{supplier_id}"
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
            key="delete_product_button",
            icon=":material/delete:",
            width="stretch",
            on_click=request_product_deletion,
            args=(confirmation_key,),
        )

        return

    st.error(
        (
            f'Você realmente deseja deletar o produto '
            f'“{supplier_name}”? Esta ação não poderá ser desfeita.'
        ),
        icon="⚠️",
    )

    cancel_column, confirm_column = st.columns(2)

    with cancel_column:
        st.button(
            "Cancelar",
            key="cancel_delete_product_button",
            icon=":material/close:",
            width="stretch",
            on_click=cancel_product_deletion,
            args=(confirmation_key,),
        )

    with confirm_column:
        confirm_delete = st.button(
            "Confirmar deleção",
            key="confirm_delete_product_button",
            icon=":material/delete_forever:",
            width="stretch",
        )

    if not confirm_delete:
        return

    try:
        with st.spinner("Deletando fornecedor..."):
            supabase.delete_suppliers_plating(supplier_id)

        # Remove o estado da confirmação.
        st.session_state.pop(
            confirmation_key,
            None,
        )

        # Limpa o cache de load_products().
        st.cache_data.clear()

        # Exibe a mensagem depois que o popup fechar.
        st.session_state["catalog_update_message"] = (
            f'Fornecedor "{supplier_name}" deletado com sucesso.'
        )

        # Altera a chave da tabela e remove a seleção anterior.
        st.session_state["plating_suppliers_table_version"] += 1

        # Fecha o popup e recarrega o catálogo.
        st.rerun(scope="app")

    except Exception as error:
        st.error(
            "Não foi possível deletar o produto. "
            "Verifique a conexão com o Supabase."
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

    current_metal = str(
        supplier.get("plating_metal") or ""
    )

    current_classification = int(
        supplier.get("plating_classification") or 3
    )

    current_cost = float(
        supplier.get("plating_cost") or 0
    )

    current_contact = str(
        supplier.get("supplier_contact") or ""
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

        plating_metal = st.text_input(
            "Metal ou tipo de banho",
            value=current_metal,
            placeholder="Ex.: Ouro 18k",
            help=(
                "Informe o acabamento oferecido pelo fornecedor, "
                "como Ouro 18k, Ouro 24k, Prata ou Ródio."
            ),
        )

        classification_column, cost_column = st.columns(2)

        with classification_column:
            plating_classification = st.number_input(
                "Classificação do banho",
                min_value=1,
                max_value=5,
                value=current_classification,
                step=1,
                help=(
                    "Classificação de qualidade do banho, "
                    "entre 1 e 5."
                ),
            )

        with cost_column:
            plating_cost = st.number_input(
                "Custo do banho",
                min_value=0.00,
                value=current_cost,
                step=0.50,
                format="%.2f",
            )

        supplier_contact = st.text_input(
            "Contato do fornecedor",
            value=current_contact,
            placeholder="Ex.: (11) 99999-1234",
        )

        st.info(
            (
                f"Valor informado para o serviço: "
                f"**{currency_br(float(plating_cost))}**"
            ),
            icon="💰",
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
        supplier_name=supplier_name,
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

    supplier_data = {
        "supplier_name": supplier_name.strip(),
        "plating_metal": plating_metal.strip(),
        "plating_classification": int(
            plating_classification
        ),
        "plating_cost": round(
            float(plating_cost),
            2,
        ),
        "supplier_contact": (
            supplier_contact.strip() or None
        ),
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


# ============================================================
# Filtros
# ============================================================

def apply_supplier_filters(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    filtered = dataframe.copy()

    minimum_cost_available = float(
        dataframe["plating_cost"].min()
    )

    maximum_cost_available = float(
        dataframe["plating_cost"].max()
    )

    valid_insert_dates = dataframe[
        "insert_date"
    ].dropna()

    if valid_insert_dates.empty:
        minimum_date = date.today()
        maximum_date = date.today()

    else:
        minimum_date = valid_insert_dates.min().date()
        maximum_date = valid_insert_dates.max().date()

    with st.container(border=True):
        st.markdown(
            """
            <div class="filter-panel-title">
                Filtros de fornecedores
            </div>
            """,
            unsafe_allow_html=True,
        )

        search_column, metal_column, contact_column = (
            st.columns(3)
        )

        with search_column:
            search_term = st.text_input(
                "Buscar fornecedor ou código",
                placeholder=(
                    "Digite o nome ou ID do fornecedor"
                ),
                icon=":material/search:",
            )

        with metal_column:
            metal_filter = st.text_input(
                "Metal ou tipo de banho",
                placeholder="Ex.: Ouro 18k",
            )

        with contact_column:
            contact_filter = st.text_input(
                "Contato",
                placeholder="Telefone ou outro contato",
            )

        cost_min_column, cost_max_column = st.columns(2)
        class_min_column, class_max_column = st.columns(2)

        with cost_min_column:
            minimum_cost = st.number_input(
                "Custo mínimo",
                min_value=0.00,
                value=minimum_cost_available,
                step=0.50,
                format="%.2f",
            )

        with cost_max_column:
            maximum_cost = st.number_input(
                "Custo máximo",
                min_value=0.00,
                value=maximum_cost_available,
                step=0.50,
                format="%.2f",
            )

        with class_min_column:
            minimum_classification = st.number_input(
                "Classificação mínima",
                min_value=1,
                max_value=5,
                value=1,
                step=1,
            )

        with class_max_column:
            maximum_classification = st.number_input(
                "Classificação máxima",
                min_value=1,
                max_value=20,
                value=20,
                step=1,
            )

        date_column, sort_column, direction_column = (
            st.columns([1.3, 1, 1])
        )

        with date_column:
            selected_dates = st.date_input(
                "Período de cadastro",
                value=(minimum_date, maximum_date),
                min_value=minimum_date,
                max_value=maximum_date,
                format="DD/MM/YYYY",
            )

        sort_labels = {
            "supplier_number": "Número interno",
            "id_supplier": "Código do fornecedor",
            "supplier_name": "Nome do fornecedor",
            "plating_metal": "Metal do banho",
            "plating_classification": (
                "Classificação do banho"
            ),
            "plating_cost": "Custo do banho",
            "insert_date": "Data de cadastro",
            "updated_date": "Última atualização",
        }

        with sort_column:
            sort_column_name = st.selectbox(
                "Ordenar por",
                options=list(sort_labels.keys()),
                index=2,
                format_func=lambda value: sort_labels[value],
            )

        with direction_column:
            sort_direction = st.radio(
                "Direção",
                options=[
                    "Crescente",
                    "Decrescente",
                ],
                horizontal=True,
            )

    invalid_cost_range = minimum_cost > maximum_cost

    invalid_classification_range = (
        minimum_classification
        > maximum_classification
    )

    if invalid_cost_range:
        st.warning(
            "O custo mínimo não pode ser maior que o custo máximo.",
            icon="⚠️",
        )

    if invalid_classification_range:
        st.warning(
            "A classificação mínima não pode ser maior que "
            "a classificação máxima.",
            icon="⚠️",
        )

    if invalid_cost_range or invalid_classification_range:
        return filtered.iloc[0:0]

    if search_term.strip():
        normalized_search = search_term.strip().casefold()

        search_mask = (
            filtered["id_supplier"]
            .astype(str)
            .str.casefold()
            .str.contains(
                normalized_search,
                regex=False,
                na=False,
            )
            |
            filtered["supplier_name"]
            .astype(str)
            .str.casefold()
            .str.contains(
                normalized_search,
                regex=False,
                na=False,
            )
        )

        filtered = filtered[search_mask]

    if metal_filter.strip():
        normalized_metal = metal_filter.strip().casefold()

        filtered = filtered[
            filtered["plating_metal"]
            .astype(str)
            .str.casefold()
            .str.contains(
                normalized_metal,
                regex=False,
                na=False,
            )
        ]

    if contact_filter.strip():
        normalized_contact = contact_filter.strip().casefold()

        filtered = filtered[
            filtered["supplier_contact"]
            .astype(str)
            .str.casefold()
            .str.contains(
                normalized_contact,
                regex=False,
                na=False,
            )
        ]

    filtered = filtered[
        filtered["plating_cost"].between(
            float(minimum_cost),
            float(maximum_cost),
        )
        &
        filtered["plating_classification"].between(
            int(minimum_classification),
            int(maximum_classification),
        )
    ]

    if (
        isinstance(selected_dates, (tuple, list))
        and len(selected_dates) == 2
    ):
        start_date, end_date = selected_dates

        filtered = filtered[
            filtered["insert_date"]
            .dt.date
            .between(
                start_date,
                end_date,
            )
        ]

    filtered = filtered.sort_values(
        by=sort_column_name,
        ascending=sort_direction == "Crescente",
        na_position="last",
    )

    return filtered


def dataframe_for_export(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    export_dataframe = dataframe.copy()

    for column in DATE_COLUMNS:
        export_dataframe[column] = (
            export_dataframe[column]
            .dt.strftime("%d/%m/%Y %H:%M:%S")
        )

    return export_dataframe


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

success_message = st.session_state.pop(
    "plating_suppliers_message",
    None,
)

if success_message:
    st.success(
        success_message,
        icon="✅",
    )

try:
    with st.spinner("Carregando fornecedores..."):
        suppliers = load_plating_suppliers()

except Exception as error:
    st.error(
        "Não foi possível carregar os fornecedores do Supabase. "
        "Verifique a conexão e tente novamente."
    )

    with st.expander("Detalhes técnicos"):
        st.exception(error)

    st.stop()


# ============================================================
# Estado sem fornecedores
# ============================================================

if not suppliers:
    create_column, refresh_column, empty_column = (
        st.columns([0.22, 0.18, 0.60])
    )

    with create_column:
        create_clicked = st.button(
            "Novo fornecedor",
            icon=":material/add_business:",
            type="primary",
            width="stretch",
        )

    with refresh_column:
        refresh_clicked = st.button(
            "Atualizar dados",
            icon=":material/refresh:",
            width="stretch",
        )

    if refresh_clicked:
        st.cache_data.clear()
        st.rerun()

    if create_clicked:
        supplier_form_dialog(mode="create")

    st.info(
        "Nenhum fornecedor de banho foi cadastrado ainda.",
        icon="ℹ️",
    )

    st.stop()


# ============================================================
# Filtros e tabela
# ============================================================

suppliers_dataframe = prepare_suppliers_dataframe(
    suppliers
)

filtered_dataframe = apply_supplier_filters(
    suppliers_dataframe
)

st.markdown(
    (
        '<div class="filter-result">'
        f"Exibindo <strong>{len(filtered_dataframe)}</strong> "
        f"de <strong>{len(suppliers_dataframe)}</strong> "
        "fornecedores cadastrados."
        "</div>"
    ),
    unsafe_allow_html=True,
)

if filtered_dataframe.empty:
    create_column, refresh_column, empty_column = (
        st.columns([0.22, 0.18, 0.60])
    )

    with create_column:
        create_clicked = st.button(
            "Novo fornecedor",
            icon=":material/add_business:",
            type="primary",
            width="stretch",
            key="create_supplier_empty_result",
        )

    with refresh_column:
        refresh_clicked = st.button(
            "Atualizar dados",
            icon=":material/refresh:",
            width="stretch",
            key="refresh_supplier_empty_result",
        )

    if refresh_clicked:
        st.cache_data.clear()
        st.rerun()

    if create_clicked:
        supplier_form_dialog(mode="create")

    st.warning(
        "Nenhum fornecedor corresponde aos filtros selecionados.",
        icon="⚠️",
    )

    st.stop()


display_dataframe = filtered_dataframe.copy()

for column in DATE_COLUMNS:
    display_dataframe[column] = (
        display_dataframe[column]
        .dt.tz_localize(None)
    )


column_order = [
    "id_supplier",
    "supplier_name",
    "plating_metal",
    "plating_classification",
    "plating_cost",
    "supplier_contact",
    "updated_date",
    "insert_date",
    "supplier_number",
]


# O placeholder será exibido antes da tabela,
# embora seja preenchido depois da seleção.
action_placeholder = st.empty()

st.caption(
    "Selecione uma linha para editar o fornecedor."
)

supplier_ids = "|".join(
    filtered_dataframe["id_supplier"].astype(str)
)

table_signature = hashlib.md5(
    supplier_ids.encode("utf-8")
).hexdigest()[:10]

table_key = (
    "plating_suppliers_table_"
    f"{st.session_state['plating_suppliers_table_version']}_"
    f"{table_signature}"
)

table_event = st.dataframe(
    display_dataframe,
    key=table_key,
    width="stretch",
    height=500,
    hide_index=True,
    placeholder="—",
    column_order=column_order,
    on_select="rerun",
    selection_mode="single-row",
    column_config={
        "supplier_number": st.column_config.NumberColumn(
            "Número",
            help="Número sequencial interno.",
            format="%d",
            width="small",
        ),
        "id_supplier": st.column_config.TextColumn(
            "Código",
            help="Identificador do fornecedor.",
            width="medium",
        ),
        "supplier_name": st.column_config.TextColumn(
            "Fornecedor",
            width="large",
        ),
        "plating_metal": st.column_config.TextColumn(
            "Metal do banho",
            width="medium",
        ),
        "plating_classification": (
            st.column_config.ProgressColumn(
                "Classificação",
                help="Classificação de qualidade entre 1 e 20.",
                min_value=1,
                max_value=20,
                format="%d",
                width="medium",
            )
        ),
        "plating_cost": st.column_config.NumberColumn(
            "Custo do banho",
            format="R$ %.2f",
            width="small",
        ),
        "supplier_contact": st.column_config.TextColumn(
            "Contato",
            width="medium",
        ),
        "insert_date": st.column_config.DatetimeColumn(
            "Data de cadastro",
            format="DD/MM/YYYY HH:mm",
            width="medium",
        ),
        "updated_date": st.column_config.DatetimeColumn(
            "Última atualização",
            format="DD/MM/YYYY HH:mm",
            width="medium",
        ),
    },
)


# ============================================================
# Recuperação da linha selecionada
# ============================================================

selected_rows = table_event.selection.rows
selected_supplier: dict | None = None

if selected_rows:
    selected_position = selected_rows[0]

    if selected_position < len(filtered_dataframe):
        selected_supplier = (
            filtered_dataframe
            .iloc[selected_position]
            .to_dict()
        )


# ============================================================
# Barra de ações
# ============================================================

with action_placeholder.container():
    (
        create_column,
        edit_column,
        refresh_column,
        selected_column,
    ) = st.columns([0.20, 0.20, 0.18, 0.42])

    with create_column:
        create_clicked = st.button(
            "Novo fornecedor",
            icon=":material/add_business:",
            type="primary",
            width="stretch",
        )

    with edit_column:
        edit_clicked = st.button(
            "Editar fornecedor",
            icon=":material/edit:",
            width="stretch",
            disabled=selected_supplier is None,
        )

    with refresh_column:
        refresh_clicked = st.button(
            "Atualizar dados",
            icon=":material/refresh:",
            width="stretch",
        )

    with selected_column:
        if selected_supplier:
            selected_name = str(
                selected_supplier.get(
                    "supplier_name",
                    "",
                )
            )

            selected_id = str(
                selected_supplier.get(
                    "id_supplier",
                    "",
                )
            )

            st.markdown(
                (
                    f"**Selecionado:** {selected_name}  \n"
                    f"Código: `{selected_id}`"
                )
            )

        else:
            st.caption(
                "Selecione uma linha para habilitar a edição."
            )


if refresh_clicked:
    st.cache_data.clear()

    st.session_state[
        "plating_suppliers_table_version"
    ] += 1

    st.rerun()

if create_clicked:
    supplier_form_dialog(
        mode="create",
    )

elif edit_clicked and selected_supplier:
    supplier_form_dialog(
        mode="edit",
        supplier=selected_supplier,
    )


# ============================================================
# Exportação
# ============================================================

csv_data = dataframe_for_export(
    filtered_dataframe
).to_csv(
    index=False,
    sep=";",
    decimal=",",
).encode("utf-8-sig")

download_column, empty_column = st.columns(
    [0.25, 0.75]
)

with download_column:
    st.download_button(
        "Baixar fornecedores em CSV",
        data=csv_data,
        file_name="fornecedores_banho_wisecontrol.csv",
        mime="text/csv",
        icon=":material/download:",
        width="stretch",
    )

st.markdown(
    """
    <div class="footer-text">
        WiseControl · Gestão inteligente de fornecedores
    </div>
    """,
    unsafe_allow_html=True,
)