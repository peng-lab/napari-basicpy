"""Testing functions."""

import numpy as np
import pytest

from napari_basicpy import BasicWidget


# NOTE alternatively, use sample data, but that will make dependent on another test
@pytest.fixture
def test_data():

    np.random.seed(42)  # answer to the meaning of life, should work here too

    n_images = 8

    """Generate a parabolic gradient to simulate uneven illumination"""
    # Create a gradient
    size = 128
    grid = np.meshgrid(*(2 * (np.linspace(-size // 2 + 1, size // 2, size),)))

    # Create the gradient (flatfield) with and offset (darkfield)
    gradient = sum(d ** 2 for d in grid) ** (1 / 2) + 8
    gradient_int = gradient.astype(np.uint8)

    # Ground truth, for correctness checking
    truth = gradient / gradient.mean()

    # Create an image stack and add poisson noise
    images = np.random.poisson(lam=gradient_int.flatten(), size=(n_images, size ** 2))
    images = images.transpose().reshape((size, size, n_images))

    return gradient, images, truth


def test_q_widget(make_napari_viewer, test_data):
    viewer = make_napari_viewer()
    widget = BasicWidget(viewer)
    viewer.window.add_dock_widget(widget)
    _, data, _ = test_data
    data = np.moveaxis(data, -1, 0)
    viewer.add_image(data)
    assert len(viewer.layers) == 1
