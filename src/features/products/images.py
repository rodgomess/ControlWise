from __future__ import annotations

from io import BytesIO
import hashlib
import time

import pandas as pd
import streamlit as st
from PIL import Image, ImageOps, UnidentifiedImageError
from streamlit_cropper import st_cropper

from src.shared.data_access import get_supabase_client, load_product_image_urls
from src.shared.formatters import text_value

MAIN_IMAGE_SIZE = (800, 800)
THUMBNAIL_SIZE = (200, 200)
MINIMUM_CROP_SIZE = 500
IMAGE_UPLOAD_TYPES = ["jpg", "jpeg", "png", "webp"]
IMAGE_CONTENT_TYPE = "image/webp"

supabase = get_supabase_client()

def renew_product_image_cache() -> None:
    st.session_state["product_image_cache_token"] = (
        time.time_ns()
    )


def image_to_webp_bytes(
    image: Image.Image,
    quality: int = 85,
) -> bytes:
    buffer = BytesIO()

    image.save(
        buffer,
        format="WEBP",
        quality=quality,
        method=6,
    )

    return buffer.getvalue()


def create_product_image_versions(
    cropped_image: Image.Image,
) -> tuple[bytes, bytes]:
    """
    Cria a imagem principal e a miniatura em WebP.
    """
    normalized_image = cropped_image

    if normalized_image.mode != "RGB":
        normalized_image = normalized_image.convert("RGB")

    main_image = normalized_image.resize(
        MAIN_IMAGE_SIZE,
        Image.Resampling.LANCZOS,
    )

    thumbnail_image = main_image.resize(
        THUMBNAIL_SIZE,
        Image.Resampling.LANCZOS,
    )

    return (
        image_to_webp_bytes(main_image, quality=85),
        image_to_webp_bytes(thumbnail_image, quality=80),
    )


def upload_product_image_versions(
    product_id: str,
    main_image_bytes: bytes,
    thumbnail_image_bytes: bytes,
) -> None:
    """
    Envia a imagem principal e a miniatura como bytes.

    Os nomes são fixos para que uma nova imagem sobrescreva
    automaticamente a anterior.
    """

    supabase.upload_product_image(
        main_image_bytes,
        "original.webp",
        product_id,
        IMAGE_CONTENT_TYPE,
    )

    supabase.upload_product_image(
        thumbnail_image_bytes,
        "thumbnail.webp",
        product_id,
        IMAGE_CONTENT_TYPE,
    )


def extract_inserted_product_id(insert_response) -> str:
    """
    Extrai o ID retornado pelo insert do PostgREST/Supabase.

    Aceita resposta com atributo .data, lista de registros
    ou um dicionário contendo o registro criado.
    """
    if (
        hasattr(insert_response, "execute")
        and not hasattr(insert_response, "data")
    ):
        insert_response = insert_response.execute()

    data = getattr(insert_response, "data", insert_response)

    if isinstance(data, dict) and "data" in data:
        data = data["data"]

    if isinstance(data, list):
        data = data[0] if data else None

    if isinstance(data, dict):
        for field in ("id", "id_product", "product_id"):
            product_id = data.get(field)

            if product_id:
                return str(product_id)

    raise RuntimeError(
        "O cadastro foi executado, mas o Supabase não retornou "
        "o ID do produto. Faça insert_product() retornar a linha "
        "inserida para permitir o upload da foto."
    )


def product_image_state_keys(
    mode: str,
    product_id: str,
) -> dict[str, str]:
    context = product_id or "new"
    prefix = f"product_image_{mode}_{context}"

    return {
        "main": f"{prefix}_main",
        "thumbnail": f"{prefix}_thumbnail",
        "source_digest": f"{prefix}_source_digest",
        "uploader": f"{prefix}_uploader",
        "confirm_crop": f"{prefix}_confirm_crop",
        "discard_crop": f"{prefix}_discard_crop",
    }


def clear_pending_product_image(
    mode: str,
    product_id: str,
) -> None:
    keys = product_image_state_keys(mode, product_id)

    for key_name in ("main", "thumbnail", "source_digest"):
        st.session_state.pop(keys[key_name], None)


def append_image_cache_version(
    image_url: str | None,
) -> str | None:
    if not image_url:
        return None

    separator = "&" if "?" in image_url else "?"

    cache_token = st.session_state[
        "product_image_cache_token"
    ]

    return (
        f"{image_url}"
        f"{separator}image_version={cache_token}"
    )


