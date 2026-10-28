import numpy as np
import pytest

from skimage.measure import (
    blur_effect,
    label,
    object_count,
    regionprops,
    regionprops_table,
    shannon_entropy,
)


def _two_blobs(dtype=float):
    """Return a 12x12 image with a 3x3 blob and a 4x4 blob."""
    image = np.zeros((12, 12), dtype=dtype)
    if dtype is bool:
        value = True
    elif np.issubdtype(dtype, np.integer):
        value = 255
    else:
        value = 1
    image[1:4, 1:4] = value
    image[7:11, 7:11] = value
    return image


def test_object_count_import_and_existing_measure_api():
    import skimage as ski

    assert callable(ski.measure.object_count)
    assert "object_count" in ski.measure.__all__
    assert all(
        callable(func)
        for func in (
            label,
            regionprops,
            regionprops_table,
            shannon_entropy,
            blur_effect,
            object_count,
        )
    )


def test_two_blobs_are_counted():
    result = object_count(_two_blobs())

    assert result.count == 2
    assert result.id.tolist() == [1, 2]
    assert result.area.tolist() == [9, 16]
    np.testing.assert_allclose(result.centroid, [[2.0, 2.0], [8.5, 8.5]])
    assert result.centroid.shape == (2, 2)


def test_rgb_input_counts_the_same_objects():
    gray = _two_blobs(dtype=np.uint8)
    rgb = np.stack([gray, gray, gray], axis=-1)

    result = object_count(rgb)

    assert rgb.ndim == 3
    assert result.count == 2
    assert result.area.tolist() == [9, 16]


def test_rgba_ignores_alpha_channel():
    gray = _two_blobs(dtype=np.uint8)
    rgba = np.zeros((12, 12, 4), dtype=np.uint8)
    rgba[..., :3] = gray[..., np.newaxis]
    rgba[..., 3] = 10

    result = object_count(rgba)

    assert result.count == 2


def test_min_size_drops_smaller_objects():
    image = _two_blobs()

    assert object_count(image, min_size=0).count == 2
    assert object_count(image, min_size=9).count == 2
    kept = object_count(image, min_size=10)
    assert kept.count == 1
    assert kept.area.tolist() == [16]
    assert kept.id.tolist() == [2]

    none = object_count(image, min_size=17)
    assert none.count == 0
    assert none.id.shape == (0,)
    assert none.area.shape == (0,)
    assert none.centroid.shape == (0, 2)


def test_uniform_image_has_no_objects():
    result = object_count(np.zeros((8, 8), dtype=np.uint8))

    assert result.count == 0


def test_bool_image_does_not_warn():
    result = object_count(_two_blobs(dtype=bool))

    assert result.count == 2


def test_empty_image_raises_value_error():
    with pytest.raises(ValueError, match="empty"):
        object_count(np.empty((0, 10)))


def test_wrong_type_raises_type_error():
    with pytest.raises(TypeError, match="numeric"):
        object_count(None)
    with pytest.raises(TypeError, match="numeric"):
        object_count("coins")
    with pytest.raises(TypeError, match="numeric"):
        object_count([["a", "b"], ["c", "d"]])


def test_wrong_shape_raises_value_error():
    # A last axis of length 3 or 4 is a color image. Anything else is rejected
    # before thresholding, including volumes and channel-first stacks.
    with pytest.raises(ValueError, match=r"shape \(M, N\)"):
        object_count(np.zeros((5,)))
    with pytest.raises(ValueError, match=r"shape \(M, N\)"):
        object_count(np.zeros((4, 4, 5)))
    with pytest.raises(ValueError, match=r"shape \(M, N\)"):
        object_count(np.zeros((2, 8, 8)))


def test_nonfinite_image_raises_value_error():
    image = _two_blobs()
    image[0, 0] = np.nan

    with pytest.raises(ValueError, match="finite"):
        object_count(image)


def test_invalid_min_size_raises_clear_error():
    image = _two_blobs()

    with pytest.raises(TypeError, match="min_size"):
        object_count(image, min_size=1.5)
    with pytest.raises(TypeError, match="min_size"):
        object_count(image, min_size=True)
    with pytest.raises(ValueError, match="min_size"):
        object_count(image, min_size=-1)


def test_numpy_integer_min_size_is_accepted():
    result = object_count(_two_blobs(), min_size=np.int64(10))

    assert result.count == 1
