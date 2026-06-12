# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.gui.plots.base_plot import BasePlot
from act.core.gui.plots.base_table import BaseTable
from act.tests.base_test_case import BaseTestCase


class GUITests(BaseTestCase):
    """Tests for dashboard GUI plots and visualizations"""

    def setUp(self):
        super().setUp()
        # GUI tests need the dashboard, so remove --no-dashboard from base args
        if "--no-dashboard" in self.test_args:
            self.test_args.remove("--no-dashboard")

    def test_sunburst_plot_consistency(self):
        """Ensure that the sunburst charts for each metric are consistent over each card"""
        self.test_args.extend(
            f"-m {self.boms_dir}/server/dellr740/top.yaml --life-cycle 1 year --duty-cycle 1.0 --op-power 0 W ".split()
        )

        act = self.run_act()
        self.assertIsNotNone(act.dashboard_asset)

        expected_total_carbon = act.results.total_carbon.total()
        expected_total_cost = act.cost_analyzer.get_total_cost()

        # ensure that the total carbon across all figures is consistent
        carbon_card = act.dashboard_asset.get_card(cid="carbon-card-id")
        source_plot = carbon_card.source_plot
        category_carbon_plot = carbon_card.category_carbon_plot
        subsystem_carbon_plot = carbon_card.subsystem_carbon_plot

        # the total sectors should be the same across all carbon plots
        self.assertEqual(source_plot.get_total_carbon_weight(), expected_total_carbon)
        self.assertEqual(
            category_carbon_plot.get_total_carbon_weight(), expected_total_carbon
        )
        self.assertEqual(
            subsystem_carbon_plot.get_total_carbon_weight(), expected_total_carbon
        )

        # ensure the analysis info total carbon matches
        info_card = act.dashboard_asset.get_card(cid="sim-info-card-id")
        info_table = info_card.sim_info_table
        self.assertEqual(
            info_table.act.results.total_carbon.total(), expected_total_carbon
        )

        # ensure the total cost across all figures is consistent
        cost_card = act.dashboard_asset.get_card(cid="cost-card-id")
        category_cost_plot = cost_card.category_cost_plot
        subsystem_cost_plot = cost_card.subsystem_cost_plot
        cost_type_cost_plot = cost_card.cost_type_plot

        # the total sectors should be the same across all cost plots
        self.assertEqual(category_cost_plot.get_total_cost(), expected_total_cost)
        self.assertEqual(subsystem_cost_plot.get_total_cost(), expected_total_cost)
        self.assertEqual(cost_type_cost_plot.get_total_cost(), expected_total_cost)

    def test_no_empty_tables_and_plots(self):
        """Test that for every plot in the dashboard that there are non-zero traces in the plot"""
        self.test_args.extend(
            f"-m {self.boms_dir}/server/dellr740/top.yaml --life-cycle 1 year --duty-cycle 1.0 --op-power 0 W ".split()
        )
        act = self.run_act()

        def assert_non_zero_traces(plot):
            self.assertGreater(len(plot.fig.data), 0)

        def assert_non_empty_table(table):
            self.assertGreater(len(table.header), 0)
            self.assertGreater(len(table.data), 0)
            self.assertIsNotNone(table.table)

        cards = act.dashboard_asset.cards
        checked_plots, checked_tables = 0, 0
        for card in cards:
            attributes = dir(card)
            for attribute in attributes:
                value = getattr(card, attribute)
                if isinstance(value, BasePlot):
                    assert_non_zero_traces(value)
                    checked_plots += 1
                if isinstance(value, BaseTable):
                    assert_non_empty_table(value)
                    checked_tables += 1

        self.assertGreater(checked_plots, 0)
        self.assertGreater(checked_tables, 0)
