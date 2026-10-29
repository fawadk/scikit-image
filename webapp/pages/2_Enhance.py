"""Enhance a dark or noisy photo and compare it with the original."""

import sys
from pathlib import Path

import numpy as np
import streamlit as st

from skimage import data

# `streamlit run` puts this file's folder on the path, not the repo root.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from webapp.enhance_ui import (  # noqa: E402
    channel_axis_for,
    decode_uploaded,
    display_image,
    intensity_counts,
    preview_png_bytes,
    run_preview,
)

SAMPLE_NAME = "camera (sample)"


def load_sample():
    st.session_state.workspace_image = data.camera()
    st.session_state.workspace_name = SAMPLE_NAME
    st.session_state.workspace_upload_id = None


def load_upload(uploaded):
    st.session_state.workspace_image = decode_uploaded(uploaded.getvalue())
    st.session_state.workspace_name = uploaded.name
    st.session_state.workspace_upload_id = uploaded.file_id


@st.cache_data(show_spinner=False)
def _cached_preview(
    blob,
    shape,
    dtype_name,
    equalize,
    denoise,
    sigma_color,
    sigma_spatial,
):
    image = np.frombuffer(blob, dtype=np.dtype(dtype_name)).reshape(shape).copy()
    return run_preview(
        image,
        equalize=equalize,
        denoise=denoise,
        sigma_color=sigma_color,
        sigma_spatial=sigma_spatial,
    )


def main():
    st.set_page_config(page_title="Enhance", layout="wide")
    st.title("Enhance a dark or noisy photo")
    st.write(
        "Compare the original with a cleaned copy. "
        "Turn on histogram equalization, bilateral denoise, or both, "
        "then download the cleaned PNG. No Python required."
    )

    if "workspace_image" not in st.session_state:
        load_sample()

    with st.sidebar:
        st.header("Cleanup")
        equalize = st.checkbox(
            "Histogram equalization", value=True, key="equalize"
        )
        denoise = st.checkbox("Bilateral denoise", value=False, key="denoise")
        sigma_color = st.slider(
            "sigma_color",
            min_value=0.01,
            max_value=1.0,
            value=0.05,
            step=0.01,
            key="sigma_color",
            help="How different a nearby color can be and still be smoothed.",
        )
        sigma_spatial = st.slider(
            "sigma_spatial",
            min_value=1,
            max_value=10,
            value=1,
            step=1,
            key="sigma_spatial",
            help="How far smoothing looks around each pixel.",
        )
        show_hist = st.checkbox(
            "Show intensity histograms", value=False, key="show_hist"
        )
        st.header("Photo")
        uploaded = st.file_uploader(
            "Open a photo",
            type=["png", "jpg", "jpeg", "tif", "tiff"],
            help="Leave this empty to keep the sample camera photo.",
        )
        use_sample = st.button("Use sample camera photo", key="use_sample")

    if use_sample:
        load_sample()
        if uploaded is not None:
            # Ignore the file already sitting in the uploader until it changes.
            st.session_state.workspace_upload_id = uploaded.file_id
    elif uploaded is not None and uploaded.file_id != st.session_state.get(
        "workspace_upload_id"
    ):
        try:
            load_upload(uploaded)
        except ValueError as exc:
            st.error(str(exc))
            st.stop()

    # Caption is after the upload/sample update so it matches the photo shown.
    st.sidebar.caption(f"Current photo: {st.session_state.workspace_name}")

    image = np.ascontiguousarray(st.session_state.workspace_image)
    try:
        channel_axis_for(image)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    with st.spinner("Cleaning the photo…"):
        preview = _cached_preview(
            image.tobytes(),
            image.shape,
            image.dtype.str,
            bool(equalize),
            bool(denoise),
            float(sigma_color),
            float(sigma_spatial),
        )

    original_col, cleaned_col = st.columns(2)
    with original_col:
        st.subheader("Original")
        st.image(display_image(image), width="stretch")
    with cleaned_col:
        st.subheader("Cleaned")
        st.image(display_image(preview), width="stretch")

    if show_hist:
        hist_left, hist_right = st.columns(2)
        with hist_left:
            st.caption("Original intensity histogram")
            st.bar_chart(intensity_counts(image), height=160)
        with hist_right:
            st.caption("Cleaned intensity histogram")
            st.bar_chart(intensity_counts(preview), height=160)

    st.download_button(
        "Download cleaned PNG",
        data=preview_png_bytes(preview),
        file_name="cleaned.png",
        mime="image/png",
        key="download_cleaned",
    )


main()
