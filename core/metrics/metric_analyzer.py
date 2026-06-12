# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core import metrics
from act.core.metrics.base_metric import BaseMetric
from act.core.utils.import_utils import all_subclasses, import_submodules


class MetricAnalyzer:
    """Analyzer for calculating all registered optimization metrics.

    This class auto-discovers all BaseMetric subclasses and calculates
    their values for a given ACT model.

    Attributes:
        metrics (list): List of discovered metric classes.
        act_model (ACTModel): The ACT model to analyze.
    """

    def __init__(self, act_model):
        """Initialize the Metric Analyzer.

        Args:
            act_model (ACTModel): The ACT model containing analysis results.
        """
        import_submodules(metrics)
        self.metrics = all_subclasses(BaseMetric)
        self.act_model = act_model

    def get_results(self):
        """Calculate all metrics and return the results.

        Returns:
            dict[str, pint.Quantity]: Dictionary mapping metric names to calculated values.
        """

        metric_results = dict()
        for Metric in self.metrics:
            m = Metric(act_model=self.act_model)
            metric_results[m.NAME] = m.calculate()
        return metric_results
