"""
TODO
[ ] Add Autosegment feature when checkbox is marked
[ ] Add text instructions to "Hover input field for tooltip"
"""

SEQ_SENTINEL = "__SEQ_SENTINEL__"

import tqdm
from napari.utils.notifications import show_info, show_warning
import enum
import re
import logging
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Optional
import importlib.metadata
import tifffile
import numpy as np
from basicpy import BaSiC
from magicgui.widgets import create_widget
from napari.qt import thread_worker
from qtpy.QtCore import QEvent, Qt
from qtpy.QtGui import QDoubleValidator, QPixmap
from qtpy.QtWidgets import (
    QComboBox,
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    QGridLayout,
    QSlider,
    QSizePolicy,
    QLineEdit,
    QDialog,
    QMessageBox,
)
from matplotlib.backends.backend_qt5agg import FigureCanvas
from .utils import _cast_with_scaling

if TYPE_CHECKING:
    import napari  # pragma: no cover

from magicgui.widgets import ComboBox
from napari.layers import Image
import numpy as np
import tifffile
from qtpy.QtWidgets import QFileDialog

SHOW_LOGO = True  # Show or hide the BaSiC logo in the widget

logger = logging.getLogger(__name__)

import tempfile
import os

cache_path = tempfile.gettempdir()


def save_dialog(parent, file_name):
    """
    Opens a dialog to select a location to save a file

    Parameters
    ----------
    parent : QWidget
        Parent widget for the dialog

    Returns
    -------
    str
        Path of selected file
    """
    dialog = QFileDialog()
    filepath, _ = dialog.getSaveFileName(
        parent,
        "Select location for {} to be saved".format(file_name),
        "./{}.tif".format(file_name),
        filter="TIFF files (*tif *.tiff)",
    )
    if not (filepath.endswith(".tiff") or filepath.endswith(".tif")):
        filepath += ".tiff"
    return filepath


def write_tiff(path: str, data: np.ndarray):
    """
    Write data to a TIFF file

    Parameters
    ----------
    path : str
        Path to save the file
    data : np.ndarray
        Data to save
    """
    tifffile.imwrite(path, data)


class GeneralSetting(QGroupBox):
    # (15.11.2024) Function 1
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVisible(False)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.setStyleSheet("QGroupBox { " "border-radius: 10px}")
        self.viewer = parent.viewer
        self.parent = parent
        self.name = ""  # layer.name

        # layout and parameters for intensity normalization
        vbox = QGridLayout()
        self.setLayout(vbox)

        skip = [
            "resize_mode",
            "resize_params",
            "working_size",
            "fitting_mode",
            "fitting_mode",
            "get_darkfield",
            "smoothness_flatfield",
            "smoothness_darkfield",
            "sparse_cost_darkfield",
            "sort_intensity",
            "device",
        ]
        self._settings = {k: self.build_widget(k) for k in BaSiC().settings.keys() if k not in skip}

        # sort settings into either simple or advanced settings containers
        # _settings = {**{"device": ComboBox(choices=["cpu", "cuda"])}, **_settings}
        i = 0
        for k, v in self._settings.items():
            vbox.addWidget(QLabel(k), i, 0, 1, 1)
            vbox.addWidget(v.native, i, 1, 1, 1)
            i += 1

    def build_widget(self, k):
        field = BaSiC.model_fields[k]
        description = field.description
        default = field.default
        annotation = field.annotation
        # Handle enumerated settings
        try:
            if issubclass(annotation, enum.Enum):
                try:
                    default = annotation[default]
                except KeyError:
                    default = default
        except TypeError:
            pass
        # Define when to use scientific notation spinbox based on default value
        if (type(default) == float or type(default) == int) and (default < 0.01 or default > 999):
            widget = ScientificDoubleSpinBox()
            widget.native.setValue(default)
            widget.native.adjustSize()
        else:
            widget = create_widget(
                value=default,
                annotation=annotation,
                options={"tooltip": description},
            )
        return widget


class AutotuneSetting(QGroupBox):
    # (15.11.2024) Function 1
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVisible(False)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.setStyleSheet("QGroupBox { " "border-radius: 10px}")
        self.viewer = parent.viewer
        self.parent = parent
        self.name = ""  # layer.name

        # layout and parameters for intensity normalization
        vbox = QGridLayout()
        self.setLayout(vbox)

        args = [
            "histogram_qmin",
            "histogram_qmax",
            "vmin_factor",
            "vrange_factor",
            "histogram_bins",
            "histogram_use_fitting_weight",
            "fourier_l0_norm_image_threshold",
            "fourier_l0_norm_fourier_radius",
            "fourier_l0_norm_threshold",
            "fourier_l0_norm_cost_coef",
        ]

        _default = {
            "histogram_qmin": 0.01,
            "histogram_qmax": 0.99,
            "vmin_factor": 0.6,
            "vrange_factor": 1.5,
            "histogram_bins": 1000,
            "histogram_use_fitting_weight": True,
            "fourier_l0_norm_image_threshold": 0.1,
            "fourier_l0_norm_fourier_radius": 10,
            "fourier_l0_norm_threshold": 0.0,
            "fourier_l0_norm_cost_coef": 30,
        }

        self._settings = {k: self.build_widget(k, _default[k]) for k in args}
        # sort settings into either simple or advanced settings containers
        # _settings = {**{"device": ComboBox(choices=["cpu", "cuda"])}, **_settings}
        i = 0
        for k, v in self._settings.items():
            vbox.addWidget(QLabel(k), i, 0, 1, 1)
            vbox.addWidget(v.native, i, 1, 1, 1)
            i += 1

    def build_widget(self, k, default):
        # Handle enumerated settings
        annotation = type(default)
        try:
            if issubclass(annotation, enum.Enum):
                try:
                    default = annotation[default]
                except KeyError:
                    default = default
        except TypeError:
            pass

        # Define when to use scientific notation spinbox based on default value
        if (type(default) == float or type(default) == int) and (default < 0.01 or default > 999):
            widget = ScientificDoubleSpinBox()
            widget.native.setValue(default)
            widget.native.adjustSize()
        else:
            widget = create_widget(
                value=default,
                annotation=annotation,
            )
        # widget.native.setMinimumWidth(150)
        return widget


class SequenceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Choose image sequence folder")
        self.setModal(True)

        self.folder_le = QLineEdit(self)
        self.filter_le = QLineEdit(self)
        self.out_folder_le = QLineEdit(self)

        browse_btn = QPushButton("Browse", self)  # input folder
        browse_out_btn = QPushButton("Browse", self)  # output folder
        ok_btn = QPushButton("OK", self)
        cancel_btn = QPushButton("Cancel", self)

        layout = QGridLayout(self)
        layout.addWidget(QLabel("Folder:"), 0, 0)
        layout.addWidget(self.folder_le, 0, 1)
        layout.addWidget(browse_btn, 0, 2)

        layout.addWidget(QLabel("Filter (comma-separated):"), 1, 0)
        layout.addWidget(self.filter_le, 1, 1, 1, 2)

        layout.addWidget(QLabel("Output folder:"), 2, 0)
        layout.addWidget(self.out_folder_le, 2, 1)
        layout.addWidget(browse_out_btn, 2, 2)

        layout.addWidget(ok_btn, 3, 1)
        layout.addWidget(cancel_btn, 3, 2)

        browse_btn.clicked.connect(self._browse)
        browse_out_btn.clicked.connect(self._browse_out)
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

    def _browse(self):
        path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if path:
            self.folder_le.setText(path)

    def _browse_out(self):
        path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if path:
            self.out_folder_le.setText(path)

    @property
    def folder(self) -> str:
        return self.folder_le.text().strip()

    @property
    def filters(self) -> str:
        return self.filter_le.text().strip()

    @property
    def filters_tokens(self) -> list[str]:
        return parse_filter_text(self.filter_le.text())

    @property
    def out_folder(self) -> str:
        return self.out_folder_le.text().strip()


def parse_filter_text(s: str) -> list[str]:
    if s is None:
        return []
    s = s.replace(", ", ",")
    tokens = [t.strip() for t in s.split(",") if t.strip()]
    return tokens


class SaveOptionsDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Save options")
        layout = QGridLayout(self)

        self.dtype_cb = QComboBox(self)
        self.dtype_cb.addItems(["float32", "uint16", "uint8"])

        self.mode_cb = QComboBox(self)
        self.mode_cb.addItems(
            [
                "preserve (no clip, auto-rescale if out-of-range)",
                "rescale to full range",
            ]
        )

        layout.addWidget(QLabel("Save dtype:"), 0, 0)
        layout.addWidget(self.dtype_cb, 0, 1)
        layout.addWidget(QLabel("Scaling:"), 1, 0)
        layout.addWidget(self.mode_cb, 1, 1)

        btn_ok = QPushButton("OK", self)
        btn_cancel = QPushButton("Cancel", self)
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        layout.addWidget(btn_ok, 2, 0)
        layout.addWidget(btn_cancel, 2, 1)

        if hasattr(parent, "_last_save_dtype"):
            self.dtype_cb.setCurrentText(parent._last_save_dtype)
        if hasattr(parent, "_last_save_mode"):
            self.mode_cb.setCurrentText(parent._last_save_mode)

    @property
    def dtype(self) -> str:
        return self.dtype_cb.currentText()

    @property
    def mode(self) -> str:
        return self.mode_cb.currentText()


