import enum
import logging
import pkg_resources
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import numpy as np
from basicpy import BaSiC
from magicgui.widgets import create_widget
from napari.qt import thread_worker
from qtpy.QtCore import QEvent, Qt
from qtpy.QtGui import QDoubleValidator, QPixmap
from qtpy.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    import napari  # pragma: no cover

logger = logging.getLogger(__name__)

BASICPY_VERSION = pkg_resources.get_distribution("BaSiCPy").version

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

        # header
        header = self.build_header()
        self.layout().addWidget(header)

        self.layout().addWidget(layer_select_container)
        self.layout().addWidget(simple_settings)

        # toggle advanced settings visibility
        self.toggle_advanced_cb = QCheckBox("Show Advanced Settings")
        tb_doc_reference = QLabel()
        tb_doc_reference.setOpenExternalLinks(True)
        tb_doc_reference.setText(
            '<a href="https://basicpy.readthedocs.io/en/latest/api.html">'
            "See docs for settings details</a>"
        )
        self.layout().addWidget(tb_doc_reference)

        self.layout().addWidget(self.toggle_advanced_cb)
        self.toggle_advanced_cb.stateChanged.connect(self.toggle_advanced_settings)

        self.advanced_settings.setVisible(False)
        self.layout().addWidget(advanced_settings)
        self.layout().addWidget(self.run_btn)
        self.layout().addWidget(self.cancel_btn)

    def _build_settings_containers(self):
        advanced = [
            "epsilon",
            "estimation_mode",
            # "fitting_mode",
            # "get_darkfield",
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

            if (type(default) == float or type(default) == int) and (
                default < 0.01 or default > 999
            ):
                widget = ScientificDoubleSpinBox()
                widget.native.setValue(default)
                widget.native.adjustSize()
            else:
                widget = create_widget(
                    value=default,
                    annotation=type_,
                    options={"tooltip": description},
                )

            widget.native.setMinimumWidth(150)
            return widget

        # all settings here will be used to initialize BaSiC
        self._settings = {
            k: build_widget(k)
            for k in BaSiC().settings.keys()
            # exclude settings
            if k not in ["working_size"]
        }

        self._extrasettings = dict()
        # settings to display correction profiles
        # options to show flatfield/darkfield profiles
        # self._extrasettings["show_flatfield"] = create_widget(
        #     value=True,
        #     options={"tooltip": "Output flatfield profile with corrected image"},
        # )
        # self._extrasettings["show_darkfield"] = create_widget(
        #     value=True,
        #     options={"tooltip": "Output darkfield profile with corrected image"},
        # )
        self._extrasettings["get_timelapse"] = create_widget(
            value=False,
            options={"tooltip": "Output timelapse correction with corrected image"},
        )

        simple_settings_container = QGroupBox("Settings")
        simple_settings_container.setLayout(QFormLayout())
        simple_settings_container.layout().setFieldGrowthPolicy(
            QFormLayout.AllNonFixedFieldsGrow
        )

        # this mess is to put scrollArea INSIDE groupBox
        advanced_settings_list = QWidget()
        advanced_settings_list.setLayout(QFormLayout())
        advanced_settings_list.layout().setFieldGrowthPolicy(
            QFormLayout.AllNonFixedFieldsGrow
        )

        for k, v in self._settings.items():
            if k in advanced:
                # advanced_settings_container.layout().addRow(k, v.native)
                advanced_settings_list.layout().addRow(k, v.native)
            else:
                simple_settings_container.layout().addRow(k, v.native)

        advanced_settings_scroll = QScrollArea()
        advanced_settings_scroll.setWidget(advanced_settings_list)

        advanced_settings_container = QGroupBox("Advanced Settings")
        advanced_settings_container.setLayout(QVBoxLayout())
        advanced_settings_container.layout().addWidget(advanced_settings_scroll)

        for k, v in self._extrasettings.items():
            simple_settings_container.layout().addRow(k, v.native)

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
            data, flatfield, darkfield, baseline, meta = update
            print(f"corrected shape: {data.shape}")
            self.viewer.add_image(data, **meta)
            self.viewer.add_image(flatfield)
            if self._settings["get_darkfield"].value:
                self.viewer.add_image(darkfield)
            if self._extrasettings["get_timelapse"].value:
                self.viewer.add_image(baseline)

        @thread_worker(
            start_thread=False,
            # connect={"yielded": update_layer, "returned": update_layer},
            connect={"returned": update_layer},
        )
        def call_basic(data):
            # TODO log basic output to a QtTextEdit or in a new window
            basic = BaSiC(**self.settings)
            logger.info(
                "Calling `basic.fit_transform` with `get_timelapse="
                f"{self._extrasettings['get_timelapse'].value}`"
            )
            corrected = basic.fit_transform(
                data, timelapse=self._extrasettings["get_timelapse"].value
            )

            flatfield = basic.flatfield
            darkfield = basic.darkfield

            if self._extrasettings["get_timelapse"]:
                # flatfield = flatfield / basic.baseline
                ...

            # reenable run button
            # TODO also reenable when error occurs
            self.run_btn.setDisabled(False)

            return corrected, flatfield, darkfield, meta

        # TODO trigger error when BaSiC fails, re-enable "run" button
        worker = call_basic(data)
        self.cancel_btn.clicked.connect(partial(self._cancel, worker=worker))
        worker.finished.connect(self.cancel_btn.clicked.disconnect)
        worker.errored.connect(lambda: self.run_btn.setDisabled(False))
        worker.start()
        return worker

    def _cancel(self, worker):
        logger.info("Cancel requested")
        worker.quit()
        # enable run button
        worker.finished.connect(lambda: self.run_btn.setDisabled(False))

    def showEvent(self, event: QEvent) -> None:  # noqa: D102
        super().showEvent(event)
        self.reset_choices()

    def reset_choices(self, event: Optional[QEvent] = None) -> None:
        """Repopulate image list."""  # noqa DAR101
        self.layer_select.reset_choices(event)
        if len(self.layer_select) < 1:
            self.run_btn.setEnabled(False)
        else:
            self.run_btn.setEnabled(True)

    def toggle_advanced_settings(self) -> None:
        """Toggle the advanced settings container."""
        # container = self.advanced_settings
        container = self.advanced_settings
        if self.toggle_advanced_cb.isChecked():
            container.setHidden(False)
        else:
            container.setHidden(True)

    def build_header(self):
        """Build a header."""
        # TODO spice up the header, maybe add logo

        logo_path = Path(__file__).parent / "_icons/logo.png"
        logo_pm = QPixmap(str(logo_path.absolute()))
        logo_lbl = QLabel()
        logo_lbl.setPixmap(logo_pm)
        logo_lbl.setAlignment(Qt.AlignCenter)
        lbl = QLabel(f"<b>BaSiC Shading Correction</b> v{BASICPY_VERSION}")
        lbl.setAlignment(Qt.AlignCenter)

        header = QWidget()
        header.setLayout(QVBoxLayout())
        header.layout().addWidget(logo_lbl)
        header.layout().addWidget(lbl)

        return header


class QScientificDoubleSpinBox(QDoubleSpinBox):
    """QDoubleSpinBox with scientific notation."""

    def __init__(self, *args, **kwargs):
        """Initialize a QDoubleSpinBox for scientific notation input."""
        super().__init__(*args, **kwargs)
        self.validator = QDoubleValidator()
        self.validator.setNotation(QDoubleValidator.ScientificNotation)
        self.setDecimals(10)
        self.setMinimum(-np.inf)
        self.setMaximum(np.inf)

    def validate(self, text, pos):  # noqa: D102
        return self.validator.validate(text, pos)

    def fixup(self, text):  # noqa: D102
        return self.validator.fixup(text)

    def textFromValue(self, value):  # noqa: D102
        return f"{value:.2E}"


class ScientificDoubleSpinBox:
    """Widget for inputing scientific notation."""

    def __init__(self, *args, **kwargs):
        """Initialize a scientific spinbox widget."""
        self.native = QScientificDoubleSpinBox(*args, **kwargs)

    @property
    def value(self):
        """Return the current value of the widget."""
        return self.native.value()
