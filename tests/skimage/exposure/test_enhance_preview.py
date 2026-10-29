import numpy as np
import pytest
from numpy.testing import assert_allclose, assert_array_equal

from skimage.exposure import enhance_preview, equalize_hist
from skimage.restoration import denoise_bilateral


# Random seed generated for this file; results depend on it.
RNG_SEED = 2376609660


def test_enhance_preview_is_public():
    assert callable(enhance_preview)


def test_enhance_preview_disabled_returns_copy():
    image = np.array([[1, 2], [3, 4]], dtype=np.uint8)
    out = enhance_preview(image)
    assert out is not image
    assert out.dtype == image.dtype
    assert_array_equal(out, image)


def test_enhance_preview_does_not_mutate_input():
    image = np.arange(16, dtype=np.uint8).reshape(4, 4)
    original = image.copy()
    enhance_preview(
        image,
        equalize=True,
        denoise=True,
        sigma_color=0.1,
        sigma_spatial=1,
    )
    assert_array_equal(image, original)


def test_enhance_preview_equalize_matches_equalize_hist():
    dark = np.array([[0, 1], [2, 40]], dtype=np.uint8)
    out = enhance_preview(dark, equalize=True)
    assert_allclose(out, equalize_hist(dark))
    assert out.max() > (dark.max() / np.iinfo(dark.dtype).max)


def test_enhance_preview_denoise_matches_bilateral():
    rng = np.random.RandomState(RNG_SEED)
    noisy = rng.random((16, 16))
    out = enhance_preview(noisy, denoise=True, sigma_color=0.1, sigma_spatial=1)
    expected = denoise_bilateral(noisy, sigma_color=0.1, sigma_spatial=1)
    assert_allclose(out, expected)


def test_enhance_preview_sigma_changes_result():
    rng = np.random.RandomState(RNG_SEED)
    noisy = rng.random((16, 16))
    narrow = enhance_preview(noisy, denoise=True, sigma_color=0.05, sigma_spatial=1)
    wide = enhance_preview(noisy, denoise=True, sigma_color=0.05, sigma_spatial=3)
    assert not np.allclose(narrow, wide)


def test_enhance_preview_denoise_then_equalize():
    rng = np.random.RandomState(RNG_SEED)
    noisy = rng.random((16, 16))
    out = enhance_preview(
        noisy,
        equalize=True,
        denoise=True,
        sigma_color=0.1,
        sigma_spatial=1,
    )
    denoised = denoise_bilateral(noisy, sigma_color=0.1, sigma_spatial=1)
    assert_allclose(out, equalize_hist(denoised))


def test_enhance_preview_rgb_equalize_per_channel():
    rng = np.random.RandomState(RNG_SEED)
    rgb = rng.random((8, 8, 3))
    out = enhance_preview(rgb, equalize=True, channel_axis=-1)
    expected = np.stack([equalize_hist(rgb[..., c]) for c in range(3)], axis=-1)
    assert out.shape == rgb.shape
    assert_allclose(out, expected)


def test_enhance_preview_channel_axis_first():
    rng = np.random.RandomState(RNG_SEED)
    channels_first = rng.random((3, 8, 8))
    out = enhance_preview(channels_first, equalize=True, channel_axis=0)
    expected = np.stack([equalize_hist(channels_first[c]) for c in range(3)], axis=0)
    assert_allclose(out, expected)


def test_enhance_preview_rgb_denoise_then_equalize():
    rng = np.random.RandomState(RNG_SEED)
    rgb = rng.random((8, 8, 3))
    out = enhance_preview(
        rgb,
        equalize=True,
        denoise=True,
        sigma_color=0.1,
        sigma_spatial=1,
        channel_axis=-1,
    )
    denoised = denoise_bilateral(
        rgb, sigma_color=0.1, sigma_spatial=1, channel_axis=-1
    )
    expected = np.stack([equalize_hist(denoised[..., c]) for c in range(3)], axis=-1)
    assert_allclose(out, expected)


def test_enhance_preview_accepts_array_like():
    raw = [[0, 10], [20, 30]]
    out = enhance_preview(raw, equalize=True)
    assert_allclose(out, equalize_hist(np.asarray(raw)))


def test_enhance_preview_rejects_non_numeric():
    with pytest.raises(TypeError, match="numeric"):
        enhance_preview("not-an-image")


def test_enhance_preview_rejects_1d():
    with pytest.raises(ValueError, match="2D grayscale"):
        enhance_preview(np.array([1, 2, 3], dtype=np.uint8))


def test_enhance_preview_requires_channel_axis_for_color():
    rgb = np.zeros((4, 4, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="channel_axis"):
        enhance_preview(rgb)


def test_enhance_preview_rejects_channel_axis_on_grayscale():
    image = np.zeros((4, 4), dtype=np.uint8)
    with pytest.raises(ValueError, match="channel_axis"):
        enhance_preview(image, channel_axis=-1)


def test_enhance_preview_rejects_nonpositive_sigma():
    image = np.zeros((4, 4), dtype=np.float64)
    with pytest.raises(ValueError, match="sigma_spatial"):
        enhance_preview(image, denoise=True, sigma_spatial=0)
    with pytest.raises(ValueError, match="sigma_color"):
        enhance_preview(image, denoise=True, sigma_spatial=1, sigma_color=-0.1)
