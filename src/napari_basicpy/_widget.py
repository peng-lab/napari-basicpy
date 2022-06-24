import enum
import logging
from functools import partial
from typing import TYPE_CHECKING, Optional

from basicpy import BaSiC
from magicgui.widgets import create_widget
from napari.qt import thread_worker
from qtpy.QtCore import QEvent
from qtpy.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

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
        self.advanced_settings = advanced_settings

        self.run_btn = QPushButton("Run")
        self.run_btn.clicked.connect(self._run)
        self.cancel_btn = QPushButton("Cancel")

        # TODO add BaSiC header

        self.layout().addWidget(layer_select_container)
        self.layout().addWidget(simple_settings)

        # toggle advanced settings visibility
        self.toggle_advanced_cb = QCheckBox("Show Advanced Settings")
        self.layout().addWidget(self.toggle_advanced_cb)
        self.toggle_advanced_cb.stateChanged.connect(self.toggle_advanced_settings)

        self.scrollArea = QScrollArea()
        self.scrollArea.setWidget(self.advanced_settings)
        self.scrollArea.setVisible(False)

        self.layout().addWidget(self.scrollArea)
        # self.advanced_settings.setVisible(False)
        # self.layout().addWidget(advanced_settings)
        self.layout().addWidget(self.run_btn)
        self.layout().addWidget(self.cancel_btn)

    def _build_settings_containers(self):
        advanced = [
            # "get_darkfield",
            "epsilon",
            "estimation_mode",
            # "fitting_mode",
            "lambda_darkfield_coef",
            "lambda_darkfield_sparse_coef",
            "lambda_darkfield",
            "lambda_flatfield_coef",
            "lambda_flatfield",
            "max_iterations",
            "max_mu_coef",
            "max_reweight_iterations_baseline",
            "max_reweight_iterations",
            "mu_coef",
            "optimization_tol_diff",
            "optimization_tol",
            "resize_method",
            "reweighting_tol",
            "rho",
            "sort_intensity",
            "varying_coeff",
            "working_size",
        ]

        def build_widget(k):
            field = BaSiC.__fields__[k]
            default = field.default
            description = field.field_info.description
            type_ = field.type_
            try:
                if issubclass(type_, enum.Enum):
                    try:
                        default = type_[default]
                    except KeyError:
                        default = default
            except TypeError:
                pass
            # name = field.name
            return create_widget(
                value=default,
                annotation=type_,
                options={"tooltip": description},
            )

        # all settings here will be used to initialize BaSiC
        self._settings = {k: build_widget(k) for k in BaSiC().settings.keys()}

        self._extrasettings = dict()
        # settings to display correction profiles
        # options to show flatfield/darkfield profiles
        self._extrasettings["show_flatfield"] = create_widget(
            value=True,
            options={"tooltip": "Output flatfield profile with corrected image"},
        )
        self._extrasettings["show_darkfield"] = create_widget(
            value=True,
            options={"tooltip": "Output darkfield profile with corrected image"},
        )
        self._extrasettings["show_timelapse"] = create_widget(
            value=False,
            options={"tooltip": "Output timelapse correction with corrected image"},
        )

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

        # for k, v in self._extrasettings.items():
        #     simple_settings_container.layout().addRow(k, v.native)

        return simple_settings_container, advanced_settings_container

    @property
    def settings(self):
        """Get settings for BaSiC."""
        return {k: v.value for k, v in self._settings.items()}

    def _run(self):

        # TODO visualization (on button?) to represent that program is running
        # disable run button
        self.run_btn.setDisabled(True)

        data, meta, _ = self.layer_select.value.as_layer_data_tuple()

        def update_layer(update):
            data, flatfield, darkfield, meta = update
            self.viewer.add_image(data, **meta)
            if self._extrasettings["show_flatfield"].value:
                self.viewer.add_image(flatfield)
            if (
                self._extrasettings["show_darkfield"].value
                and self._settings["get_darkfield"].value
            ):
                self.viewer.add_image(darkfield)

        @thread_worker(
            start_thread=False,
            # connect={"yielded": update_layer, "returned": update_layer},
            connect={"returned": update_layer},
        )
        def call_basic(data):
            # TODO log basic output to a QtTextEdit or in a new window

            basic = BaSiC(**self.settings)
            corrected = basic.fit_transform(data)

            flatfield = basic.flatfield
            darkfield = basic.darkfield

            # reenable run button
            self.run_btn.setDisabled(False)

            return corrected, flatfield, darkfield, meta

        worker = call_basic(data)
        self.cancel_btn.clicked.connect(partial(self._cancel, worker=worker))
        worker.finished.connect(self.cancel_btn.clicked.disconnect)
        worker.start()
        return worker

    def _cancel(self, worker):
        logger.info("Canceling BasiC")
        worker.quit()
        # enable run button
        worker.finished.connect(lambda: self.run_btn.setDisabled(False))

    def showEvent(self, event: QEvent) -> None:  # noqa: D102
        super().showEvent(event)
        self.reset_choices()

    def reset_choices(self, event: Optional[QEvent] = None) -> None:
        """Repopulate image list."""  # noqa DAR101
        self.layer_select.reset_choices(event)

    def toggle_advanced_settings(self) -> None:
        """Toggle the advanced settings container."""
        # container = self.advanced_settings
        container = self.scrollArea
        if self.toggle_advanced_cb.isChecked():
            container.setHidden(False)
        else:
            container.setHidden(True)

    def build_header(self):
        ...
