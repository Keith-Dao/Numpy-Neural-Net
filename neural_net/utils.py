"""
This module contains various utility functions.
"""

import numpy as np
from numpy.typing import NDArray


def softmax(x: NDArray) -> NDArray:
    """
    The softmax function.

    Args:
        x: The input vector or matrix
    Returns:
        The row wise probability vector of the given input.
    """
    exp = np.exp(x - np.max(x, axis=-1, keepdims=True))
    return exp / exp.sum(axis=-1, keepdims=True)
