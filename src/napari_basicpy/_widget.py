import enum
import logging
from functools import partial
from typing import TYPE_CHECKING, Optional

import numpy as np
from magicgui.widgets import create_widget
from napari.qt import thread_worker
from pybasic import BaSiC
from qtpy.QtCore import QEvent
from qtpy.QtWidgets import QFormLayout, QGroupBox, QPushButton, QVBoxLayout, QWidget

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

        layer_select_layout = QFormLayout()
        layer_select_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.layer_select = create_widget(
            annotation="napari.layers.Layer", label="layer_select"
        )
        layer_select_layout.addRow("layer", self.layer_select.native)
        layer_select_container = QWidget()
        layer_select_container.setLayout(layer_select_layout)

        simple_settings, advanced_settings = self._build_settings_containers()

        self.run_btn = QPushButton("Run")
        self.run_btn.clicked.connect(self._run)
        self.cancel_btn = QPushButton("Cancel")

        self.layout().addWidget(layer_select_container)
        self.layout().addWidget(simple_settings)
        self.layout().addWidget(advanced_settings)
        self.layout().addWidget(self.run_btn)
        self.layout().addWidget(self.cancel_btn)

    def _build_settings_containers(self):
        advanced = [
            "epsilon",
            "lambda_darkfield",
            "lambda_flatfield",
            "estimation_mode",
            "max_iterations",
            "max_reweight_iterations",
            "optimization_tol",
            "reweighting_tol",
            "varying_coeff",
        ]

        def build_widget(k):
            field = BaSiC.__fields__[k]
            default = field.default
            description = field.field_info.description
            type_ = field.type_
            if issubclass(type_, enum.Enum):
                try:
                    default = type_[default]
                except KeyError:
                    default = default
            # name = field.name
            return create_widget(
                value=default,
                annotation=type_,
                options={"tooltip": description},
            )

        # all settings here will be used to initialize BaSiC
        self._settings = {k: build_widget(k) for k in BaSiC().settings.keys()}

        simple_settings_container = QGroupBox("Settings")
        simple_settings_container.setLayout(QFormLayout())
        simple_settings_container.layout().setFieldGrowthPolicy(
            QFormLayout.AllNonFixedFieldsGrow
        )

        advanced_settings_container = QGroupBox("Advanced Settings")
        advanced_settings_container.setLayout(QFormLayout())
        advanced_settings_container.layout().setFieldGrowthPolicy(
            QFormLayout.AllNonFixedFieldsGrow
        )

        for k, v in self._settings.items():
            if k in advanced:
                advanced_settings_container.layout().addRow(k, v.native)
            else:
                simple_settings_container.layout().addRow(k, v.native)

        return simple_settings_container, advanced_settings_container

    @property
    def settings(self):
        return {k: v.value for k, v in self._settings.items()}

    def _run(self):

        data, meta, _ = self.layer_select.value.as_layer_data_tuple()
        data = np.moveaxis(data, 0, -1)

        def update_layer(update):
            data, meta = update
            self.viewer.add_image(data, **meta)

        @thread_worker(
            start_thread=False,
            # connect={"yielded": update_layer, "returned": update_layer},
            connect={"returned": update_layer},
        )
        def call_basic(data):
            # FIXME passing settings breaks BaSiC
            # basic = BaSiC(**self.settings)
            basic = BaSiC()
            corrected = basic.fit_predict(data)
            corrected = np.moveaxis(corrected, -1, 0)
            return corrected, meta
            # flatfield = basic.flatfield
            # if self.settings["get_darkfield"]:
            #     darkfield = basic.darkfield
            #     self.viewer.add_image(darkfield)
            # self.viewer.add_image(flatfield)

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
        """Repopulate image list."""  # noqa DAR101
        self.layer_select.reset_choices(event)
