"""Behavior of the Enhance page helpers."""

import io

import numpy as np
import pytest
from imageio.v3 import imread, imwrite
from numpy.testing import assert_array_equal
from PIL import Image, ImageOps

from webapp.enhance_ui import decode_uploaded, preview_png_bytes, run_preview


def _rgba_with_clear_background():
    """Mostly transparent PNG-like image. A small opaque block sits in the middle."""
    image = np.zeros((20, 30, 4), dtype=np.uint8)
    image[..., 0] = 20
    image[..., 1] = 40
    image[..., 2] = 60
    image[..., 3] = 0
    image[5:15, 5:20] = (200, 180, 160, 255)
    return image


def test_equalize_does_not_make_transparent_pixels_opaque():
    """Histogram equalization is on by default and must not rewrite alpha.

    A clear pixel has to stay clear in the cleaned PNG. Equalizing alpha
    maps the transparent background onto a high opacity.
    """
    image = _rgba_with_clear_background()
    out = run_preview(
        image,
        equalize=True,
        denoise=False,
        sigma_color=0.05,
        sigma_spatial=1,
    )
    saved = imread(io.BytesIO(preview_png_bytes(out)))

    assert saved.shape == image.shape
    assert_array_equal(saved[..., 3], image[..., 3])
    # Color channels are still equalized, so the opaque block is not a copy.
    assert not np.array_equal(saved[5:15, 5:20, :3], image[5:15, 5:20, :3])


def test_denoise_does_not_rewrite_alpha():
    rng = np.random.default_rng(0)
    color = rng.integers(0, 40, size=(24, 24, 3), dtype=np.uint8)
    alpha = np.zeros((24, 24), dtype=np.uint8)
    alpha[4:20, 4:20] = 255
    image = np.dstack([color, alpha])

    out = run_preview(
        image,
        equalize=False,
        denoise=True,
        sigma_color=0.2,
        sigma_spatial=1,
    )
    saved = imread(io.BytesIO(preview_png_bytes(out)))

    assert_array_equal(saved[..., 3], alpha)


def _png_bytes(image, *, exif_orientation=None):
    pil = Image.fromarray(image)
    buf = io.BytesIO()
    if exif_orientation is None:
        pil.save(buf, format="PNG")
    else:
        exif = pil.getexif()
        exif[274] = exif_orientation
        pil.save(buf, format="PNG", exif=exif.tobytes())
    return buf.getvalue()


def test_decode_uploaded_applies_exif_orientation():
    """Portrait phone photos store a landscape buffer plus an orientation tag."""
    stored = np.zeros((40, 80), dtype=np.uint8)
    stored[5:25, 5:25] = 255
    data = _png_bytes(stored, exif_orientation=6)

    decoded = decode_uploaded(data)
    expected = np.asarray(ImageOps.exif_transpose(Image.open(io.BytesIO(data))))

    assert decoded.shape == (80, 40)
    assert_array_equal(decoded, expected)


def test_decode_uploaded_converts_cmyk_jpeg_to_rgb():
    """A 4-channel JPEG is CMYK ink, not RGBA. Keeping K as alpha hides the scan."""
    cmyk = np.zeros((30, 40, 4), dtype=np.uint8)
    cmyk[..., 0] = np.linspace(0, 200, 40, dtype=np.uint8)
    cmyk[..., 1] = 30
    cmyk[..., 2] = 80
    cmyk[..., 3] = 0
    buf = io.BytesIO()
    Image.fromarray(cmyk, mode="CMYK").save(buf, format="JPEG", quality=90)

    decoded = decode_uploaded(buf.getvalue())
    expected = np.asarray(Image.open(io.BytesIO(buf.getvalue())).convert("RGB"))

    assert decoded.shape == expected.shape
    assert decoded.shape[-1] == 3
    assert_array_equal(decoded, expected)


def test_decode_uploaded_keeps_16bit_tiff_values():
    scan = (np.arange(12, dtype=np.uint16).reshape(3, 4) * 1000)
    buf = io.BytesIO()
    imwrite(buf, scan, extension=".tif")

    decoded = decode_uploaded(buf.getvalue())

    assert decoded.dtype == np.uint16
    assert_array_equal(decoded, scan)


def test_decode_uploaded_keeps_rgba_png_alpha():
    image = _rgba_with_clear_background()
    decoded = decode_uploaded(_png_bytes(image))

    assert decoded.shape == image.shape
    assert_array_equal(decoded, image)


def test_decode_uploaded_expands_grayscale_with_alpha():
    gray = np.full((8, 8), 100, dtype=np.uint8)
    alpha = np.zeros((8, 8), dtype=np.uint8)
    alpha[2:6, 2:6] = 255
    image = Image.fromarray(gray, mode="L")
    image.putalpha(Image.fromarray(alpha, mode="L"))
    buf = io.BytesIO()
    image.save(buf, format="PNG")

    decoded = decode_uploaded(buf.getvalue())

    assert decoded.shape == (8, 8, 4)
    assert_array_equal(decoded[..., 0], gray)
    assert_array_equal(decoded[..., 3], alpha)


def test_decode_uploaded_rejects_bytes_that_are_not_a_photo():
    with pytest.raises(ValueError, match="could not be read"):
        decode_uploaded(b"this is not a photo")


def test_preview_without_cleanup_keeps_alpha_values():
    image = _rgba_with_clear_background()
    out = run_preview(
        image,
        equalize=False,
        denoise=False,
        sigma_color=0.05,
        sigma_spatial=1,
    )

    assert out.dtype == np.uint8
    assert_array_equal(out, image)
