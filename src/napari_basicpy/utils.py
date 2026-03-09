import torch
import tqdm
import numpy as np


def _dtype_limits(dtype):
    dt = np.dtype(dtype)
    if np.issubdtype(dt, np.integer):
        info = np.iinfo(dt)
        return info.min, info.max
    return None, None


def _cast_with_scaling(
    arr: np.ndarray,
    target_dtype: str,
    mode: str,
):
    a = np.asarray(arr)

    if target_dtype == "float32":
        return a.astype(np.float32, copy=False)

    tmin, tmax = _dtype_limits(target_dtype)
    if tmin is None:
        return a.astype(np.float32, copy=False)

    if mode == "preserve (no clip, auto-rescale if out-of-range)":
        a_min = float(np.nanmin(a))
        a_max = float(np.nanmax(a))

        if a_min >= tmin and a_max <= tmax:
            return a.astype(target_dtype, copy=False)

        if not np.isfinite(a_min) or not np.isfinite(a_max) or a_max <= a_min:
            scaled = np.zeros_like(a, dtype=np.float32)
        else:
            scaled = (a - a_min) / (a_max - a_min)
        out = (scaled * (tmax - tmin) + tmin).round()
        return np.clip(out, tmin, tmax).astype(target_dtype, copy=False)

    if mode == "rescale to full range":
        a_min = float(np.nanmin(a))
        a_max = float(np.nanmax(a))
        if not np.isfinite(a_min) or not np.isfinite(a_max) or a_max <= a_min:
            scaled = np.zeros_like(a, dtype=np.float32)
        else:
            scaled = (a - a_min) / (a_max - a_min)
        out = (scaled * (tmax - tmin) + tmin).round()
        return np.clip(out, tmin, tmax).astype(target_dtype, copy=False)

    # fallback
    return a.astype(target_dtype, copy=False)
