"""Count bright objects in a grayscale or color image."""

import numpy as np

from ..color.colorconv import rgb2gray
from ..filters.thresholding import threshold_otsu
from ._label import label
from ._regionprops import regionprops


class ObjectCountResult:
    """Number of foreground objects and one row of measurements per object.

    Attributes
    ----------
    count : int
        Number of objects kept after ``min_size`` filtering.
    id : (N,) ndarray of int
        Connected-component label of each object. Labels start at 1 and are
        not renumbered when ``min_size`` drops an object.
    area : (N,) ndarray of int
        Area of each object in pixels, in the same order as ``id``.
    centroid : (N, 2) ndarray of float
        ``(row, column)`` centroid of each object, in the same order as ``id``.
    """

    __slots__ = ("count", "id", "area", "centroid")

    def __init__(self, count, id, area, centroid):
        self.count = count
        self.id = id
        self.area = area
        self.centroid = centroid

    def __repr__(self):
        return (
            f"ObjectCountResult(count={self.count}, id={self.id!r}, "
            f"area={self.area!r}, centroid={self.centroid!r})"
        )

    def __eq__(self, other):
        if not isinstance(other, ObjectCountResult):
            return NotImplemented
        return (
            self.count == other.count
            and np.array_equal(self.id, other.id)
            and np.array_equal(self.area, other.area)
            and np.array_equal(self.centroid, other.centroid)
        )


def _validate_min_size(min_size):
    if isinstance(min_size, bool) or not isinstance(min_size, (int, np.integer)):
        raise TypeError(
            f"min_size must be a non-negative integer, got {type(min_size).__name__}"
        )
    min_size = int(min_size)
    if min_size < 0:
        raise ValueError(f"min_size must be >= 0, got {min_size}")
    return min_size


def _as_grayscale_image(image):
    """Validate ``image`` and return a 2D real array."""
    if image is None:
        raise TypeError("image must be a real numeric array, got None")
    try:
        image = np.asarray(image)
    except (TypeError, ValueError) as exc:
        raise TypeError("image must be a real numeric array") from exc

    if image.dtype.kind not in "buif":
        raise TypeError(f"image must be a real numeric array, got dtype {image.dtype}")
    if image.size == 0:
        raise ValueError("image must not be empty")
    if image.dtype.kind == "f" and not np.isfinite(image).all():
        raise ValueError("image must contain only finite values")

    if image.ndim == 3 and image.shape[-1] in (3, 4):
        # RGBA: drop alpha. rgb2gray requires exactly three channels.
        image = rgb2gray(image[..., :3])
    elif image.ndim != 2:
        raise ValueError(
            "image must be 2D grayscale with shape (M, N) or color with "
            f"shape (M, N, 3) or (M, N, 4); got shape {image.shape}"
        )

    # threshold_otsu warns when it has to cast bool input.
    if image.dtype == bool:
        image = image.astype(np.uint8)
    return image


def object_count(image, min_size=0):
    """Count bright objects in a grayscale or color image.

    The image is converted to grayscale when it has color channels, then
    split into foreground and background with Otsu's threshold. Connected
    foreground regions smaller than ``min_size`` are discarded. The rest are
    labeled and counted.

    Parameters
    ----------
    image : ndarray of shape (M, N) or (M, N, 3) or (M, N, 4)
        Grayscale, RGB, or RGBA image. An alpha channel is ignored.
        Foreground pixels are those strictly brighter than Otsu's threshold.
    min_size : int, optional
        Drop objects whose area is smaller than this many pixels. The default,
        ``0``, keeps every foreground object.

    Returns
    -------
    result : ObjectCountResult
        ``count`` is the number of objects. ``id``, ``area``, and ``centroid``
        describe each object: ``id`` is its connected-component label (starting
        at 1), ``area`` is its size in pixels, and ``centroid`` has shape
        ``(count, 2)`` with ``(row, column)`` coordinates.

    Raises
    ------
    TypeError
        If ``image`` is not a real numeric array, or if ``min_size`` is not an
        integer.
    ValueError
        If ``image`` is empty, has a shape other than ``(M, N)``, ``(M, N, 3)``,
        or ``(M, N, 4)``, or contains non-finite values. Also if ``min_size``
        is negative.

    See Also
    --------
    label
    regionprops
    regionprops_table
    skimage.filters.threshold_otsu

    Examples
    --------
    >>> import numpy as np
    >>> from _skimage2.measure import object_count
    >>> image = np.zeros((12, 12))
    >>> image[1:4, 1:4] = 1
    >>> image[7:11, 7:11] = 1
    >>> result = object_count(image)
    >>> result.count
    2
    >>> result.area.tolist()
    [9, 16]
    >>> result.centroid.tolist()
    [[2.0, 2.0], [8.5, 8.5]]
    """
    min_size = _validate_min_size(min_size)
    image = _as_grayscale_image(image)

    binary = image > threshold_otsu(image)
    props = [prop for prop in regionprops(label(binary)) if prop.area >= min_size]
    ids = np.array([prop.label for prop in props], dtype=int)
    areas = np.array([int(np.rint(prop.area)) for prop in props], dtype=int)
    if props:
        centroids = np.array([prop.centroid for prop in props], dtype=float)
    else:
        centroids = np.empty((0, image.ndim), dtype=float)
    return ObjectCountResult(len(props), ids, areas, centroids)
