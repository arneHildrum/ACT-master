# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from abc import abstractmethod


class BaseMetric:
    """Base class for carbon optimization metrics.

    This class provides a foundation for implementing various optimization
    metrics that can be calculated from ACT analysis results.

    Attributes:
        NAME (str): The name of the metric.
        act_model (ACTModel): The ACT model containing analysis results.
    """

    NAME = "Base Metric"

    def __init__(self, act_model):
        """Initialize the base metric.

        Args:
            act_model (ACTModel): An ACTModel with carbon analysis results calculated.
        """
        self.act_model = act_model

    @abstractmethod
    def calculate(self):
        """Calculate the metric based on the provided ACT model.

        Returns:
            pint.Quantity: The calculated value for this optimization metric.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        raise NotImplementedError(
            "Metric calculation not implemented. Subclasses must implement metric calculation based on act model results."
        )
