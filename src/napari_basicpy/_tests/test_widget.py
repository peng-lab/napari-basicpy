from napari_basicpy._widget import BasicWidget


def test_q_widget(make_napari_viewer, qtbot):
    viewer = make_napari_viewer()

    widget = BasicWidget(viewer)
    viewer.window.add_dock_widget(widget)

    viewer.open_sample("napari-basicpy", "sample_data_random")
    assert len(viewer.layers) == 1

    widget.reset_choices()
    widget.fit_image_select.value = viewer.layers[0]

    worker = widget._run_fit()
    assert worker is not None

    with qtbot.waitSignal(worker.finished, timeout=60000):
        pass

    layer_names = [layer.name for layer in viewer.layers]
    assert "corrected" in layer_names
    assert "flatfield" in layer_names