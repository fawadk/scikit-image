"""Tests for the image-analysis function used by the upload page."""

from io import BytesIO

import numpy as np
import pytest
from PIL import Image

from webapp import analysis
from webapp.analysis import ImageAnalysisError, analyze_image


def _encode(array, fmt='PNG'):
    buffer = BytesIO()
    Image.fromarray(array).save(buffer, format=fmt)
    return buffer.getvalue()


def _two_blobs(channels=None):
    image = np.zeros((80, 80), dtype=np.uint8)
    image[10:30, 10:30] = 255
    image[50:70, 45:70] = 255
    if channels:
        image = np.stack([image] * channels, axis=-1)
    return image


def test_two_bright_blobs_are_counted():
    result = analyze_image(_encode(_two_blobs()))

    assert result['summary']['count'] == 2
    assert len(result['objects']) == 2
    ids = [row['id'] for row in result['objects']]
    assert ids == [1, 2]
    areas = sorted(row['area'] for row in result['objects'])
    assert areas[0] > 300
    assert areas[1] > 400
    first = result['objects'][0]
    assert abs(first['centroid_row'] - 19.5) < 3
    assert abs(first['centroid_col'] - 19.5) < 3
    assert result['summary']['mean_area'] == pytest.approx(
        sum(row['area'] for row in result['objects']) / 2
    )
    assert result['summary']['max_area'] == max(row['area'] for row in result['objects'])
    assert result['summary']['min_area'] == min(row['area'] for row in result['objects'])
    assert result['width'] == 80
    assert result['height'] == 80
    assert result['overlay_png'].startswith(b'\x89PNG')


def test_dark_blobs_on_a_light_background_are_counted():
    image = np.full((80, 80), 255, dtype=np.uint8)
    image[10:30, 10:30] = 0
    image[50:70, 45:70] = 0

    result = analyze_image(_encode(image))

    assert result['summary']['count'] == 2
    assert len(result['objects']) == 2


def test_rgb_input_does_not_crash_and_counts_blobs():
    result = analyze_image(_encode(_two_blobs(channels=3)))

    assert result['summary']['count'] == 2
    overlay = Image.open(BytesIO(result['overlay_png']))
    assert overlay.size == (80, 80)
    assert overlay.mode == 'RGB'


def test_jpeg_upload_is_accepted():
    result = analyze_image(_encode(_two_blobs(), fmt='JPEG'))

    assert result['summary']['count'] == 2


def test_speckle_below_min_size_is_dropped():
    image = _two_blobs()
    image[0:2, 0:2] = 255

    result = analyze_image(_encode(image), min_size=32)

    assert result['summary']['count'] == 2


def test_uniform_image_finds_no_objects():
    result = analyze_image(_encode(np.zeros((40, 40), dtype=np.uint8)))

    assert result['summary']['count'] == 0
    assert result['objects'] == []
    assert result['summary']['mean_area'] is None
    assert result['summary']['max_area'] is None
    assert result['summary']['min_area'] is None
    assert result['overlay_png'].startswith(b'\x89PNG')


def test_invalid_bytes_raise_a_clear_error():
    with pytest.raises(ImageAnalysisError, match='PNG or JPEG'):
        analyze_image(b'this is not an image')


def test_empty_bytes_raise_a_clear_error():
    with pytest.raises(ImageAnalysisError, match='PNG or JPEG'):
        analyze_image(b'')


def test_image_over_the_pixel_cap_is_rejected(monkeypatch):
    monkeypatch.setattr(analysis, '_MAX_PIXELS', 100)
    image = np.zeros((20, 20), dtype=np.uint8)

    with pytest.raises(ImageAnalysisError, match='too large'):
        analyze_image(_encode(image))


def test_shapes_defined_only_by_alpha_are_counted():
    """A flat RGB color with an alpha mask is what the preview shows."""
    rgba = np.full((80, 80, 4), 255, dtype=np.uint8)
    rgba[..., 3] = 0
    rgba[10:30, 10:30, 3] = 255
    rgba[50:70, 45:70, 3] = 255

    result = analyze_image(_encode(rgba))

    assert result['summary']['count'] == 2
    overlay = np.asarray(Image.open(BytesIO(result['overlay_png'])))
    # Transparent corners are painted over the same #111 well as the preview.
    assert overlay[0, 0].tolist() == [0x11, 0x11, 0x11]


def test_fully_transparent_pixels_are_not_objects():
    rgba = np.zeros((80, 80, 4), dtype=np.uint8)
    rgba[10:30, 10:30, :3] = 255
    rgba[50:70, 45:70, :3] = 255

    result = analyze_image(_encode(rgba))

    assert result['summary']['count'] == 0


def test_a_transparent_pixel_does_not_hide_color_objects():
    rgb = _two_blobs(channels=3)
    rgba = np.dstack([rgb, np.full(rgb.shape[:2], 255, dtype=np.uint8)])
    rgba[0, 0, 3] = 0

    result = analyze_image(_encode(rgba))

    assert result['summary']['count'] == 2


def test_opaque_rgba_still_counts_color_objects():
    rgb = _two_blobs(channels=3)
    rgba = np.dstack([rgb, np.full(rgb.shape[:2], 255, dtype=np.uint8)])

    result = analyze_image(_encode(rgba))

    assert result['summary']['count'] == 2


def test_exif_orientation_is_applied_before_measuring():
    stored = np.zeros((40, 80), dtype=np.uint8)
    stored[5:25, 5:25] = 255
    image = Image.fromarray(stored)
    exif = image.getexif()
    exif[274] = 6  # displayed width/height swap relative to stored pixels
    buffer = BytesIO()
    image.save(buffer, format='PNG', exif=exif.tobytes())

    result = analyze_image(buffer.getvalue())

    assert result['summary']['count'] == 1
    assert (result['width'], result['height']) == (40, 80)


def test_multi_picture_jpeg_is_measured():
    first = Image.fromarray(_two_blobs())
    second = Image.fromarray(np.zeros((80, 80), dtype=np.uint8))
    buffer = BytesIO()
    first.save(buffer, format='MPO', save_all=True, append_images=[second])

    result = analyze_image(buffer.getvalue())

    assert result['summary']['count'] == 2
