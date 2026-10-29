"""Measure objects in an uploaded image.

The upload page calls this module. It does not import the web framework,
so the measurements can be tested on their own.
"""

from io import BytesIO

import numpy as np
from PIL import Image, ImageDraw, UnidentifiedImageError
from PIL.Image import DecompressionBombError

import skimage as ski


class ImageAnalysisError(ValueError):
    """The upload cannot be measured. The message is safe to show to a user."""


_ALLOWED_FORMATS = {'PNG', 'JPEG'}
_MAX_PIXELS = 8_000_000
_OUTLINE = (31, 79, 216)


def analyze_image(data: bytes, *, min_size: int = 64) -> dict:
    """Count objects and draw a numbered outline.

    Bright objects on a dark background, and dark objects on a light
    background, are both treated as foreground. Blobs of ``min_size``
    pixels or fewer are dropped.

    Parameters
    ----------
    data : bytes
        PNG or JPEG file contents.
    min_size : int, optional
        Drop connected components this size or smaller.

    Returns
    -------
    result : dict
        ``summary`` (count and area stats), ``objects`` (one row per
        object), ``overlay_png`` (numbered outline), and ``width`` /
        ``height``.

    Raises
    ------
    ImageAnalysisError
        If ``data`` is not a PNG or JPEG, or the image has no pixels.
    """
    rgb, gray = _load_rgb_and_gray(data)
    height, width = gray.shape

    smooth = ski.filters.gaussian(gray, sigma=1, preserve_range=True)
    threshold = float(ski.filters.threshold_otsu(smooth))
    foreground = smooth > threshold
    # The larger class is the background, whether the objects are bright
    # or dark.
    if foreground.size and float(foreground.mean()) > 0.5:
        foreground = ~foreground

    cleaned = ski.morphology.remove_small_objects(
        foreground, max_size=int(min_size)
    )
    labels = ski.measure.label(cleaned)
    properties = ski.measure.regionprops(labels)

    objects = []
    for prop in properties:
        row, col = prop.centroid
        objects.append(
            {
                'id': int(prop.label),
                'area': int(prop.area),
                'centroid_row': round(float(row), 1),
                'centroid_col': round(float(col), 1),
                'perimeter': round(float(prop.perimeter), 1),
            }
        )

    overlay = _draw_overlay(rgb, labels, objects)
    return {
        'summary': _summary(objects),
        'objects': objects,
        'overlay_png': _png_bytes(overlay),
        'width': int(width),
        'height': int(height),
    }


def _summary(objects):
    if not objects:
        return {
            'count': 0,
            'mean_area': None,
            'max_area': None,
            'min_area': None,
        }
    areas = [row['area'] for row in objects]
    return {
        'count': len(objects),
        'mean_area': float(sum(areas) / len(areas)),
        'max_area': max(areas),
        'min_area': min(areas),
    }


def _load_rgb_and_gray(data: bytes):
    if not data:
        raise ImageAnalysisError('Upload a PNG or JPEG image.')
    previous_limit = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = _MAX_PIXELS
    try:
        with Image.open(BytesIO(data)) as image:
            image.load()
            if image.format not in _ALLOWED_FORMATS:
                raise ImageAnalysisError('Upload a PNG or JPEG image.')
            rgb = np.asarray(image.convert('RGB'))
    except ImageAnalysisError:
        raise
    except DecompressionBombError as exc:
        raise ImageAnalysisError('That image is too large to analyze.') from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ImageAnalysisError('Upload a PNG or JPEG image.') from exc
    finally:
        Image.MAX_IMAGE_PIXELS = previous_limit

    if rgb.shape[0] == 0 or rgb.shape[1] == 0:
        raise ImageAnalysisError('That image is empty.')
    if rgb.shape[0] * rgb.shape[1] > _MAX_PIXELS:
        raise ImageAnalysisError('That image is too large to analyze.')

    # rgb2gray returns values in [0, 1]. Scale to the 8-bit range so the
    # threshold matches the intensities stored in the file.
    gray = np.asarray(ski.color.rgb2gray(rgb), dtype=np.float64) * 255.0
    return rgb, gray


def _draw_overlay(rgb, labels, objects):
    overlay = np.array(rgb, copy=True)
    boundaries = ski.segmentation.find_boundaries(labels, mode='outer')
    overlay[boundaries] = _OUTLINE

    canvas = Image.fromarray(overlay, mode='RGB')
    draw = ImageDraw.Draw(canvas)
    for obj in objects:
        x = float(obj['centroid_col'])
        y = float(obj['centroid_row'])
        text = str(obj['id'])
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            draw.text((x + dx, y + dy), text, fill=(11, 31, 58))
        draw.text((x, y), text, fill=(255, 255, 255))
    return np.asarray(canvas)


def _png_bytes(array):
    buffer = BytesIO()
    Image.fromarray(array, mode='RGB').save(buffer, format='PNG')
    return buffer.getvalue()
