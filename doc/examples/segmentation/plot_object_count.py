"""
==========================
Count objects in an image
==========================

``skimage.measure.object_count`` turns the usual threshold, label, and
measure steps into one call. Bright pixels (above Otsu's threshold) are
the foreground. ``min_size`` drops specks that are smaller than a coin.
"""

import matplotlib.pyplot as plt

from skimage import data
from skimage.filters import threshold_otsu
from skimage.measure import find_contours, label, object_count

image = data.coins()
min_size = 100
result = object_count(image, min_size=min_size)

# Outlines follow the same Otsu labels that ``object_count`` kept.
labels = label(image > threshold_otsu(image))

fig, ax = plt.subplots(figsize=(8, 6))
ax.imshow(image, cmap='gray')
for object_id, (row, col) in zip(result.id, result.centroid, strict=True):
    contours = find_contours(labels == object_id, 0.5)
    if not contours:
        continue
    contour = max(contours, key=len)
    ax.plot(contour[:, 1], contour[:, 0], color='red', linewidth=1.5)
    ax.text(
        col,
        row,
        str(object_id),
        color='yellow',
        ha='center',
        va='center',
        fontsize=8,
    )
ax.set_title(f'{result.count} objects (min_size={min_size})')
ax.set_axis_off()
plt.tight_layout()
plt.show()
