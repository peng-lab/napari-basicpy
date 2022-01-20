import enum
import logging
from typing import TYPE_CHECKING, Optional

import numpy as np
from magicgui.widgets import create_widget
from pybasic import BaSiC
from qtpy.QtCore import QEvent
from qtpy.QtWidgets import QFormLayout, QPushButton, QVBoxLayout, QWidget

# from napari_basicpy._mock_basic import MockBaSiC as BaSiC

if TYPE_CHECKING:
    import napari  # pragma: no cover

logger = logging.getLogger(__name__)


class BasicWidget(QWidget):
    """Example widget class."""

    def __init__(self, viewer: "napari.viewer.Viewer"):
        """Init example widget."""  # noqa DAR101
        super().__init__()
        self.viewer = viewer

        self.setLayout(QVBoxLayout())

        settings_layout = QFormLayout()
        settings_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.settings_container = QWidget()
        self.settings_container.setLayout(settings_layout)

        self.layer_select = create_widget(
            annotation="napari.layers.Layer", label="layer_select"
        )
        settings_layout.addRow("layer", self.layer_select.native)

        for k in BaSiC().settings.keys():
            field = BaSiC.__fields__[k]

            default = field.default
            description = field.field_info.description
            type_ = field.type_
            if issubclass(type_, enum.Enum):
                try:
                    default = type_[default]
                except KeyError:
                    default = default
            name = field.name
            w = create_widget(
                value=default,
                annotation=type_,
                options={"tooltip": description},
            )
            settings_layout.addRow(name, w.native)

        self.run_btn = QPushButton("Run")
        self.run_btn.clicked.connect(self._run)
        self.cancel_btn = QPushButton("Cancel")

        self.layout().addWidget(self.settings_container)
        self.layout().addWidget(self.run_btn)
        self.layout().addWidget(self.cancel_btn)

    def _run(self):

        data, meta, _ = self.layer_select.value.as_layer_data_tuple()
        data = np.moveaxis(data, 0, -1)

        basic = BaSiC()
        corrected = basic.fit_predict(data)
        corrected = np.moveaxis(corrected, -1, 0)
        # the meta dict transfers all metadata settings from original to new layer
        self.viewer.add_image(corrected, **meta)

        def update_layer(image):
            try:
                self.viewer.layers["result"].data = image
            except KeyError:
                self.viewer.add_image(image, name="result")

        # @thread_worker(
        #     start_thread=False,
        #     connect={"yielded": update_layer, "returned": update_layer},
        # )
        def call_basic(data):
            basic = BaSiC(get_darkfield=False)
            corrected = basic(data)
            update_layer(corrected)
            # fit = basic.fit(image, updates=True)
            # while True:
            #     try:
            #         yield next(fit)
            #     except StopIteration as final:
            #         return final.value

        logger.info("Starting BaSiC")

        # worker = call_basic(data)

        # self.cancel_btn.clicked.connect(partial(self._cancel, worker=worker))
        # worker.finished.connect(self.cancel_btn.clicked.disconnect)

        # worker.start()

    # def _get_settings(self):
    #     layout = self.settings_container.layout()
    #     settings = {}
    #     for i in range(layout.count()):
    #         field = layout.itemAt(i).widget()

    #     return settings

    def _cancel(self, worker):
        logger.info("Canceling BasiC")
        worker.quit()

    def showEvent(self, event: QEvent) -> None:  # noqa: D102
        super().showEvent(event)
        self.reset_choices()

    def reset_choices(self, event: Optional[QEvent] = None) -> None:
        """Repopulate image list."""  # noqa DAR101
        self.layer_select.reset_choices(event)
