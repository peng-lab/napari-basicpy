from __future__ import annotations

from typing import TYPE_CHECKING, List

import numpy as np

if TYPE_CHECKING:
    import napari


def make_sample_data() -> List[napari.types.LayerData]:
    """Generate a parabolic gradient to simulate uneven illumination"""
    np.random.seed(42)

    n_images = 8

    # Create a gradient
    size = 128
    grid = np.meshgrid(*(2 * (np.linspace(-size // 2 + 1, size // 2, size),)))

    # Create the gradient (flatfield) with and offset (darkfield)
    gradient = sum(d ** 2 for d in grid) ** (1 / 2) + 8
    gradient_int = gradient.astype(np.uint8)  # type: ignore

    # Create an image stack and add poisson noise
    images = np.random.poisson(lam=gradient_int.flatten(), size=(n_images, size ** 2))
    images = images.transpose().reshape((size, size, n_images))
    images = np.moveaxis(images, -1, 0)
    images = 255 - images

    return [(images, {"name": "Uneven Illumination"}, "image")]


make_sample_data()
