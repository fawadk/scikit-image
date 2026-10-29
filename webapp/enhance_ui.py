"""Pure helpers for the Enhance page. No Streamlit imports."""

import io

import numpy as np
from imageio.v3 import imwrite

from skimage.exposure import enhance_preview, histogram
from skimage.util import img_as_ubyte


def prepare_uploaded(array):
    """Drop a trailing singleton channel so grayscale uploads stay 2D."""
    image = np.asarray(array)
    if image.ndim == 3 and image.shape[-1] == 1:
        image = np.squeeze(image, axis=-1)
    return image


def channel_axis_for(image):
    """Return the channel axis for a grayscale or RGB/RGBA photo.

    Parameters
    ----------
    image : ndarray
        Photo array.

    Returns
    -------
    channel_axis : int or None
        ``None`` for grayscale, ``-1`` when the last axis is color.

    Raises
    ------
    ValueError
        If ``image`` is not a 2D grayscale or 3D color photo.
    """
    image = np.asarray(image)
    if image.ndim == 2:
        return None
    if image.ndim == 3 and image.shape[-1] in (3, 4):
        return -1
    raise ValueError(
        "Use a grayscale or RGB photo. " f"This image has shape {image.shape}."
    )


def intensity_counts(image):
    """Return histogram counts for a simple bar chart."""
    gray = np.asarray(image)
    if gray.ndim == 3:
        gray = gray.mean(axis=-1)
    if np.issubdtype(gray.dtype, np.floating):
        gray = np.clip(gray, 0.0, 1.0)
    counts, _centers = histogram(gray, nbins=64)
    return np.asarray(counts)


def display_image(image):
    """Clip floating images to the range Streamlit can show."""
    image = np.asarray(image)
    if np.issubdtype(image.dtype, np.floating):
        return np.clip(image, 0.0, 1.0)
    return image


def preview_png_bytes(image):
    """Encode a preview image as PNG bytes.

    Floating images are clipped to ``[0, 1]`` and stored as 8-bit PNG.
    """
    image = np.asarray(image)
    if image.dtype != np.uint8:
        if np.issubdtype(image.dtype, np.floating):
            image = np.clip(image, 0.0, 1.0)
        image = img_as_ubyte(image)
    buffer = io.BytesIO()
    imwrite(buffer, np.ascontiguousarray(image), extension=".png")
    return buffer.getvalue()


def run_preview(image, *, equalize, denoise, sigma_color, sigma_spatial):
    """Call ``enhance_preview`` with the channel axis chosen for this photo."""
    image = np.asarray(image)
    channel_axis = channel_axis_for(image)
    return enhance_preview(
        image,
        equalize=equalize,
        denoise=denoise,
        sigma_color=sigma_color,
        sigma_spatial=sigma_spatial,
        channel_axis=channel_axis,
    )
