"""Test sample data."""
import pytest

@pytest.mark.skip(reason="broken on backend")
def test_data(make_napari_viewer):
    samples = [
        "sample_data_random",
        "sample_data_cell_culture",
        "sample_data_timelapse_brightfield",
        "sample_data_timelapse_nanog",
        "sample_data_timelapse_pu1",
        "sample_data_wsi_brain",
    ]

    viewer = make_napari_viewer()
    for sample in samples:
        n = len(viewer.layers)
        viewer.open_sample(
            "napari-basicpy",
            sample,
        )
        assert len(viewer.layers) == (n + 1)

    # NOTE
    # assert viewer.layers[0].dtype == np.uint8
