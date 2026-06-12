# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import logging
import pathlib as pl
import unittest

from act.core.gui.cards.delta_cost_card import DeltaCostCard
from act.core.gui.cards.delta_overview_card import DeltaOverviewCard
from act.core.gui.cards.sim_info_card import SimInfoCard
from act.core.gui.delta_dashboard import DeltaDashboard
from act.tests.base_test_case import BaseTestCase


class DeltaTests(BaseTestCase):
    """Unit tests for ACT delta dashboard functionality"""

    def setUp(self):
        super().setUp()
        # Set up test-specific configurations
        self.test_bom_file = f"{self.boms_dir}/tests/test.yaml"
        self.simple_bom_file = f"{self.boms_dir}/tests/manual.yaml"

    def _create_test_simulation(self, bom_file, out_dir_suffix=""):
        """
        Helper method to create an ACT simulation for testing.

        Args:
            bom_file (str): Path to the BOM file to use
            out_dir_suffix (str): Suffix to add to output directory name

        Returns:
            ACT simulation object
        """
        test_args = [
            "./act",
            "--test",
            f"-m={bom_file}",
        ]

        # Create and run simulation
        self.test_args = test_args
        act_sim = self.run_act(loglevel=logging.WARNING)
        return act_sim

    def test_delta_dashboard_single_experiment(self):
        """Test delta dashboard generation with single experiment"""

        # Create baseline simulation
        base_sim = self._create_test_simulation(
            self.test_bom_file, out_dir_suffix="/base_single"
        )

        # Create experiment simulation (using different BOM for variation)
        exp_sim = self._create_test_simulation(
            self.simple_bom_file, out_dir_suffix="/exp_single"
        )

        # Create delta dashboard
        dashboard = DeltaDashboard(
            base_sim=base_sim,
            delta_sims=[exp_sim],
            out_dir=f"{self.out_dir}/delta_single",
            test=True,  # Skip packed HTML generation for tests
            dashboard_title="Single Experiment Test",
        )

        # Generate dashboard
        dashboard.generate_dashboard()

        # Verify dashboard files were created
        self.assertIsFile(f"{self.out_dir}/delta_single/index.html")

        # Verify dashboard has expected cards
        self.assertEqual(len(dashboard.cards), 3)  # Overview, Cost, SimInfo

        # Verify card types
        overview_card = dashboard.get_card_by_type(DeltaOverviewCard)
        cost_card = dashboard.get_card_by_type(DeltaCostCard)
        sim_info_card = dashboard.get_card_by_type(SimInfoCard)

        self.assertIsNotNone(overview_card)
        self.assertIsNotNone(cost_card)
        self.assertIsNotNone(sim_info_card)

        # Verify card titles
        self.assertEqual(overview_card.title, "Emissions")
        self.assertEqual(cost_card.title, "Cost")
        self.assertEqual(sim_info_card.title, "Simulation Info")

    def test_delta_dashboard_multiple_experiments(self):
        """Test delta dashboard generation with multiple experiments"""

        # Create baseline simulation
        base_sim = self._create_test_simulation(
            self.test_bom_file, out_dir_suffix="/base_multi"
        )

        # Create multiple experiment simulations
        exp_sims = []
        for i in range(3):
            exp_sim = self._create_test_simulation(
                self.simple_bom_file if i % 2 == 0 else self.test_bom_file,
                out_dir_suffix=f"/exp_multi_{i}",
            )
            exp_sims.append(exp_sim)

        # Create delta dashboard
        dashboard = DeltaDashboard(
            base_sim=base_sim,
            delta_sims=exp_sims,
            out_dir=f"{self.out_dir}/delta_multi",
            test=True,
            dashboard_title="Multiple Experiments Test",
        )

        # Generate dashboard
        dashboard.generate_dashboard()

        # Verify dashboard files were created
        self.assertIsFile(f"{self.out_dir}/delta_multi/index.html")

        # Verify dashboard has expected cards
        self.assertEqual(len(dashboard.cards), 3)

        # Verify that cards handle multiple experiments
        overview_card = dashboard.get_card_by_type(DeltaOverviewCard)
        cost_card = dashboard.get_card_by_type(DeltaCostCard)

        self.assertIsNotNone(overview_card)
        self.assertIsNotNone(cost_card)

        # Verify that the cards were initialized with correct number of experiments
        self.assertEqual(len(overview_card.delta_sims), 3)
        self.assertEqual(len(cost_card.delta_sims), 3)

    def test_delta_dashboard_identical_simulations(self):
        """Test delta dashboard with identical baseline and experiment simulations"""

        # Create baseline simulation
        base_sim = self._create_test_simulation(
            self.test_bom_file, out_dir_suffix="/base_identical"
        )

        # Create identical experiment simulation
        exp_sim = self._create_test_simulation(
            self.test_bom_file, out_dir_suffix="/exp_identical"
        )

        # Create delta dashboard
        dashboard = DeltaDashboard(
            base_sim=base_sim,
            delta_sims=[exp_sim],
            out_dir=f"{self.out_dir}/delta_identical",
            test=True,
            dashboard_title="Identical Simulations Test",
        )

        # Generate dashboard
        dashboard.generate_dashboard()

        # Verify dashboard was created successfully
        self.assertIsFile(f"{self.out_dir}/delta_identical/index.html")

        # Verify dashboard structure
        self.assertEqual(len(dashboard.cards), 3)

    def test_delta_dashboard_empty_experiments(self):
        """Test delta dashboard with empty experiments list"""

        # Create baseline simulation
        base_sim = self._create_test_simulation(
            self.test_bom_file, out_dir_suffix="/base_empty"
        )

        # Create delta dashboard with empty experiments
        dashboard = DeltaDashboard(
            base_sim=base_sim,
            delta_sims=[],
            out_dir=f"{self.out_dir}/delta_empty",
            test=True,
            dashboard_title="Empty Experiments Test",
        )

        # Generate dashboard
        dashboard.generate_dashboard()

        # Verify dashboard was created successfully
        self.assertIsFile(f"{self.out_dir}/delta_empty/index.html")

        # Verify dashboard structure
        self.assertEqual(len(dashboard.cards), 3)

    def test_delta_dashboard_custom_configuration(self):
        """Test delta dashboard with custom configuration options"""

        # Create simulations
        base_sim = self._create_test_simulation(
            self.test_bom_file, out_dir_suffix="/base_custom"
        )
        exp_sim = self._create_test_simulation(
            self.simple_bom_file, out_dir_suffix="/exp_custom"
        )

        # Create dashboard with custom settings
        custom_title = "Custom ACT Delta Analysis"
        custom_html_file = "custom_delta.html"

        dashboard = DeltaDashboard(
            base_sim=base_sim,
            delta_sims=[exp_sim],
            out_dir=f"{self.out_dir}/delta_custom",
            html_file=custom_html_file,
            test=True,
            dashboard_title=custom_title,
        )

        # Verify custom settings
        self.assertEqual(dashboard.dashboard_title, custom_title)
        self.assertEqual(dashboard.html_file, custom_html_file)

        # Generate dashboard
        dashboard.generate_dashboard()

        # Verify files were created
        self.assertIsFile(f"{self.out_dir}/delta_custom/index.html")

    def assertIsFile(self, path):
        """Helper method to assert that a file exists"""
        if not pl.Path(path).resolve().is_file():
            raise AssertionError(f"File does not exist: {path}")

    def assertIsNotFile(self, path):
        """Helper method to assert that a file does not exist"""
        if pl.Path(path).resolve().is_file():
            raise AssertionError(f"File exists: {path}")


if __name__ == "__main__":
    unittest.main()
