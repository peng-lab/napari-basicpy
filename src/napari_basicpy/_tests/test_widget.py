"""Testing functions."""


from napari_basicpy import BasicWidget


# NOTE this test depends on `make_sample_data` working, might be bad design
# alternative, get pytest fixture from BaSiCPy package and use here
def test_q_widget(make_napari_viewer):
    viewer = make_napari_viewer()

    widget = BasicWidget(viewer)
    viewer.window.add_dock_widget(widget)

    viewer.open_sample("napari-basicpy", "sample_data")
    assert len(viewer.layers) == 1

    widget._run()
    assert len(viewer.layers) == 2
