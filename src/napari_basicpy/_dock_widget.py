import logging
from functools import partial
from typing import TYPE_CHECKING, Optional

from magicgui.widgets import create_widget
from napari.qt.threading import thread_worker
from napari_plugin_engine import napari_hook_implementation
from qtpy.QtCore import QEvent, Qt
from qtpy.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from napari_basicpy._mock_basic import MockBaSiC as BaSiC

if TYPE_CHECKING:
    import napari  # pragma: no cover

logger = logging.getLogger(__name__)


class BasicWidget(QWidget):
    """Example widget class."""

    def __init__(self, viewer: "napari.viewer.Viewer"):
        """Init example widget."""
        super().__init__()
        self.viewer = viewer

        self.setLayout(QVBoxLayout())
        self.layer_select = create_widget(
            annotation="napari.layers.Layer", label="image_layer"
        )
        self.layout().addWidget(self.layer_select.native)

        settings_layout = QFormLayout()
        settings_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        settings_layout.addRow("Setting 1", QSpinBox())
        settings_layout.addRow("Setting 2", QSlider(Qt.Horizontal))
        settings_layout.addRow("Setting 3", QCheckBox())
        settings_layout.addRow("Setting 4", QCheckBox())
        self.settings_container = QWidget()
        self.settings_container.setLayout(settings_layout)

        self.run_btn = QPushButton("Run")
        self.run_btn.clicked.connect(self._run)
        self.cancel_btn = QPushButton("Cancel")

        self.layout().addWidget(self.settings_container)
        self.layout().addWidget(self.run_btn)
        self.layout().addWidget(self.cancel_btn)

    def _run(self):
        def update_layer(image):
            try:
                self.viewer.layers["result"].data = image
            except KeyError:
                self.viewer.add_image(image, name="result")

        @thread_worker(
            start_thread=False,
            connect={"yielded": update_layer, "returned": update_layer},
        )
        def call_basic(image):
            basic = BaSiC()
            fit = basic.fit(image, updates=True)
            while True:
                try:
                    yield next(fit)
                except StopIteration as final:
                    return final.value

        logger.info("Starting BaSiC")

        data = self.layer_select.value.data
        worker = call_basic(data)

        self.cancel_btn.clicked.connect(partial(self._cancel, worker=worker))
        worker.finished.connect(self.cancel_btn.clicked.disconnect)

        worker.start()

    def _cancel(self, worker):
        logger.info("Canceling BasiC")
        worker.quit()

    def showEvent(self, event: QEvent) -> None:  # noqa: D102
        super().showEvent(event)
        self.reset_choices()

    def reset_choices(self, event: Optional[QEvent] = None) -> None:
        """Repopulate image list."""
        self.layer_select.reset_choices(event)


@napari_hook_implementation
def napari_experimental_provide_dock_widget():  # noqa
    return [BasicWidget]
