"""BaSiCPy plugin for napari."""

try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"


from ._widget import BasicWidget

__all__ = ["BasicWidget"]
