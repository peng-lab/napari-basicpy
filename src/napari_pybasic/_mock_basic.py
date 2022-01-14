"""A class to mock BaSiC.

Performs median filter instead of illumination estimation and correction.
"""

from skimage.filters import median
from skimage.morphology import disk


class MockBaSiC:
    def __init__(self, *args, **kwargs):
        ...

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
