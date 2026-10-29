"""Tests for the image-analysis function used by the upload page."""

from io import BytesIO

import numpy as np
import pytest
from PIL import Image
from PIL.ExifTags import Base

from webapp import analysis
from webapp.analysis import ImageAnalysisError, analyze_image


def _encode(array, fmt='PNG'):
    buffer = BytesIO()
    Image.fromarray(array).save(buffer, format=fmt)
    return buffer.getvalue()


# Inverse of the rotation a viewer applies for each EXIF orientation.
# Phone cameras store the sensor raster and set this tag; orientation 6
# (rotate 90° clockwise for display) is the usual portrait JPEG.
_STORED_TRANSPOSE = {
    3: Image.Transpose.ROTATE_180,
    6: Image.Transpose.ROTATE_90,
    8: Image.Transpose.ROTATE_270,
}


def _jpeg_with_exif_orientation(upright, orientation):
    image = Image.fromarray(upright)
    inverse = _STORED_TRANSPOSE.get(orientation)
    if inverse is not None:
        image = image.transpose(inverse)
    exif = image.getexif()
    exif[Base.Orientation] = orientation
    buffer = BytesIO()
    image.save(buffer, format='JPEG', exif=exif, quality=95)
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


@pytest.mark.parametrize('orientation', [1, 3, 6, 8])
def test_jpeg_exif_orientation_is_measured_upright(orientation):
    """Centroids and the overlay follow the upright view browsers show."""
    upright = np.zeros((120, 50), dtype=np.uint8)
    upright[8:28, 6:26] = 255
    expected = analyze_image(_encode(upright))

    result = analyze_image(_jpeg_with_exif_orientation(upright, orientation))

    assert result['width'] == expected['width'] == 50
    assert result['height'] == expected['height'] == 120
    assert result['summary']['count'] == 1
    got = result['objects'][0]
    exp = expected['objects'][0]
    assert got['centroid_row'] == pytest.approx(exp['centroid_row'], abs=1.5)
    assert got['centroid_col'] == pytest.approx(exp['centroid_col'], abs=1.5)
    overlay = Image.open(BytesIO(result['overlay_png']))
    assert overlay.size == (expected['width'], expected['height'])
    # The blob interior stays in the upright top-left, not the raw corner.
    assert np.asarray(overlay.convert('RGB'))[17, 15].mean() > 200


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
