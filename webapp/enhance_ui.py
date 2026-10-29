"""Pure helpers for the Enhance page. No Streamlit imports."""

import io

import numpy as np
from imageio.v3 import imopen, imwrite

from skimage.exposure import enhance_preview, histogram
from skimage.util import img_as_ubyte


def prepare_uploaded(array):
    """Drop a trailing singleton channel so grayscale uploads stay 2D."""
    image = np.asarray(array)
    if image.ndim == 3 and image.shape[-1] == 1:
        image = np.squeeze(image, axis=-1)
    return image


def decode_uploaded(data):
    """Load photo bytes the way the picture should be shown.

    EXIF orientation is applied, and the sample values are left intact.
    A CMYK JPEG is converted to RGB so the black plate is not kept as
    alpha. Grayscale-with-alpha is expanded to RGBA.

    Raises
    ------
    ValueError
        If the bytes are not a readable photo.
    """
    buffer = io.BytesIO(data)
    try:
        with imopen(buffer, "r", plugin="pillow") as src:
            mode = src.metadata().get("mode")
            read_mode = None
            if mode == "CMYK":
                read_mode = "RGB"
            elif mode in {"LA", "PA"}:
                read_mode = "RGBA"
            image = src.read(rotate=True, mode=read_mode)
    except Exception as exc:
        raise ValueError(
            "That file could not be read. Use a PNG, JPEG, or TIFF photo."
        ) from exc
    return prepare_uploaded(image)


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


def _split_alpha(image):
    """Separate a trailing alpha channel from color.

    Histogram equalization and bilateral denoising are defined on color.
    Applying either one to alpha remaps transparency. A fully clear pixel
    in a mostly transparent image becomes opaque.
    """
    image = np.asarray(image)
    if image.ndim == 3 and image.shape[-1] == 4:
        return image[..., :3], image[..., 3]
    return image, None


def _restore_alpha(preview, alpha):
    """Append ``alpha`` using the same scale as ``preview``."""
    if alpha is None:
        return preview
    if np.issubdtype(preview.dtype, np.floating):
        if np.issubdtype(alpha.dtype, np.integer):
            alpha_out = alpha.astype(preview.dtype) / np.iinfo(alpha.dtype).max
        elif np.issubdtype(alpha.dtype, np.floating):
            alpha_out = np.clip(alpha, 0.0, 1.0).astype(preview.dtype, copy=False)
        else:
            alpha_out = alpha.astype(preview.dtype)
    else:
        alpha_out = alpha.astype(preview.dtype, copy=False)
    return np.concatenate([preview, alpha_out[..., None]], axis=-1)


def run_preview(image, *, equalize, denoise, sigma_color, sigma_spatial):
    """Call ``enhance_preview`` with the channel axis chosen for this photo.

    An RGBA photo is cleaned on the color channels only. Alpha is copied
    through unchanged so a transparent background stays transparent.
    """
    color, alpha = _split_alpha(image)
    channel_axis = channel_axis_for(color)
    preview = enhance_preview(
        color,
        equalize=equalize,
        denoise=denoise,
        sigma_color=sigma_color,
        sigma_spatial=sigma_spatial,
        channel_axis=channel_axis,
    )
    return _restore_alpha(preview, alpha)
