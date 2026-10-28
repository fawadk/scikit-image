from _skimage2.measure.object_count import object_count as object_count  # noqa: F401

__all__ = ['object_count']

from skimage._doctest_adapters import adapt_doctests

adapt_doctests(globals())
