import numpy as np
import math


class OneEuro1D:
    def __init__(self, freq, min_cutoff=1.0, beta=0.0, d_cutoff=1.0):
        self.freq = float(freq)
        self.min_cutoff = float(min_cutoff)
        self.beta = float(beta)
        self.d_cutoff = float(d_cutoff)
        self.x_prev = None
        self.dx_prev = 0.0

    def _alpha(self, cutoff):
        tau = 1.0 / (2.0 * math.pi * cutoff)
        te = 1.0 / self.freq
        return 1.0 / (1.0 + tau / te)

    def filter(self, x):
        x = float(x)
        if self.x_prev is None:
            self.x_prev = x
            return x

        # dérivée
        dx = (x - self.x_prev) * self.freq
        a_d = self._alpha(self.d_cutoff)
        dx_hat = a_d * dx + (1.0 - a_d) * self.dx_prev

        # cutoff adaptatif
        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        a = self._alpha(cutoff)

        x_hat = a * x + (1.0 - a) * self.x_prev

        self.x_prev = x_hat
        self.dx_prev = dx_hat
        return x_hat


class OneEuro3D:
    def __init__(self, freq=100.0, min_cutoff=1.2, beta=0.02, d_cutoff=1.0):
        self.fx = OneEuro1D(freq, min_cutoff, beta, d_cutoff)
        self.fy = OneEuro1D(freq, min_cutoff, beta, d_cutoff)
        self.fz = OneEuro1D(freq, min_cutoff, beta, d_cutoff)

    def filter(self, v):
        v = np.asarray(v, dtype=float)
        return np.array(
            [self.fx.filter(v[0]), self.fy.filter(v[1]), self.fz.filter(v[2])],
            dtype=float,
        )


class OneEuroDictFilter:
    def __init__(self, freq=100.0, min_cutoff=1.2, beta=0.02, d_cutoff=1.0):
        self.filters = {}
        self.freq = freq
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff

    def update(self, sample: dict) -> dict:
        out = {}
        for k, x in sample.items():
            if k not in self.filters:
                self.filters[k] = OneEuro3D(
                    self.freq, self.min_cutoff, self.beta, self.d_cutoff
                )
            out[k] = self.filters[k].filter(x)
        return out
