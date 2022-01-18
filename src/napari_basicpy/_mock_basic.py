"""A class to mock BaSiC.

Performs median filter instead of illumination estimation and correction.
"""

from skimage.filters import median
from skimage.morphology import disk
from pydantic import Field, BaseModel, PrivateAttr
from enum import Enum
import numpy as np

NUM_THREADS=1

class EstimationMode(Enum):

    l0: str = "l0"


class Device(Enum):

    cpu: str = "cpu"
    gpu: str = "gpu"
    tpu: str = "tpu"

class MockBaSiC(BaseModel):
    darkfield: np.ndarray = Field(
        default_factory=lambda: np.zeros((128, 128), dtype=np.float64),
        description="Holds the darkfield component for the shading model.",
        exclude=True,  # Don't dump to output json/yaml
    )
    device: Device = Field(
        Device.cpu,
        description="Must be one of ['cpu','gpu','tpu'].",
        exclude=True,  # Don't dump to output json/yaml
    )
    epsilon: float = Field(
        0.1,
        description="Weight regularization term.",
    )
    estimation_mode: EstimationMode = Field(
        "l0",
        description="Flatfield offset for weight updates.",
    )
    flatfield: np.ndarray = Field(
        default_factory=lambda: np.zeros((128, 128), dtype=np.float64),
        description="Holds the flatfield component for the shading model.",
        exclude=True,  # Don't dump to output json/yaml
    )
    get_darkfield: bool = Field(
        False,
        description="When True, will estimate the darkfield shading component.",
    )
    lambda_darkfield: float = Field(
        0.0,
        description="Darkfield offset for weight updates.",
    )
    lambda_flatfield: float = Field(
        0.0,
        description="Flatfield offset for weight updates.",
    )
    max_iterations: int = Field(
        500,
        description="Maximum number of iterations.",
    )
    max_reweight_iterations: int = Field(
        10,
        description="Maximum number of reweighting iterations.",
    )
    max_workers: int = Field(
        NUM_THREADS,
        description="Maximum number of threads used for processing.",
        exclude=True,  # Don't dump to output json/yaml
    )
    optimization_tol: float = Field(
        1e-6,
        description="Optimization tolerance.",
    )
    reweighting_tol: float = Field(
        1e-3,
        description="Reweighting tolerance.",
    )
    varying_coeff: bool = Field(
        True,
        description="This description will need to be filled in.",
    )
    working_size: int = Field(
        128,
        description="Size for running computations. Should be a power of 2 (2^n).",
    )


    class Config:

        arbitrary_types_allowed = True

    def __init__(self, **kwargs) -> None:
        """Initialize BaSiC with the provided settings."""

        super().__init__(**kwargs)

    def fit(self, images, updates=True):
        CONVERGED = False
        iter = 1
        while not CONVERGED:
            print("iteration", iter)
            # iterative process
            im = median(images, disk(iter))
            iter += 1
            if iter > 12:
                CONVERGED = True
            if updates:
                yield im
        return 255 - im

    def predict(self, images):
        return images

    def fit_predict(self, images):
        self.fit(images)
        return self.predict(images)

    def profiles(self):
        ...

    def score(self):
        ...