class BasicWidget(QWidget):
    """Example widget class."""

    def __init__(self, viewer: "napari.viewer.Viewer"):
        """Init example widget."""  # noqa DAR101
        super().__init__()

        self.viewer = viewer

        # Define builder functions
        widget = QWidget()
        main_layout = QGridLayout()
        widget.setLayout(main_layout)

        # Define builder functions
        def build_header_container():
            """Build the widget header."""
            header_container = QWidget()
            header_layout = QVBoxLayout()
            header_container.setLayout(header_layout)
            # show/hide logo
            if SHOW_LOGO:
                logo_path = str((Path(__file__).parent / "_icons/logo.png").absolute())
                logo_pm = QPixmap(logo_path)
                logo_lbl = QLabel()
                logo_lbl.setPixmap(logo_pm)
                logo_lbl.setAlignment(Qt.AlignCenter)
                header_layout.addWidget(logo_lbl)
            # Show label and package version of BaSiCPy
            lbl = QLabel(f"<b>BaSiCPy Shading Correction</b>")
            lbl.setAlignment(Qt.AlignCenter)
            header_layout.addWidget(lbl)

            return header_container

        def build_doc_reference_label():
            doc_reference_label = QLabel()
            doc_reference_label.setOpenExternalLinks(True)
            # doc_reference_label.setText(
            #     '<a href="https://basicpy.readthedocs.io/en/latest/api.html#basicpy.basicpy.BaSiC">'
            #     "See docs for settings details</a>"
            # )

            doc_reference_label.setText(
                '<a style= color:white; style= background-color:green; href="https://basicpy.readthedocs.io/en/latest/api.html#basicpy.basicpy.BaSiC">See docs for settings details</a>'
            )

            return doc_reference_label

        # Build fit widget components
        header_container = build_header_container()
        doc_reference_lbl = build_doc_reference_label()
        self.fit_widget = self.build_fit_widget_container()
        self.transform_widget = self.build_transform_widget_container()

        # Add containers/widgets to layout

        self.btn_fit = QPushButton("Fit BaSiCPy")
        self.btn_fit.setCheckable(True)
        self.btn_fit.clicked.connect(self.toggle_fit)
        self.btn_fit.setStyleSheet("""QPushButton{background:green;border-radius:5px;}""")
        self.btn_fit.setFixedWidth(400)

        self.btn_transform = QPushButton("Apply BaSiCPy")
        self.btn_transform.setCheckable(True)
        self.btn_transform.clicked.connect(self.toggle_transform)
        self.btn_transform.setStyleSheet("""QPushButton{background:green;border-radius:5px;}""")
        self.btn_transform.setFixedWidth(400)

        main_layout.addWidget(header_container, 0, 0, 1, 2)
        main_layout.addWidget(self.btn_fit, 1, 0)
        main_layout.addWidget(self.fit_widget, 2, 0)
        main_layout.addWidget(self.btn_transform, 3, 0)
        main_layout.addWidget(self.transform_widget, 4, 0)
        main_layout.addWidget(doc_reference_lbl, 6, 0)

        main_layout.setAlignment(Qt.AlignTop)

        scroll_area = QScrollArea()
        scroll_area.setWidget(widget)
        scroll_area.setWidgetResizable(True)

        self.setLayout(QVBoxLayout())
        self.layout().addWidget(scroll_area)

        self.run_fit_btn.clicked.connect(self._run_fit)
        self.autotune_btn.clicked.connect(self._run_autotune)
        self.run_transform_btn.clicked.connect(self._run_transform)
        self.save_fit_btn.clicked.connect(self._save_fit)
        self.save_transform_btn.clicked.connect(self._save_transform)

    def build_transform_widget_container(self):
        settings_container = QGroupBox("Parameters")  # make groupbox
        settings_layout = QGridLayout()
        label_timelapse = QLabel("is_timelapse:")
        label_timelapse.setFixedWidth(150)
        self.checkbox_is_timelapse_transform = QCheckBox()
        self.checkbox_is_timelapse_transform.setChecked(False)

        settings_layout.addWidget(label_timelapse, 0, 0)
        settings_layout.addWidget(self.checkbox_is_timelapse_transform, 0, 1)

        settings_layout.setAlignment(Qt.AlignTop)
        settings_container.setLayout(settings_layout)

        inputs_container = self.build_transform_inputs_containers()

        self.run_transform_btn = QPushButton("Run")
        self.cancel_transform_btn = QPushButton("Cancel")
        self.save_transform_btn = QPushButton("Save")

        transform_layout = QGridLayout()
        transform_layout.addWidget(inputs_container, 0, 0, 1, 2)
        transform_layout.addWidget(settings_container, 1, 0, 1, 2)
        transform_layout.addWidget(self.run_transform_btn, 2, 0, 1, 1)
        transform_layout.addWidget(self.cancel_transform_btn, 2, 1, 1, 1)
        transform_layout.addWidget(self.save_transform_btn, 3, 0, 1, 2)
        transform_layout.setAlignment(Qt.AlignTop)

        transform_widget = QWidget()
        transform_widget.setLayout(transform_layout)
        transform_widget.setVisible(False)

        return transform_widget

    def build_fit_widget_container(self):

        settings_container = self.build_settings_containers()
        inputs_container = self.build_inputs_containers()

        advanced_parameters = QGroupBox("Advanced parameters")
        advanced_parameters_layout = QGridLayout()
        advanced_parameters.setLayout(advanced_parameters_layout)

        # general settings
        self.general_settings = GeneralSetting(self)
        self.btn_general_settings = QPushButton("General settings")
        self.btn_general_settings.setCheckable(True)
        self.btn_general_settings.clicked.connect(self.toggle_general_settings)
        self.checkbox_get_darkfield.clicked.connect(self.toggle_lineedit_smoothness_darkfield)
        advanced_parameters_layout.addWidget(self.btn_general_settings)

        advanced_parameters_layout.addWidget(self.general_settings)

        # autotune settings
        self.autotune_settings = AutotuneSetting(self)
        self.btn_autotune_settings = QPushButton("Autotune settings")
        self.btn_autotune_settings.setCheckable(True)
        self.btn_autotune_settings.clicked.connect(self.toggle_autotune_settings)
        advanced_parameters_layout.addWidget(self.btn_autotune_settings)
        advanced_parameters_layout.addWidget(self.autotune_settings)

        self.run_fit_btn = QPushButton("Run")
        self.cancel_fit_btn = QPushButton("Cancel")
        self.save_fit_btn = QPushButton("Save")

        fit_layout = QGridLayout()
        fit_layout.addWidget(inputs_container, 0, 0, 1, 2)
        fit_layout.addWidget(settings_container, 1, 0, 1, 2)
        fit_layout.addWidget(advanced_parameters, 2, 0, 1, 2)
        fit_layout.addWidget(self.run_fit_btn, 3, 0, 1, 1)
        fit_layout.addWidget(self.cancel_fit_btn, 3, 1, 1, 1)
        fit_layout.addWidget(self.save_fit_btn, 4, 0, 1, 2)
        fit_layout.setAlignment(Qt.AlignTop)
        fit_widget = QWidget()
        fit_widget.setLayout(fit_layout)
        fit_widget.setVisible(False)
        return fit_widget

    def build_transform_inputs_containers(self):
        input_gb = QGroupBox("Inputs")
        gb_layout = QGridLayout()

        label_image = QLabel("images:")
        label_image.setFixedWidth(150)
        label_flatfield = QLabel("flatfield:")
        label_flatfield.setFixedWidth(150)
        label_darkfield = QLabel("darkfield:")
        label_darkfield.setFixedWidth(150)
        label_weight = QLabel("Segmentation mask:")
        label_weight.setFixedWidth(150)

        self.transform_image_select = ComboBox(choices=self.layers_image_transform)
        self.transform_image_select.changed.connect(self._on_transform_image_changed)

        self.fit_weight_select = ComboBox(choices=self.layers_weight_transform)
        self.checkbox_is_timelapse_transform.clicked.connect(self.toggle_weight_in_transform)
        self.flatfield_select = ComboBox(choices=self.layers_image_flatfield)
        self.darkfield_select = ComboBox(choices=self.layers_weight_darkfield)

        self.inverse_cb_transform = QCheckBox("Inverse")
        self.inverse_cb_transform.setChecked(False)

        note = QLabel("1 = background, 0 = foreground")
        note.setWordWrap(True)
        note.setStyleSheet("color: gray;")

        gb_layout.addWidget(label_image, 0, 0, 1, 1)
        gb_layout.addWidget(self.transform_image_select.native, 0, 1, 1, 2)
        gb_layout.addWidget(label_flatfield, 1, 0, 1, 1)
        gb_layout.addWidget(self.flatfield_select.native, 1, 1, 1, 2)
        gb_layout.addWidget(label_darkfield, 2, 0, 1, 1)
        gb_layout.addWidget(self.darkfield_select.native, 2, 1, 1, 2)
        gb_layout.addWidget(label_weight, 3, 0, 1, 1)
        gb_layout.addWidget(self.fit_weight_select.native, 3, 1, 1, 1)
        gb_layout.addWidget(self.inverse_cb_transform, 3, 2, 1, 1)
        gb_layout.addWidget(note, 4, 1, 1, 2)

        gb_layout.setAlignment(Qt.AlignTop)
        input_gb.setLayout(gb_layout)

        return input_gb

    def _fast_count_files(self, folder: str, tokens: list[str], hard_limit: int = 1_000_000):
        """尽量快地统计匹配个数；用 scandir 并可提前停止。"""
        cnt = 0
        try:
            with os.scandir(folder) as it:
                for e in it:
                    if not e.is_file():
                        continue
                    name = e.name
                    ok = True
                    for t in tokens or []:
                        if t and t not in name:
                            ok = False
                            break
                    if ok:
                        cnt += 1
                        if cnt >= hard_limit:  # 防止极端目录把统计时间拖太久
                            break
        except Exception:
            logger.exception("fast count failed")
        return cnt

    def _on_transform_image_changed(self, value):
        if value == SEQ_SENTINEL:
            dlg = SequenceDialog(self)
            if dlg.exec_() == QDialog.Accepted:
                self.transform_sequence_folder = dlg.folder
                self.transform_sequence_filters = dlg.filters_tokens
                self.transform_sequence_out_folder = dlg.out_folder

                if not self.transform_sequence_folder:
                    QMessageBox.warning(self, "No folder", "Please choose a source folder.")
                elif not self.transform_sequence_out_folder:
                    QMessageBox.warning(self, "No output folder", "Please choose an output folder.")
                elif os.path.abspath(self.transform_sequence_out_folder) == os.path.abspath(
                    self.transform_sequence_folder
                ):
                    QMessageBox.warning(
                        self, "Output = Input", "Output folder must be different from the source folder."
                    )
                else:
                    from napari.qt import thread_worker
                    from napari.utils.notifications import show_info, show_warning

                    # 防重复：如果还在统计，就别再启动
                    if getattr(self, "_count_worker_running", False):
                        show_warning("Counting is already in progress…")
                    else:
                        self._count_worker_running = True
                        show_info(
                            "Sequence selected.\n"
                            f"Source: {self.transform_sequence_folder}\n"
                            f"Output: {self.transform_sequence_out_folder}\n"
                            f"Filters: {', '.join(self.transform_sequence_filters) if self.transform_sequence_filters else '(none)'}\n"
                            "Counting matched files…"
                        )

                        @thread_worker(start_thread=True)  # 关键：自动启动
                        def _count_worker():
                            return self._fast_count_files(
                                self.transform_sequence_folder,
                                self.transform_sequence_filters,
                            )

                        def _on_done(n):
                            self._count_worker_running = False
                            show_info(
                                f"Matched files: {n}\n"
                                f"Source: {self.transform_sequence_folder}\n"
                                f"Output: {self.transform_sequence_out_folder}"
                            )

                        def _on_err(e=None):
                            self._count_worker_running = False
                            show_warning("Counting failed; see logs.")

                        w = _count_worker()
                        w.returned.connect(_on_done)
                        w.errored.connect(_on_err)
                        # 注意：不要再调用 w.start() 了！

            # 重置下拉
            try:
                self.transform_image_select.value = "--select input images--"
            except Exception:
                pass

    def _natural_key(self, s: str):
        return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]

    def _list_sequence_files(self, folder: str, tokens: list[str]) -> list[str]:
        names = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
        for t in tokens or []:
            names = [n for n in names if t in n]
        names.sort(key=self._natural_key)
        return [os.path.join(folder, n) for n in names]

    def _iter_chunks(self, seq: list, size: int):
        for i in range(0, len(seq), size):
            yield seq[i : i + size]

    def build_inputs_containers(self):
        input_gb = QGroupBox("Inputs")
        gb_layout = QGridLayout()

        label_image = QLabel("images:")
        label_image.setFixedWidth(150)
        label_fitting_weight = QLabel("segmentation mask:")
        label_fitting_weight.setFixedWidth(150)

        note = QLabel("1 = background, 0 = foreground")
        note.setWordWrap(True)
        note.setStyleSheet("color: gray;")

        self.inverse_cb = QCheckBox("Inverse")
        self.inverse_cb.setChecked(False)

        self.fit_image_select = ComboBox(choices=self.layers_image_fit)
        self.weight_select = ComboBox(choices=self.layers_weight)

        gb_layout.addWidget(label_image, 0, 0, 1, 1)
        gb_layout.addWidget(self.fit_image_select.native, 0, 1, 1, 2)
        gb_layout.addWidget(label_fitting_weight, 1, 0, 1, 1)
        gb_layout.addWidget(self.weight_select.native, 1, 1, 1, 1)  # 之前是 (1,1,1,2)
        gb_layout.addWidget(self.inverse_cb, 1, 2, 1, 1)
        gb_layout.addWidget(note, 2, 1, 1, 2)

        gb_layout.setAlignment(Qt.AlignTop)
        input_gb.setLayout(gb_layout)

        return input_gb

    def build_settings_containers(self):
        simple_settings_gb = QGroupBox("Parameters")  # make groupbox
        gb_layout = QGridLayout()

        label_get_darkfield = QLabel("get_darkfield:")
        label_timelapse = QLabel("is_timelapse:")
        label_sorting = QLabel("sort_intensity:")
        label_smoothness_flatfield = QLabel("smoothness_flatfield:")
        label_smoothness_darkfield = QLabel("smoothness_darkfield:")

        label_get_darkfield.setFixedWidth(150)
        label_timelapse.setFixedWidth(150)
        label_sorting.setFixedWidth(150)
        label_smoothness_flatfield.setFixedWidth(150)
        label_smoothness_darkfield.setFixedWidth(150)

        self.lineedit_smoothness_flatfield = QLineEdit()
        self.lineedit_smoothness_darkfield = QLineEdit()
        self.lineedit_smoothness_darkfield.setEnabled(False)
        self.lineedit_smoothness_darkfield.setText("Not available")
        self.lineedit_smoothness_flatfield.setText("")

        self.autotune_btn = QPushButton("autotune")
        self.autotune_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        self.checkbox_get_darkfield = QCheckBox()
        self.checkbox_get_darkfield.setChecked(False)
        self.checkbox_is_timelapse = QCheckBox()
        self.checkbox_is_timelapse.setChecked(False)
        self.checkbox_sorting = QCheckBox()
        self.checkbox_sorting.setChecked(False)

        gb_layout.addWidget(label_get_darkfield, 0, 0)
        gb_layout.addWidget(self.checkbox_get_darkfield, 0, 1)
        gb_layout.addWidget(label_timelapse, 1, 0)
        gb_layout.addWidget(self.checkbox_is_timelapse, 1, 1)
        gb_layout.addWidget(label_sorting, 2, 0)
        gb_layout.addWidget(self.checkbox_sorting, 2, 1)
        gb_layout.addWidget(label_smoothness_flatfield, 3, 0, 1, 1)
        gb_layout.addWidget(self.lineedit_smoothness_flatfield, 3, 1, 1, 1)
        gb_layout.addWidget(label_smoothness_darkfield, 4, 0, 1, 1)
        gb_layout.addWidget(self.lineedit_smoothness_darkfield, 4, 1, 1, 1)
        gb_layout.addWidget(self.autotune_btn, 3, 2, 2, 1)

        gb_layout.setAlignment(Qt.AlignTop)
        simple_settings_gb.setLayout(gb_layout)

        return simple_settings_gb

    def toggle_lineedit_smoothness_darkfield(self, checked: bool):
        if self.checkbox_get_darkfield.isChecked():
            self.lineedit_smoothness_darkfield.setEnabled(True)
            self.lineedit_smoothness_darkfield.clear()
        else:
            self.lineedit_smoothness_darkfield.setEnabled(False)
            self.lineedit_smoothness_darkfield.setText("Not available")

    def toggle_transform(self, checked: bool):
        # Switching the visibility of the transform_widget
        if self.transform_widget.isVisible():
            self.transform_widget.setVisible(False)
        else:
            self.transform_widget.setVisible(True)
            self.fit_widget.setVisible(False)

    def toggle_fit(self, checked: bool):
        # Switching the visibility of the fit_widget
        if self.fit_widget.isVisible():
            self.fit_widget.setVisible(False)
        else:
            self.fit_widget.setVisible(True)
            self.transform_widget.setVisible(False)

    def toggle_weight_in_transform(self, checked: bool):
        # Switching the visibility of the fit_widget
        if self.checkbox_is_timelapse_transform.isChecked():
            self.fit_weight_select.enabled = True
        else:
            self.fit_weight_select.enabled = False

    def toggle_general_settings(self, checked: bool):
        # Switching the visibility of the General settings
        if self.general_settings.isVisible():
            self.general_settings.setVisible(False)
            self.btn_general_settings.setText("General settings")
        else:
            self.general_settings.setVisible(True)
            self.btn_general_settings.setText("Hide general settings")

    def toggle_autotune_settings(self, checked: bool):
        # Switching the visibility of the Autotune settings
        if self.autotune_settings.isVisible():
            self.autotune_settings.setVisible(False)
            self.btn_autotune_settings.setText("Autotune settings")
        else:
            self.autotune_settings.setVisible(True)
            self.btn_autotune_settings.setText("Hide autotune settings")

    def layers_image_fit(
        self,
        wdg: ComboBox,
    ) -> list[Image]:
        return ["--select input images--"] + [layer for layer in self.viewer.layers]

    def layers_image_transform(self, wdg) -> list:
        special = [
            ("--select input images--", "--select input images--"),
            ("Choose sequence from a folder…", SEQ_SENTINEL),
        ]
        layer_items = [(layer.name, layer) for layer in self.viewer.layers]
        return special + layer_items

    def layers_weight_transform(
        self,
        wdg: ComboBox,
    ) -> list[Image]:
        return ["none"] + [layer for layer in self.viewer.layers]

    def layers_weight_darkfield(
        self,
        wdg: ComboBox,
    ) -> list[Image]:
        return ["none"] + [layer for layer in self.viewer.layers]

    def layers_image_flatfield(
        self,
        wdg: ComboBox,
    ) -> list[Image]:
        return ["--select input images--"] + [layer for layer in self.viewer.layers]

    def layers_weight(
        self,
        wdg: ComboBox,
    ) -> list[Image]:
        return ["none"] + [layer for layer in self.viewer.layers]

    @property
    def settings(self):
        """Get settings for BaSiC."""
        return {k: v.value for k, v in self._settings.items()}

    def _run_autotune(self):
        # disable run button
        self.autotune_btn.setDisabled(True)
        # get layer information
        data, meta, _ = self.fit_image_select.value.as_layer_data_tuple()

        if self.weight_select.value == "none":
            fitting_weight = None
        else:
            fitting_weight, meta_fitting_weight, _ = self.weight_select.value.as_layer_data_tuple()
            if self.inverse_cb.isChecked():
                fitting_weight = fitting_weight > 0
                fitting_weight = 1 - fitting_weight

        # define function to update napari viewer
        def update_layer(update):
            smoothness_flatfield, smoothness_darkfield = update
            self.lineedit_smoothness_flatfield.setText(str(smoothness_flatfield))
            if _settings["get_darkfield"]:
                self.lineedit_smoothness_darkfield.setText(str(smoothness_darkfield))

        @thread_worker(
            start_thread=False,
            # connect={"yielded": update_layer, "returned": update_layer},
            connect={"returned": update_layer},
        )
        def call_autotune(data, fitting_weight, _settings, _settings_autotune):
            basic = BaSiC(**_settings)
            basic.autotune(
                data,
                is_timelapse=self.checkbox_is_timelapse.isChecked(),
                fitting_weight=fitting_weight,
                **_settings_autotune,
            )
            smoothness_flatfield = basic.smoothness_flatfield
            smoothness_darkfield = basic.smoothness_darkfield
            return smoothness_flatfield, smoothness_darkfield

        _settings_tmp = self.general_settings._settings
        _settings = {}
        for key, item in _settings_tmp.items():
            _settings[key] = item.value

        _settings.update(
            {
                "get_darkfield": self.checkbox_get_darkfield.isChecked(),
                "sort_intensity": self.checkbox_sorting.isChecked(),
            }
        )

        _settings_autotune_tmp = self.autotune_settings._settings
        _settings_autotune = {}
        for key, item in _settings_autotune_tmp.items():
            if key != "histogram_bins":
                _settings_autotune[key] = item.value
            else:
                _settings_autotune[key] = int(item.value)

        worker = call_autotune(data, fitting_weight, _settings, _settings_autotune)
        worker.finished.connect(lambda: self.autotune_btn.setDisabled(False))
        worker.errored.connect(lambda: self.autotune_btn.setDisabled(False))
        worker.start()
        logger.info("Autotune worker started")
        return worker

    def _estimate_batch_size(self, first_file, target_gb=0.5, hard_cap=64):
        arr = tifffile.imread(first_file)
        bytes_per = arr.nbytes if hasattr(arr, "nbytes") else np.asarray(arr).nbytes
        if bytes_per <= 0:
            return 16
        bs = max(1, int((target_gb * (1024**3)) // bytes_per))
        return min(bs, hard_cap)

    def _run_transform(self):
        self.run_transform_btn.setDisabled(True)

        # ====== SEQUENCE 模式 ======
        if getattr(self, "transform_sequence_folder", None):
            try:
                src_dir = self.transform_sequence_folder
                out_dir = getattr(self, "transform_sequence_out_folder", "")
                if not out_dir:
                    QMessageBox.warning(self, "No output folder", "Please choose an output folder.")
                    self.run_transform_btn.setDisabled(False)
                    return
                os.makedirs(out_dir, exist_ok=True)

                # 只构造文件名列表（不排序就不会阻塞太久；若一定要自然排序再排序）
                names = [f for f in os.scandir(src_dir) if f.is_file()]
                # 过滤
                tokens = getattr(self, "transform_sequence_filters", []) or []
                if tokens:
                    keep = []
                    for e in names:
                        name = e.name
                        ok = True
                        for t in tokens:
                            if t and t not in name:
                                ok = False
                                break
                        if ok:
                            keep.append(e)
                    names = keep
                if not names:
                    QMessageBox.warning(self, "No files", "No files matched your filters.")
                    self.run_transform_btn.setDisabled(False)
                    return

                # 可选：自然排序（慢一些，放在需要时）
                names = sorted((e.name for e in names), key=self._natural_key)
                files = [os.path.join(src_dir, n) for n in names]

                flatfield, _, _ = self.flatfield_select.value.as_layer_data_tuple()
                if self.darkfield_select.value == "none":
                    darkfield = np.zeros_like(flatfield)
                else:
                    darkfield, _, _ = self.darkfield_select.value.as_layer_data_tuple()

                # 序列模式禁用 mask
                if self.fit_weight_select.value != "none":
                    QMessageBox.warning(
                        self,
                        "Segmentation mask ignored",
                        "Sequence mode does not support a per-frame segmentation mask. It will be ignored.",
                    )
                fitting_weight = None

                # 估算 batch 大小
                batch_size = self._estimate_batch_size(files[0], target_gb=0.5, hard_cap=64)

                def on_progress(state):
                    done, total = state
                    # 更新状态栏而不是弹无数提示
                    self.viewer.status = f"BaSiCPy: {done}/{total} ({done/total:.1%})"

                def on_done(_out_dir):
                    QMessageBox.information(self, "Done", f"Saved corrected frames to:\n{_out_dir}")
                    try:
                        first_out = os.path.join(_out_dir, os.path.basename(files[0]))
                        preview = tifffile.imread(first_out)
                        self.viewer.add_image(preview, name="corrected_preview")
                    except Exception:
                        pass
                    self.run_transform_btn.setDisabled(False)

                """
                @thread_worker(start_thread=False, connect={"yielded": on_progress, "returned": on_done})
                def call_basic_sequence(files, out_dir, batch_size):
                    basic = BaSiC()
                    basic.darkfield = np.asarray(darkfield)
                    basic.flatfield = np.asarray(flatfield)

                    total = len(files)
                    done = 0

                    for i in range(0, total, batch_size):
                        batch = files[i : i + batch_size]
                        # 逐个读，避免临时峰值内存过大；不需要 np.stack
                        corrected_list = []
                        for fp in batch:
                            img = tifffile.imread(fp)
                            corr = basic.transform(
                                img,
                                is_timelapse=self.checkbox_is_timelapse_transform.isChecked(),
                                fitting_weight=fitting_weight,
                            )
                            corrected_list.append(np.asarray(corr))

                        # 写回磁盘（文件名不变）
                        for fp, arr in zip(batch, corrected_list):
                            out_fp = os.path.join(out_dir, os.path.basename(fp))
                            tifffile.imwrite(out_fp, arr)

                        done += len(batch)
                        yield (done, total)

                    return out_dir
                """

                @thread_worker(start_thread=False, connect={"yielded": on_progress, "returned": on_done})
                def call_basic_sequence(files, out_dir, _settings):
                    basic = BaSiC(**_settings)
                    basic.darkfield = np.asarray(darkfield)
                    basic.flatfield = np.asarray(flatfield)

                    total = len(files)
                    done = 0
                    batch_size = 50  # 固定一次 50 张

                    im_max = tifffile.imread(files[0])
                    target_dtype = im_max.dtype

                    if np.issubdtype(target_dtype, np.floating):
                        pass
                    else:
                        print("estimate dynamic range...")
                        for i in tqdm.tqdm(range(1, total, 20), leave=False):
                            im_max = np.maximum(im_max, tifffile.imread(files[i]))
                        im_max = im_max / basic.flatfield

                        if target_dtype == np.uint8:
                            if im_max.max() > 255:
                                basic.flatfield = basic.flatfield / 255 * im_max.max()
                        elif target_dtype == np.uint16:
                            if im_max.max() > 65535:
                                basic.flatfield = basic.flatfield / 65535 * im_max.max()
                        else:
                            raise ValueError(f"Unsupported numpy dtype: {target_dtype}")

                    for i in tqdm.tqdm(range(0, total, batch_size), desc="transforming: "):
                        batch = files[i : i + batch_size]

                        # 一次性读取 50 张并堆叠
                        imgs = [tifffile.imread(fp) for fp in batch]
                        try:
                            stack = np.stack(imgs, axis=0)  # 形状 ~ (B, Y, X) 或 (B, Z, Y, X)
                        except Exception:
                            # 如果形状不一致，明确报错，避免 silent fail
                            shapes = {np.asarray(im).shape for im in imgs}
                            raise ValueError(f"Images in this batch have different shapes: {shapes}")

                        # 一次性做 transform
                        corrected = basic.transform(
                            stack,
                            is_timelapse=self.checkbox_is_timelapse_transform.isChecked(),  # 批量按时间序列处理
                            fitting_weight=None,  # 序列模式禁用 mask
                        )
                        corr = np.asarray(corrected)

                        # 逐张写回（文件名保持不变）
                        if corr.ndim == 2:
                            # 极端情况：只有 1 张
                            out_fp = os.path.join(out_dir, os.path.basename(batch[0]))
                            tifffile.imwrite(out_fp, corr)
                        else:
                            for j, src_fp in enumerate(batch):
                                out_fp = os.path.join(out_dir, os.path.basename(src_fp))
                                tifffile.imwrite(out_fp, corr[j])

                        # 释放本批内存（可选）
                        del imgs, stack, corr

                        done += len(batch)
                        yield (done, total)

                    return out_dir

                _basic_settings_tmp = self.general_settings._settings
                _basic_settings = {}
                for key, item in _basic_settings_tmp.items():
                    _basic_settings[key] = item.value

                _basic_settings.update(
                    {
                        "get_darkfield": self.checkbox_get_darkfield.isChecked(),
                        "sort_intensity": self.checkbox_sorting.isChecked(),
                    }
                )

                worker = call_basic_sequence(files, out_dir, _basic_settings)
                worker.errored.connect(lambda e=None: self.run_transform_btn.setDisabled(False))
                self.cancel_transform_btn.clicked.connect(partial(self._cancel_transform, worker=worker))
                worker.finished.connect(self.cancel_transform_btn.clicked.disconnect)
                worker.start()
                return

            except Exception as e:
                logger.exception("Sequence transform failed")
                QMessageBox.critical(self, "Error", str(e))
                self.run_transform_btn.setDisabled(False)
                return

        # ====== 否则：保持你原来的 layer → layer 流程（不变） ======
        try:
            data, meta, _ = self.transform_image_select.value.as_layer_data_tuple()
            flatfield, _, _ = self.flatfield_select.value.as_layer_data_tuple()
            if self.darkfield_select.value == "none":
                darkfield = np.zeros_like(flatfield)
            else:
                darkfield, _, _ = self.darkfield_select.value.as_layer_data_tuple()
            if self.fit_weight_select.value == "none":
                fitting_weight = None
            else:
                fitting_weight, _, _ = self.fit_weight_select.value.as_layer_data_tuple()
                if self.inverse_cb_transform.isChecked():
                    fitting_weight = fitting_weight > 0
                    fitting_weight = 1 - fitting_weight
        except:
            logger.error("Error inputs.")
            self.run_transform_btn.setDisabled(False)
            return

        def update_layer(update):
            data, meta = update
            self.corrected = data
            self.viewer.add_image(data, name="corrected")
            print("Transform is done.")

        @thread_worker(start_thread=False, connect={"returned": update_layer})
        def call_basic(data, _settings, _basic_settings):
            basic = BaSiC(**_basic_settings)
            basic.darkfield = np.asarray(darkfield)
            basic.flatfield = np.asarray(flatfield)
            corrected = basic.transform(data, **_settings)
            self.run_transform_btn.setDisabled(False)
            return corrected, meta

        _settings = {
            "is_timelapse": self.checkbox_is_timelapse_transform.isChecked(),
            "fitting_weight": fitting_weight,
        }

        _basic_settings_tmp = self.general_settings._settings
        _basic_settings = {}
        for key, item in _basic_settings_tmp.items():
            _basic_settings[key] = item.value

        _basic_settings.update(
            {
                "get_darkfield": self.checkbox_get_darkfield.isChecked(),
                "sort_intensity": self.checkbox_sorting.isChecked(),
            }
        )

        worker = call_basic(data, _settings, _basic_settings)
        self.cancel_transform_btn.clicked.connect(partial(self._cancel_transform, worker=worker))
        worker.finished.connect(self.cancel_transform_btn.clicked.disconnect)
        worker.finished.connect(lambda: self.run_transform_btn.setDisabled(False))
        worker.errored.connect(lambda: self.run_transform_btn.setDisabled(False))
        worker.start()
        logger.info("BaSiC worker for tranform only started")
        return worker

    def _run_fit(self):
        # disable run button
        self.run_fit_btn.setDisabled(True)
        # get layer information
        try:
            data, meta, _ = self.fit_image_select.value.as_layer_data_tuple()

            if self.weight_select.value == "none":
                fitting_weight = None
            else:
                fitting_weight, meta_fitting_weight, _ = self.weight_select.value.as_layer_data_tuple()
                if self.inverse_cb.isChecked():
                    fitting_weight = fitting_weight > 0
                    fitting_weight = 1 - fitting_weight
        except:
            logger.error("Error inputs.")
            self.run_fit_btn.setDisabled(False)
            return

        # define function to update napari viewer
        def update_layer(update):
            uncorrected, data, flatfield, darkfield, _settings, meta = update
            self.viewer.add_image(data, name="corrected")
            self.viewer.add_image(flatfield, name="flatfield")
            self.corrected = data
            self.flatfield = flatfield
            if _settings["get_darkfield"]:
                self.viewer.add_image(darkfield, name="darkfield")
                self.darkfield = darkfield
            if self.checkbox_is_timelapse.isChecked():
                import matplotlib.pyplot as plt
                import matplotlib.image as mpimg

                m, n = data.shape[-2:]

                fig, (ax1, ax2) = plt.subplots(1, 2)
                # fig.tight_layout()
                # fig.set_size_inches(n / 300, m / 300)
                baseline_before = np.squeeze(np.asarray(uncorrected.mean((-2, -1))))
                baseline_after = np.squeeze(np.asarray(data.mean((-2, -1))))
                baseline_max = 1.01 * max(baseline_after.max(), baseline_before.max())
                baseline_min = 0.99 * min(baseline_after.min(), baseline_before.min())
                ax1.plot(baseline_before)
                ax2.plot(baseline_after)
                ax1.tick_params(labelsize=10)
                ax2.tick_params(labelsize=10)
                ax1.set_title("before BaSiCPy")
                ax2.set_title("after BaSiCPy")
                ax1.set_xlabel("slices")
                ax2.set_xlabel("slices")
                ax1.set_ylabel("baseline value")
                # ax2.set_ylabel("baseline value")
                ax1.set_ylim([baseline_min, baseline_max])
                ax2.set_ylim([baseline_min, baseline_max])

                plt.savefig(os.path.join(cache_path, "baseline.jpg"), dpi=300)
                baseline_image = mpimg.imread(os.path.join(cache_path, "baseline.jpg"))
                self.viewer.add_image(baseline_image, name="baseline")
                os.remove(os.path.join(cache_path, "baseline.jpg"))
            print("BaSiCPy fit is done.")

        @thread_worker(
            start_thread=False,
            # connect={"yielded": update_layer, "returned": update_layer},
            connect={"returned": update_layer},
        )
        def call_basic(data, fitting_weight, _settings):
            basic = BaSiC(**_settings)
            corrected = basic(
                data,
                is_timelapse=self.checkbox_is_timelapse.isChecked(),
                fitting_weight=fitting_weight,
            )
            flatfield = basic.flatfield
            darkfield = basic.darkfield
            self.run_fit_btn.setDisabled(False)  # reenable run button
            return data, corrected, flatfield, darkfield, _settings, meta

        _settings_tmp = self.general_settings._settings
        _settings = {}
        for key, item in _settings_tmp.items():
            _settings[key] = item.value

        if self.lineedit_smoothness_flatfield.text() != "":
            try:
                params_smoothness_flatfield = float(self.lineedit_smoothness_flatfield.text())
                _settings.update({"smoothness_flatfield": params_smoothness_flatfield})
            except:
                logger.warning("Invalid smoothness_flatfield")
        if self.lineedit_smoothness_darkfield.isEnabled():
            try:
                params_smoothness_darkfield = float(self.lineedit_smoothness_darkfield.text())
                _settings.update({"smoothness_darkfield": params_smoothness_darkfield})
            except:
                logger.warning("Invalid smoothness_darkfield")

        _settings.update(
            {
                "get_darkfield": self.checkbox_get_darkfield.isChecked(),
                "sort_intensity": self.checkbox_sorting.isChecked(),
            }
        )
        worker = call_basic(data, fitting_weight, _settings)
        self.cancel_fit_btn.clicked.connect(partial(self._cancel_fit, worker=worker))
        worker.finished.connect(self.cancel_fit_btn.clicked.disconnect)
        worker.finished.connect(lambda: self.run_fit_btn.setDisabled(False))
        worker.errored.connect(lambda: self.run_fit_btn.setDisabled(False))
        worker.start()
        logger.info("BaSiC worker started")
        return worker

    def _cancel_fit(self, worker):
        logger.info("Cancel requested")
        worker.quit()
        # enable run button
        worker.finished.connect(lambda: self.run_fit_btn.setDisabled(False))

    def _cancel_transform(self, worker):
        logger.info("Cancel requested")
        worker.quit()
        # enable run button
        worker.finished.connect(lambda: self.run_transform_btn.setDisabled(False))

    # def _save_fit(self):
    #     try:
    #         filepath = save_dialog(self, "corrected_image")
    #         write_tiff(filepath, self.corrected)
    #     except:
    #         self.logger.info("Corrected image is not found.")
    #     try:
    #         filepath = save_dialog(self, "flatfield")
    #         data = self.flatfield.astype(np.float32)
    #         write_tiff(filepath, data)
    #     except:
    #         self.logger.info("Flatfield is not found.")
    #     if self.checkbox_get_darkfield.isChecked():
    #         try:
    #             filepath = save_dialog(self, "darkfield")
    #             data = self.darkfield.astype(np.float32)
    #             write_tiff(filepath, data)
    #         except:
    #             self.logger.info("Darkfield is not found.")
    #     else:
    #         pass
    #     print("Saving is done.")
    #     return

    def _save_fit(self):
        ok_any = False
        try:
            if hasattr(self, "corrected"):
                opt = SaveOptionsDialog(parent=self)
                if opt.exec_() == QDialog.Accepted:
                    self._last_save_dtype = opt.dtype
                    self._last_save_mode = opt.mode

                    fp = save_dialog(self, "corrected_image")
                    if fp:
                        arr = _cast_with_scaling(self.corrected, opt.dtype, opt.mode)
                        write_tiff(fp, arr)
                        ok_any = True
            else:
                logger.info("No 'corrected' result to save in _save_fit().")
        except Exception as e:
            logger.exception("Failed to save corrected image (fit)")
            QMessageBox.critical(self, "Save failed", f"Corrected image: {e}")

        try:
            if hasattr(self, "flatfield"):
                fp = save_dialog(self, "flatfield")
                if fp:
                    write_tiff(fp, self.flatfield.astype(np.float32))
                    ok_any = True
            else:
                logger.info("No 'flatfield' to save in _save_fit().")
        except Exception as e:
            logger.exception("Failed to save flatfield")
            QMessageBox.critical(self, "Save failed", f"Flatfield: {e}")

        if self.checkbox_get_darkfield.isChecked():
            try:
                if hasattr(self, "darkfield"):
                    fp = save_dialog(self, "darkfield")
                    if fp:
                        write_tiff(fp, self.darkfield.astype(np.float32))
                        ok_any = True
                else:
                    logger.info("No 'darkfield' to save in _save_fit().")
            except Exception as e:
                logger.exception("Failed to save darkfield")
                QMessageBox.critical(self, "Save failed", f"Darkfield: {e}")

        if ok_any:
            QMessageBox.information(self, "Saved", "Export finished successfully.")
            try:
                self.viewer.status = "BaSiCPy: export finished."
            except Exception:
                pass
        else:
            QMessageBox.information(self, "Nothing saved", "No file was selected or available.")

    # def _save_transform(self):
    #     try:
    #         filepath = save_dialog(self, "corrected_image")
    #         write_tiff(filepath, self.corrected)
    #     except:
    #         self.logger.info("Corrected image is not found.")
    #     print("Saving is done.")
    #     return

    def _save_transform(self):
        try:
            if hasattr(self, "corrected"):
                opt = SaveOptionsDialog(parent=self)
                if opt.exec_() != QDialog.Accepted:
                    return
                self._last_save_dtype = opt.dtype
                self._last_save_mode = opt.mode

                fp = save_dialog(self, "corrected_image")
                if fp:
                    arr = _cast_with_scaling(self.corrected, opt.dtype, opt.mode)
                    write_tiff(fp, arr)
                    QMessageBox.information(self, "Saved", f"Saved to:\n{fp}")
            else:
                QMessageBox.warning(self, "No data", "Corrected image is not found.")
        except Exception as e:
            logger.exception("Failed to save corrected image")
            QMessageBox.critical(self, "Save failed", str(e))

    def showEvent(self, event: QEvent) -> None:  # noqa: D102
        super().showEvent(event)
        self.reset_choices()

    def reset_choices(self, event: Optional[QEvent] = None) -> None:
        """Repopulate image layer dropdown list."""  # noqa DAR101
        self.fit_image_select.reset_choices(event)
        self.transform_image_select.reset_choices(event)
        self.flatfield_select.reset_choices(event)
        self.darkfield_select.reset_choices(event)

        self.weight_select.reset_choices(event)
        self.fit_weight_select.reset_choices(event)

        # # If no layers are present, disable the 'run' button
        # print(self.fit_image_select.value)
        # print(self.fit_image_select.value is "--select input images--")
        # if self.fit_image_select.value is "--select input images--":
        #     self.run_fit_btn.setEnabled(False)
        #     self.autotune_btn.setEnabled(False)
        # else:
        #     self.run_fit_btn.setEnabled(True)
        #     self.autotune_btn.setEnabled(True)

        # if (self.transform_image_select.value is "--select input images--") and (
        #     self.flatfield_select.value is "--select input images--"
        # ):
        #     self.run_transform_btn.setEnabled(False)
        # else:
        #     self.run_transform_btn.setEnabled(True)


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
