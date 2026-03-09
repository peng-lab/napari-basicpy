"""Test sample data."""

def test_data(make_napari_viewer):
    samples = [
        "sample_data_random",
    ]

    viewer = make_napari_viewer()
    for sample in samples:
        n = len(viewer.layers)
        viewer.open_sample(
            "napari-basicpy",
            sample,
        )
        assert len(viewer.layers) == (n + 1)
