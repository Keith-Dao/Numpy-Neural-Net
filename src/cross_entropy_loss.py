"""
This module contains the cross entropy loss class.
"""
from __future__ import annotations
from typing import Any, Callable, Hashable

import numpy as np
from numpy.typing import NDArray

from src import utils


class CrossEntropyLoss:
    """
    Cross entropy loss.
    """
    REDUCTIONS: dict[str, Callable[..., float]] = {
        "mean": np.mean,
        "sum": np.sum
    }

    def __init__(
        self,
        reduction: str = "mean"
    ) -> None:
        """
        Cross entropy loss init.

        Args:
            reduction: Name of the reduction method (mean, sum)
        """
        self._probabilities: NDArray | None = None
        self._target: NDArray | None = None
        self._reduction: str = ""
        self.reduction = reduction

    # region Properties
    @property
    def reduction(self) -> str:
        """
        The reduction method.
        """
        return self._reduction

    @reduction.setter
    def reduction(self, reduction: str) -> None:
        if (
            not isinstance(reduction, Hashable)
            or reduction not in CrossEntropyLoss.REDUCTIONS
        ):
            raise ValueError(
                "Invalid reduction method. Expected "
                f"{' or '.join(CrossEntropyLoss.REDUCTIONS.keys())},"
                f" got {reduction}."
            )
        self._reduction = reduction
    # endregion Properties

    # region Load
    @classmethod
    def from_dict(cls, attributes: dict[str, Any]) -> CrossEntropyLoss:
        """
        Create a cross-entropy loss instance from an attributes dictionary.

        Args:
            attributes: The attributes of the cross-entropy loss instance

        Returns:
            A cross-entropy loss instance with the provided attributes.
        """
        if cls.__name__ != attributes["class"]:
            raise ValueError(
                f"Invalid class value in attributes. Expected {cls.__name__},"
                f" got {attributes['class']}."
            )

        return cls(attributes["reduction"])
    # endregion Load

    # region Save
    def to_dict(self) -> dict[str, Any]:
        """
        Get all relevant attributes in a serialisable format.

        Attributes include:
            - reduction -- the reduction method used

        Returns:
            Attributes listed above as a dictionary.
        """
        return {
            "class": type(self).__name__,
            "reduction": self.reduction
        }
    # endregion Save

    # region Forward pass
    def forward(self, logits: NDArray, targets: NDArray | list[int]) -> float:
        """
        Calculate the cross entropy loss.

        Args:
            logits: The logits to calculate the cross entropy loss on
            targets: The one-hot encoded labels or the class labels

        Returns:
            The cross entropy loss.
        """
        if len(targets) < 1:
            raise ValueError(
                f"Length of targets must be >= 1, got {len(targets)}."
            )

        if len(logits) < 1:
            raise ValueError(
                f"Length of logits must be >= 1, got {len(logits)}."
            )

        num_classes = logits.shape[-1]
        if isinstance(targets, list):
            if not isinstance(targets[0], int):
                raise TypeError(
                    "Targets must either be a NumPy array or a list"
                    f" of ints, got a list of {type(targets[0]).__name__}."
                )
            try:
                targets = utils.one_hot_encode(targets, num_classes)
            except IndexError as ex:
                raise ValueError(
                    "Received a label index greater than the number"
                    " of classes."
                ) from ex

        if (
            logits.reshape(-1, num_classes).shape
            != targets.reshape(-1, num_classes).shape
        ):
            raise ValueError(
                f"The shape of logits ({logits.shape}) does not match the"
                f" shape of targets ({targets.shape}). ")
        self._target = targets
        self._probabilities = utils.softmax(logits)

        return CrossEntropyLoss.REDUCTIONS[self.reduction](
            -np.sum(targets * utils.log_softmax(logits), axis=-1),
            axis=None
        )
    # endregion Forward pass

    # region Backward pass
    def backward(self) -> NDArray:
        """
        Perform the backward pass using the previous forward inputs.

        Returns:
            The gradients with respect to the predictions.
        """
        if self._probabilities is None or self._target is None:
            raise RuntimeError("forward must be called before backward.")

        # Rescale the gradients
        batch_size = self._probabilities.shape[0]
        if self.reduction == "sum" or len(self._probabilities.shape) == 1:
            batch_size = 1

        return (self._probabilities - self._target) / batch_size

    # endregion Backward pass

    # region Built-ins
    def __call__(self, logits: NDArray, targets: NDArray | list[int]) -> float:
        """
        Calculate the cross entropy loss.

        Args:
            logits: The logits to calculate the cross entropy loss on
            targets: The one-hot encoded labels or the class labels

        Returns:
            The cross entropy loss.
        """
        return self.forward(logits, targets)

    def __eq__(self, other: object) -> bool:
        """
        Checks if another is equal to this.

        Args:
            other: Object to compare with

        Returns:
            True if all attributes are equal, otherwise False.
        """
        return (
            isinstance(other, type(self))
            and self.reduction == other.reduction
        )
    # endregion Built-ins
