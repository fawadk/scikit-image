---
name: dual-tree-tests
description: Write and run scikit-image pytest coverage for both skimage and skimage2. Use when adding tests, changing public APIs, handling deprecations, measuring coverage, or running spin test.
---

# Dual-tree tests

This repo has two public APIs and two test trees. A change is unfinished if only one tree is updated.

## Where tests live

| Surface | Import in tests | Test tree |
|---|---|---|
| Stable `skimage` | `import skimage as ski` or `from skimage...` | `tests/skimage/<submodule>/test_*.py` |
| Experimental `skimage2` | `import _skimage2 as ski2` (not `skimage2` — that raises `ExperimentalAPIWarning`) | `tests/skimage2/<submodule>/test_*.py` |

Doctests are collected from `skimage` and `_skimage2` only (`pytest` `testpaths`). Do not put new tests next to sources under `src/`.

v1-only on purpose: `tests/skimage/future/`, `test_migration.py`, `test_doctest_adapters.py`, `util/test_backends.py`. v2-only: `tests/skimage2/_shared/`, `test_skimage2.py`. Everything else should be mirrored (names may differ, e.g. `test_gray.py` vs `test_grayscale_operators.py`).

## Required cases

- Happy path, dtypes (`uint8` / float), 2D and at least one nD or `channel_axis` case when the function is multi-channel.
- Invalid input → `pytest.raises`.
- API deprecations → `pytest.warns(FutureWarning, match="...")`. Warnings are errors in this suite; do not hide them with a blanket `filterwarnings`.
- RNG: local `np.random.RandomState(<fixed seed>)`, never the global NumPy RNG.

Policy is 100% statement coverage for touched modules (`spin test --coverage`). Thin existing spots (few module-level tests vs Cython): `graph`, `metrics`, `registration` — do not leave new branches there untested.

## Commands

```bash
spin test -- tests/skimage/<submodule> tests/skimage2/<submodule>
spin test -- -k <expression>
spin test --test-modified
spin test --coverage
```

PR CI runs `--test-modified` only. Touching test infra or both APIs: mention the `run-all-tests` label.
