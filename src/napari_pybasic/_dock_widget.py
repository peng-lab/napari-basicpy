from typing import TYPE_CHECKING

from napari_plugin_engine import napari_hook_implementation
from qtpy.QtWidgets import QHBoxLayout, QPushButton, QWidget

if TYPE_CHECKING:
    import napari


class ExampleQWidget(QWidget):
    """Example widget class."""

    def __init__(self, viewer: "napari.viewer.Viewer"):
        """Init example widget."""
        super().__init__()
        self.viewer = viewer

        btn = QPushButton("Click me!")
        btn.clicked.connect(self._on_click)

        self.setLayout(QHBoxLayout())
        self.layout().addWidget(btn)

    def _on_click(self):
        print("napari has", len(self.viewer.layers), "layers")


@napari_hook_implementation
def napari_experimental_provide_dock_widget():  # noqa
    return [ExampleQWidget]
