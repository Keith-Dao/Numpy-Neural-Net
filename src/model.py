"""
This module contains the model class.
"""
from __future__ import annotations
import json
import pathlib
import pickle
from types import ModuleType
from typing import Any

import matplotlib.pyplot as plt
from numpy.typing import NDArray
from tabulate import tabulate
from tqdm import tqdm

from src import (
    cross_entropy_loss,
    image_loader,
    linear,
    metrics,
    utils
)


# pylint: disable=too-many-instance-attributes
class Model:
    """
    The neural network model.
    """
    SAVE_METHODS: dict[str, tuple[ModuleType, bool]] = {
        # file extension : (module, is binary file)
        ".pkl": (pickle, True),
        ".json": (json, False)
    }

    def __init__(
        self,
        layers: list[linear.Linear],
        loss: cross_entropy_loss.CrossEntropyLoss,
        **kwargs
    ) -> None:
        """
        Model init.

        Args:
            layers: List of sequential layers in the neural network
            loss: The loss used to update this model

        Keyword args:
            total_epochs: The total epochs of the model
            train_metrics: The training metrics to store or
                the training history metrics
            validation_metrics: The validation metrics to store or
                the validation history metrics
        """
        self._eval = False
        self.layers = layers
        self.loss = loss
        self.total_epochs = kwargs.get("total_epochs", 0)

        # Metrics
        self.train_metrics = kwargs.get("train_metrics") or []
        self.validation_metrics = kwargs.get("validation_metrics") or []

    # region Properties
    # region Evaluation mode
    @property
    def eval(self) -> bool:
        """
        Model's evaluation mode.
        """
        return self._eval

    @eval.setter
    def eval(self, eval_: bool) -> None:
        utils.check_type(eval_, bool, "eval")
        if self._eval == eval_:
            return

        for layer in self.layers:
            layer.eval = eval_
        self._eval = eval_
    # endregion Evaluation mode

    # region Layers
    @property
    def layers(self) -> list[linear.Linear]:
        """
        Model's layers.
        """
        return self._layers

    @layers.setter
    def layers(self, layers: list[linear.Linear]) -> None:
        utils.check_type(layers, list, "layers")
        if not layers:
            raise ValueError("layers cannot be an empty list.")

        if any(not isinstance(layer, linear.Linear) for layer in layers):
            raise TypeError(
                "Invalid type for layers. Expected all list elements to be"
                " Linear."
            )

        self._layers = layers
    # endregion Layers

    # region Loss
    @property
    def loss(self) -> cross_entropy_loss.CrossEntropyLoss:
        """
        The model's loss.
        """
        return self._loss

    @loss.setter
    def loss(self, loss: cross_entropy_loss.CrossEntropyLoss) -> None:
        utils.check_type(loss, cross_entropy_loss.CrossEntropyLoss, "loss")

        self._loss = loss
    # endregion Loss

    # region Total epochs
    @property
    def total_epochs(self) -> int:
        """
        Total epochs the model has trained for.
        """
        return self._total_epochs

    @total_epochs.setter
    def total_epochs(self, epochs: int) -> None:
        utils.check_type(epochs, int, "total_epochs")
        if epochs < 0:
            raise ValueError("total_epochs must be > 0.")

        self._total_epochs = epochs
    # endregion Total epochs

    # region Train metrics
    @property
    def train_metrics(self) -> dict[str, list[float]]:
        """
        The metrics to store when training the model.
        """
        return self._train_metrics

    @train_metrics.setter
    def train_metrics(self, train_metrics) -> None:
        utils.check_type(train_metrics, (dict, list), "train_metrics")

        if isinstance(train_metrics, dict):
            self._train_metrics = train_metrics
        else:
            self._train_metrics = {
                metric: []
                for metric in train_metrics
            }

        if any(
            metric != "loss" and not hasattr(metrics, metric)
            for metric in self.train_metrics
        ):
            raise ValueError(
                "An invalid metric was provided to train_metrics."
            )
        if any(
            not isinstance(value, list)
            for value in self.train_metrics.values()
        ):
            raise ValueError(
                "All train metric histories must be a list."
            )
    # endregion Train metrics

    # region Train metrics
    @property
    def validation_metrics(self) -> dict[str, list[float]]:
        """
        The metrics to store when validating the model.
        """
        return self._validation_metrics

    @validation_metrics.setter
    def validation_metrics(self, validation_metrics) -> None:
        utils.check_type(
            validation_metrics,
            (dict, list),
            "validation_metrics"
        )

        if isinstance(validation_metrics, dict):
            self._validation_metrics = validation_metrics
        else:
            self._validation_metrics = {
                metric: []
                for metric in validation_metrics
            }

        if any(
            metric != "loss" and not hasattr(metrics, metric)
            for metric in self.validation_metrics
        ):
            raise ValueError(
                "An invalid metric was provided to validation_metrics."
            )
        if any(
            not isinstance(value, list)
            for value in self.validation_metrics.values()
        ):
            raise ValueError(
                "All validation metric histories must be a list."
            )
    # endregion Train metrics
    # endregion Properties

    # region Load
    @classmethod
    def from_dict(cls, attributes: dict[str, Any]) -> Model:
        """
        Create a model instance from an attributes dictionary.

        Args:
            attributes: The attributes of the model instance

        Returns:
            A model instance with the provided attributes.
        """
        if cls.__name__ != attributes["class"]:
            raise ValueError(
                f"Invalid class value in attributes. Expected {cls.__name__},"
                f" got {attributes['class']}."
            )

        layers = [
            getattr(linear, layer_attributes["class"])
            .from_dict(layer_attributes)
            for layer_attributes in attributes["layers"]
        ]
        loss = getattr(cross_entropy_loss, attributes["loss"]["class"]) \
            .from_dict(attributes["loss"])
        return cls(layers, loss, **{
            key: val
            for key, val in attributes.items()
            if key not in {"layers", "loss"}
        })

    @classmethod
    def load(
        cls,
        file_path: str | pathlib.Path
    ) -> Model:
        """
        Load a model from the given file.

        NOTE: The format of the file would be inferred by the provided
        file extension i.e. .pkl would be a pickle file while .json
        would be a JSON file.

        Args:
            file_path: Path of the file to load from

        Returns:
            A new model object with the attributes specified in the file.
        """
        utils.check_type(file_path, (str, pathlib.Path), "file_path")
        if isinstance(file_path, str):
            file_path = pathlib.Path(file_path)

        if file_path.suffix not in Model.SAVE_METHODS:
            raise ValueError(
                f"File format {file_path.suffix} not supported."
                f" Select from {' or '.join(Model.SAVE_METHODS.keys())}."
            )

        module, is_binary = Model.SAVE_METHODS[file_path.suffix]
        write_mode = "rb" if is_binary else "r"
        encoding = None if is_binary else "UTF-8"
        with open(file_path, write_mode, encoding=encoding) as load_file:
            attributes = module.load(load_file)
        return cls.from_dict(attributes)
    # endregion Load

    # region Save
    def to_dict(self) -> dict:
        """
        Get all the relevant attributes in a serialisable format.

        Attributes:
            - layers -- list of the serialised layers in sequential order
            - loss -- the loss function for the model
            - epochs -- the total number of epochs the model has trained for
            - train_metrics -- the history of the training metrics for the
                model
            - validation_metrics -- the history of the validation metrics for
                the model

        Returns:
            Attributes listed above as a dictionary.
        """
        return {
            "class": type(self).__name__,
            "layers": [
                layer.to_dict()
                for layer in self.layers
            ],
            "loss": self.loss.to_dict(),
            "epochs": self.total_epochs,
            "train_metrics": self.train_metrics,
            "validation_metrics": self.validation_metrics
        }

    def save(self, save_path: str | pathlib.Path):
        """
        Save the model attributes to the provided save path.

        NOTE: The format of the file would be inferred by the provided
        file extension i.e. .pkl would be a pickle file while .json
        would be a JSON file.

        Args:
            save_path: Path to save the model attributes.
        """
        utils.check_type(save_path, (str, pathlib.Path), "save_path")
        if isinstance(save_path, str):
            save_path = pathlib.Path(save_path)

        if save_path.suffix not in Model.SAVE_METHODS:
            raise ValueError(
                f"File format {save_path.suffix} not supported."
                f"Select from {' or '.join(Model.SAVE_METHODS.keys())}."
            )

        module, is_binary = Model.SAVE_METHODS[save_path.suffix]
        write_mode = "wb" if is_binary else "w"
        encoding = None if is_binary else "UTF-8"
        with open(save_path, write_mode, encoding=encoding) as save_file:
            module.dump(self.to_dict(), save_file)
    # endregion Save

    # region Forward pass
    def forward(self, input_: NDArray) -> NDArray:
        """
        Perform the forward pass.

        Args:
            input_: The input values to the model

        Returns:
            The output values of the model.
        """
        out = input_
        for layer in self.layers:
            out = layer(out)
        return out

    def get_loss_with_confusion_matrix(
        self,
        input_: NDArray,
        confusion_matrix: NDArray,
        labels: list[int]
    ) -> float:
        """
        Perform the forward pass and store the predictions to the
        confusion matrix.

        Args:
            input_: The input values to the model
            confusion_matrix: The confusion matrix where the rows
                represent the predicted class and the columns
                represent the actual class
            labels: The ground truth labels for the inputs

        Returns:
            The loss of the forward pass.
        """
        logits = self(input_)
        metrics.add_to_confusion_matrix(
            confusion_matrix,
            utils.logits_to_prediction(logits),
            labels
        )
        return self.loss(logits, labels)
    # endregion Forward pass

    # region Train
    def _train_step(
        self,
        data: NDArray,
        labels: list[int],
        learning_rate: float,
        confusion_matrix: NDArray
    ) -> float:
        """
        Perform a training step for one minibatch.

        Args:
            data: The minibatch data
            labels: The ground truth labels for the inputs
            learning_rate: The learning rate
            confusion_matrix: The confusion matrix where the rows
                represent the predicted class and the columns
                represent the actual class

        Returns:
            The output loss.
        """
        loss = self.get_loss_with_confusion_matrix(
            data,
            confusion_matrix,
            labels
        )
        grad = self.loss.backward()
        for layer in reversed(self.layers):
            grad = layer.update(grad, learning_rate)
        return loss

    def train(
        self,
        data_loader: image_loader.ImageLoader,
        learning_rate: float,
        batch_size: int,
        epochs: int
    ) -> None:
        """
        Train the model for the given number of epochs.

        Args:
            data_loader: The data loader
            learning_rate: The learning rate
            batch_size: The batch size
            epochs: The number of epochs to train for
        """
        num_classes = self.layers[-1].out_channels
        for epoch in range(1, epochs + 1):
            print(f"Epoch {epoch}:")
            # Training
            training_data = data_loader("train", batch_size=batch_size)
            confusion_matrix = metrics.get_new_confusion_matrix(num_classes)
            total_training_loss = sum(
                self._train_step(
                    data,
                    labels,
                    learning_rate,
                    confusion_matrix
                )
                for data, labels in tqdm(training_data, desc="Training")
            )
            training_loss = total_training_loss / len(training_data)
            self.store_metrics("train", confusion_matrix, training_loss)
            self.print_metrics("train", data_loader.classes)

            # Validation
            validation_data = data_loader("test", batch_size=batch_size)
            if len(validation_data) == 0:
                continue

            self.eval = True
            confusion_matrix = metrics.get_new_confusion_matrix(num_classes)
            total_validation_loss = sum(
                self.get_loss_with_confusion_matrix(
                    data,
                    confusion_matrix,
                    labels
                )
                for data, labels in tqdm(validation_data, desc="Validation")
            )
            validation_loss = total_validation_loss / len(validation_data)
            self.store_metrics("validation", confusion_matrix, validation_loss)
            self.print_metrics("validation", data_loader.classes)
            self.eval = False
        self.total_epochs += epochs
    # endregion Train

    # region Metrics
    def store_metrics(
        self,
        metric_type: str,
        confusion_matrix: NDArray,
        loss: float
    ) -> None:  # pragma: no cover
        """
        Store the metrics.

        Args:
            metric_type: The metric type to save the data to
            confusion_matrix: The confusion matrix to use for the metrics
            loss: The loss
        """
        metrics_ = getattr(self, f"{metric_type}_metrics")
        for metric in metrics_.keys():
            metrics_[metric].append(
                loss
                if metric == "loss"
                else getattr(metrics, metric)(confusion_matrix)
            )

    def print_metrics(
        self,
        metric_type: str,
        classes: list[str]
    ) -> None:  # pragma: no cover
        """
        Print the tracked metrics.

        Args:
            metric_type: The metric type to display
            classes: The classes in the same order as the confusion matrix
        """
        metrics_ = getattr(self, f"{metric_type}_metrics")
        headers = ["Class"]
        tabulated_data = [classes]
        for metric in metrics_:
            if metric in metrics.SINGLE_VALUE_METRICS:
                print(f"{metric.capitalize()}: {metrics_[metric][-1]:.4f}")
            else:
                headers.append(metric.capitalize())
                tabulated_data.append(metrics_[metric][-1])

        if len(headers) > 1:
            tabulated_data = list(zip(*tabulated_data))
            print(tabulate(tabulated_data, headers=headers, floatfmt=".4f"))
    # endregion Metrics

    # region Visualisation
    def generate_history_graph(self, metric: str) -> None:  # pragma: no cover
        """
        Generates the model's history data.

        Args:
            metric: The metric to generate a history graph for
        """
        if (
            metric not in self.train_metrics
            and metric not in self.validation_metrics
        ):
            raise ValueError("Invalid metric.")

        fig = plt.figure()
        axis = fig.add_subplot(1, 1, 1)

        if metric in self.train_metrics:
            axis.plot(
                self.train_metrics[metric],
                "-c",
                label="Training Loss"
            )
        if metric in self.validation_metrics:
            axis.plot(
                self.validation_metrics[metric],
                "-r",
                label="Validation Loss"
            )

        axis.legend(loc="upper right")
        axis.set_xlabel("Epoch")

    def display_history_graph(self, metric: str) -> None:  # pragma: no cover
        """
        Generates and displays the model's history graph.

        Args:
            metric: The metric to generate a history graph for
        """
        self.generate_history_graph(metric)
        plt.show()
    # endregion Visualisation

    # region Built-ins

    def __call__(self, input_: NDArray) -> NDArray:
        """
        Perform the forward pass.

        Args:
            input_: The input values to the model

        Returns:
            The output values of the model.
        """
        return self.forward(input_)

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
            and self.layers == other.layers
            and self.loss == other.loss
        )
    # endregion Built-ins
