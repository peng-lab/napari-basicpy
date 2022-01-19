def test_data(make_napari_viewer):

    viewer = make_napari_viewer()
    n = len(viewer.layers)
    viewer.open_sample("napari-basicpy", "sample_data")
    assert len(viewer.layers) == (n + 1)
