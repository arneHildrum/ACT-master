# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import copy
import logging

from act.core.common import ModelType
from act.core.gui.plots.delta_carbon_barchart import DeltaCarbonBarchart
from act.core.gui.plots.delta_carbon_table import DeltaCarbonTable
from act.core.gui.plots.delta_cost_barchart import DeltaCostBarchart
from act.core.gui.plots.delta_cost_table import DeltaCostTable
from act.tests.base_test_case import BaseTestCase


class DeltaPlotTest(BaseTestCase):
    """Tests for delta comparison plot generation"""

    @classmethod
    def setUpClass(cls):
        cls._base_sim = None
        cls._delta_sim = None

    def setUp(self):
        super().setUp()
        if DeltaPlotTest._base_sim is None:
            base_args = copy.deepcopy(self.test_args)
            self.test_args.extend(f"-m {self.boms_dir}/tests/test.yaml".split())
            DeltaPlotTest._base_sim = self.run_act(loglevel=logging.WARNING)

            self.test_args = base_args
            self.test_args.extend(f"-m {self.boms_dir}/tests/manual.yaml".split())
            DeltaPlotTest._delta_sim = self.run_act(loglevel=logging.WARNING)

        self.base_sim = DeltaPlotTest._base_sim
        self.delta_sim = DeltaPlotTest._delta_sim

    def test_barcharts_init_stores_sims(self):
        """Test that barchart objects store simulation references correctly."""
        carbon_chart = DeltaCarbonBarchart(self.base_sim, [self.delta_sim])
        cost_chart = DeltaCostBarchart(self.base_sim, [self.delta_sim])

        for chart in [carbon_chart, cost_chart]:
            self.assertEqual(chart.base_sim, self.base_sim)
            self.assertEqual(chart.delta_sims, [self.delta_sim])

    def test_all_plots_return_empty_for_none_sim(self):
        """Test that all plot types return empty results for None simulation."""
        carbon_chart = DeltaCarbonBarchart(self.base_sim, [self.delta_sim])
        cost_chart = DeltaCostBarchart(self.base_sim, [self.delta_sim])
        carbon_table = DeltaCarbonTable(self.base_sim, [self.delta_sim])
        cost_table = DeltaCostTable(self.base_sim, [self.delta_sim])

        self.assertEqual(carbon_chart.make_stacked_barchart_data(None), {})
        self.assertEqual(cost_chart.make_stacked_barchart_data(None), {})
        self.assertEqual(carbon_table.get_carbon_by_device(None), {})
        self.assertEqual(carbon_table.get_carbon_by_subsystem(None), {})
        self.assertEqual(cost_table.get_cost_by_device(None), {})
        self.assertEqual(cost_table.get_cost_by_subsystem(None), {})

    def test_all_plots_return_dict_for_valid_sim(self):
        """Test that all plot types return populated dicts for valid simulations."""
        carbon_chart = DeltaCarbonBarchart(self.base_sim, [self.delta_sim])
        cost_chart = DeltaCostBarchart(self.base_sim, [self.delta_sim])
        carbon_table = DeltaCarbonTable(self.base_sim, [self.delta_sim])
        cost_table = DeltaCostTable(self.base_sim, [self.delta_sim])

        self.assertIsInstance(
            carbon_chart.make_stacked_barchart_data(self.base_sim), dict
        )
        self.assertIsInstance(
            cost_chart.make_stacked_barchart_data(self.base_sim), dict
        )
        self.assertIsInstance(carbon_table.get_carbon_by_device(self.base_sim), dict)
        self.assertIsInstance(cost_table.get_cost_by_device(self.base_sim), dict)
        self.assertGreater(len(carbon_table.get_carbon_by_device(self.base_sim)), 0)
        self.assertGreater(len(cost_table.get_cost_by_device(self.base_sim)), 0)

    def test_barcharts_generate_stacked_bar_traces(self):
        """Test that barcharts generate valid stacked bar traces and annotations."""
        carbon_chart = DeltaCarbonBarchart(self.base_sim, [self.delta_sim])
        cost_chart = DeltaCostBarchart(self.base_sim, [self.delta_sim])

        for chart in [carbon_chart, cost_chart]:
            barchart_data = chart.make_stacked_barchart_data(self.base_sim)
            traces, annotations = chart.generate_stacked_bar_traces(
                barchart_data, "Baseline"
            )
            self.assertIsInstance(traces, dict)
            self.assertIsInstance(annotations, list)

    def test_barcharts_relocate_identical_values(self):
        """Test that barcharts properly relocate identical values between datasets."""
        carbon_chart = DeltaCarbonBarchart(self.base_sim, [self.delta_sim])
        cost_chart = DeltaCostBarchart(self.base_sim, [self.delta_sim])

        for chart in [carbon_chart, cost_chart]:
            data1 = chart.make_stacked_barchart_data(self.base_sim)
            data2 = chart.make_stacked_barchart_data(self.delta_sim)
            sorted1, sorted2 = chart.relocate_identical_values(data1, data2)
            self.assertIsInstance(sorted1, dict)
            self.assertIsInstance(sorted2, dict)

    def test_barcharts_get_html_returns_string(self):
        """Test that barcharts return valid HTML string output."""
        carbon_chart = DeltaCarbonBarchart(self.base_sim, [self.delta_sim])
        cost_chart = DeltaCostBarchart(self.base_sim, [self.delta_sim])

        for chart in [carbon_chart, cost_chart]:
            html = chart.get_html()
            self.assertIsInstance(html, str)
            self.assertIn("<div", html)

    def test_tables_init_stores_sims(self):
        """Test that table objects store simulation references correctly."""
        carbon_table = DeltaCarbonTable(self.base_sim, [self.delta_sim])
        cost_table = DeltaCostTable(self.base_sim, [self.delta_sim])

        for table in [carbon_table, cost_table]:
            self.assertEqual(table.base_sim, self.base_sim)
            self.assertEqual(table.delta_sims, [self.delta_sim])
            self.assertEqual(table.decimal_places, 2)

    def test_tables_get_data_by_subsystem_groups_by_model_type(self):
        """Test that tables group data by subsystem and model type correctly."""
        carbon_table = DeltaCarbonTable(self.base_sim, [self.delta_sim])
        cost_table = DeltaCostTable(self.base_sim, [self.delta_sim])

        carbon_result = carbon_table.get_carbon_by_subsystem(self.base_sim)
        cost_result = cost_table.get_cost_by_subsystem(self.base_sim)

        for result in [carbon_result, cost_result]:
            self.assertIsInstance(result, dict)
            for model_type in ModelType:
                self.assertIn(model_type, result)

    def test_tables_plot_populates_header_and_data(self):
        """Test that tables populate header and data fields correctly."""
        carbon_table = DeltaCarbonTable(self.base_sim, [self.delta_sim])
        cost_table = DeltaCostTable(self.base_sim, [self.delta_sim])

        self.assertIn("Device", carbon_table.header)
        self.assertIn("Baseline (kg)", carbon_table.header)
        self.assertGreater(len(carbon_table.data), 0)

        self.assertIn("Device", cost_table.header)
        self.assertIn("Baseline (USD)", cost_table.header)
        self.assertGreater(len(cost_table.data), 0)
