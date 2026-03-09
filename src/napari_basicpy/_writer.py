"""
This module is an example of a barebones writer plugin for napari.

It implements the Writer specification.
see: https://napari.org/stable/plugins/guides.html?#writers

Replace code below according to your needs.
"""

from __future__ import annotations

import numpy as np
import tifffile
from qtpy.QtWidgets import QFileDialog


def save_dialog(parent):
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
        "Select location for TIFF-File to be created",
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
    data = data.astype(np.uint16)
    OmeTiffWriter.save(data, path, dim_order_out="YX")
