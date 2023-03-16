"""Testing functions."""


from time import sleep

from napari_basicpy import BasicWidget


# NOTE this test depends on `make_sample_data` working, might be bad design
# alternative, get pytest fixture from BaSiCPy package and use here
def test_q_widget(make_napari_viewer):
    viewer = make_napari_viewer()

    widget = BasicWidget(viewer)
    viewer.window.add_dock_widget(widget)

    viewer.open_sample("napari-basicpy", "sample_data_random")
    assert len(viewer.layers) == 1

    worker = widget._run()
    sleep(1)

    while True:
        if worker.is_running:
            continue
        else:
            # assert len(viewer.layers) >= 2
            break