def add_product_image_urls(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Adiciona URLs de imagem sem exigir colunas extras na tabela SQL.
    """
    enriched_dataframe = dataframe.copy()

    if enriched_dataframe.empty:
        enriched_dataframe["original_url_image"] = None
        enriched_dataframe["thumbnail_url_image"] = None
        return enriched_dataframe

    original_urls: list[str | None] = []
    thumbnail_urls: list[str | None] = []

    for product_id in enriched_dataframe["id"].astype(str):
        urls = load_product_image_urls(product_id)

        original_urls.append(
            append_image_cache_version(
                urls.get("original_url_image")
            )
        )
        thumbnail_urls.append(
            append_image_cache_version(
                urls.get("thumbnail_url_image")
            )
        )

    enriched_dataframe["original_url_image"] = original_urls
    enriched_dataframe["thumbnail_url_image"] = thumbnail_urls

    return enriched_dataframe


def render_product_image_editor(
    *,
    mode: str,
    product_id: str,
    current_original_url: str | None,
    current_thumbnail_url: str | None,
) -> tuple[bytes | None, bytes | None]:
    """
    Editor de imagem compartilhado entre criação e edição.

    O cropper fica fora do st.form para atualizar em tempo real.
    O recorte confirmado é guardado no session_state até o usuário
    salvar o produto.
    """
    current_thumbnail_url = text_value(
        current_thumbnail_url
    ).strip()

    current_original_url = text_value(
        current_original_url
    ).strip()

    current_image_url = (
        current_thumbnail_url
        or current_original_url
    )

    keys = product_image_state_keys(mode, product_id)

    st.markdown("#### Foto do produto")

    with st.container(border=True):
        if current_original_url:
            current_image_column, current_text_column = st.columns(
                [0.28, 0.72],
                vertical_alignment="center",
            )

            with current_image_column:
                st.image(
                    current_thumbnail_url or current_original_url,
                    width=150,
                )

            with current_text_column:
                st.markdown("**Foto atual**")
                st.caption(
                    "Selecione uma nova imagem abaixo para substituir "
                    "a foto atual quando salvar as alterações."
                )
        else:
            st.caption(
                "A foto é opcional. Envie uma imagem para recortar "
                "e gerar automaticamente a versão principal e a miniatura."
            )

        uploaded_file = st.file_uploader(
            "Selecionar foto do produto",
            type=IMAGE_UPLOAD_TYPES,
            max_upload_size=10,
            key=keys["uploader"],
            help=(
                "Formatos aceitos: JPG, JPEG, PNG e WebP. "
                "Tamanho máximo: 10 MB."
            ),
        )

        if uploaded_file is not None:
            uploaded_bytes = uploaded_file.getvalue()
            source_digest = hashlib.sha256(
                uploaded_bytes
            ).hexdigest()

            previous_digest = st.session_state.get(
                keys["source_digest"]
            )

            if previous_digest != source_digest:
                st.session_state[keys["source_digest"]] = (
                    source_digest
                )
                st.session_state.pop(keys["main"], None)
                st.session_state.pop(keys["thumbnail"], None)

            try:
                source_image = Image.open(
                    BytesIO(uploaded_bytes)
                )
                source_image = ImageOps.exif_transpose(
                    source_image
                )

                if source_image.mode != "RGB":
                    source_image = source_image.convert("RGB")

                st.caption(
                    "Posicione a peça dentro do quadrado. "
                    f"O recorte mínimo é de "
                    f"{MINIMUM_CROP_SIZE} × "
                    f"{MINIMUM_CROP_SIZE} pixels."
                )

                crop_column, preview_column = st.columns(
                    [1.35, 0.65]
                )

                with crop_column:
                    cropped_image = st_cropper(
                        source_image,
                        realtime_update=True,
                        aspect_ratio=(1, 1),
                        box_color="#80644F",
                    )

                with preview_column:
                    preview_image = cropped_image.copy()
                    preview_image.thumbnail(
                        (280, 280),
                        Image.Resampling.LANCZOS,
                    )

                    st.markdown("**Pré-visualização**")
                    st.image(
                        preview_image,
                        width="stretch",
                    )
                    st.caption(
                        f"Recorte: {cropped_image.width} × "
                        f"{cropped_image.height} px"
                    )

                    confirm_crop = st.button(
                        "Usar este recorte",
                        key=keys["confirm_crop"],
                        icon=":material/crop:",
                        type="primary",
                        width="stretch",
                    )

                if confirm_crop:
                    crop_width, crop_height = cropped_image.size

                    if min(crop_width, crop_height) < MINIMUM_CROP_SIZE:
                        st.warning(
                            "O recorte está muito pequeno. "
                            "Selecione uma área de pelo menos "
                            f"{MINIMUM_CROP_SIZE} × "
                            f"{MINIMUM_CROP_SIZE} pixels.",
                            icon="⚠️",
                        )
                    else:
                        (
                            main_image_bytes,
                            thumbnail_image_bytes,
                        ) = create_product_image_versions(
                            cropped_image
                        )

                        st.session_state[keys["main"]] = (
                            main_image_bytes
                        )
                        st.session_state[keys["thumbnail"]] = (
                            thumbnail_image_bytes
                        )

            except (
                UnidentifiedImageError,
                OSError,
                ValueError,
            ):
                st.error(
                    "Não foi possível abrir essa imagem. "
                    "Escolha outro arquivo JPG, PNG ou WebP."
                )

        pending_main_image = st.session_state.get(
            keys["main"]
        )
        pending_thumbnail_image = st.session_state.get(
            keys["thumbnail"]
        )

        if pending_main_image and pending_thumbnail_image:
            st.success(
                "Recorte confirmado. A foto será enviada quando "
                "o produto for salvo.",
                icon="✅",
            )

            confirmed_image_column, discard_column = st.columns(
                [0.72, 0.28],
                vertical_alignment="center",
            )

            with confirmed_image_column:
                st.image(
                    BytesIO(pending_thumbnail_image),
                    caption="Miniatura que aparecerá no catálogo",
                    width=150,
                )

            with discard_column:
                if st.button(
                    "Descartar foto",
                    key=keys["discard_crop"],
                    icon=":material/undo:",
                    width="stretch",
                ):
                    clear_pending_product_image(
                        mode,
                        product_id,
                    )
                    st.rerun()

    return (
        st.session_state.get(keys["main"]),
        st.session_state.get(keys["thumbnail"]),
    )
