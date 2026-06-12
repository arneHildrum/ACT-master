# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from unittest.mock import MagicMock

from act.core.act_result import ACTResult
from act.core.bom import BOM
from act.core.carbon import Carbon, SourceType
from act.core.models.ci_model import CIModel, DEFAULT_BUILD_YEAR
from act.core.scaling.apply_ci_scaling import apply_ci_scaling
from act.core.scaling.scaling_config import ScalingConfig
from act.core.utils.units import g
from act.tests.base_test_case import BaseTestCase


class ApplyCIScalingTest(BaseTestCase):
    """Tests for carbon intensity scaling application"""

    def setUp(self):
        super().setUp()
        self.ci_model = CIModel()

    def _make_bom(self, devices_dict):
        """Helper to create a BOM from a devices dictionary."""
        return BOM(devices=devices_dict)

    def _make_results(self, carbon_dict):
        """Helper to create ACTResult from a carbon dictionary."""
        results = ACTResult()
        results.carbon_by_device = {
            k: Carbon(v, SourceType.FABRICATION) for k, v in carbon_dict.items()
        }
        return results

    def test_none_scaling_config_returns_early(self):
        """Test that None scaling_config leaves carbon values unchanged."""
        results = self._make_results({"cpu0.main": 100 * g})
        bom = self._make_bom(
            {"cpu0.main": {"model": "logic", "fab_ci": "taiwan", "built": 2020}}
        )
        original_carbon = results.carbon_by_device["cpu0.main"].total()
        apply_ci_scaling(results, bom, scaling_config=None)
        self.assertEqual(results.carbon_by_device["cpu0.main"].total(), original_carbon)

    def test_custom_ci_model_is_used(self):
        """Test that provided ci_model is used instead of creating a default."""
        results = self._make_results({"cpu0.main": 100 * g})
        bom = self._make_bom(
            {"cpu0.main": {"model": "logic", "fab_ci": "taiwan", "built": 2020}}
        )
        scaling_config = ScalingConfig(
            name="test", scaling_paths={"cpu": {"year": 2025}}
        )
        mock_ci_model = MagicMock()
        mock_ci_model.get_ci_scale_factor.return_value = 2.0
        apply_ci_scaling(
            results, bom, scaling_config=scaling_config, ci_model=mock_ci_model
        )
        mock_ci_model.get_ci_scale_factor.assert_called()
        self.assertAlmostEqual(results.carbon_by_device["cpu0.main"].total().m, 200.0)

    def test_location_only_scaling(self):
        """Test that location-only scaling uses new location with device's built year."""
        results = self._make_results({"cpu0.main": 100 * g})
        bom = self._make_bom(
            {"cpu0.main": {"model": "logic", "fab_ci": "taiwan", "built": 2020}}
        )
        scaling_config = ScalingConfig(
            name="test", scaling_paths={"cpu": {"location": "usa"}}
        )
        expected_factor = self.ci_model.get_ci_scale_factor(
            src_or_loc="taiwan", new_src_or_loc="usa", built=2020, new_year_built=None
        )
        apply_ci_scaling(
            results, bom, scaling_config=scaling_config, ci_model=self.ci_model
        )
        self.assertAlmostEqual(
            results.carbon_by_device["cpu0.main"].total().m, 100 * expected_factor
        )

    def test_location_and_year_scaling(self):
        """Test that combined location+year scaling uses both new location and new year."""
        results = self._make_results({"cpu0.main": 100 * g})
        bom = self._make_bom(
            {"cpu0.main": {"model": "logic", "fab_ci": "taiwan", "built": 2020}}
        )
        scaling_config = ScalingConfig(
            name="test", scaling_paths={"cpu": {"location": "usa", "year": 2025}}
        )
        expected_factor = self.ci_model.get_ci_scale_factor(
            src_or_loc="taiwan", new_src_or_loc="usa", built=2020, new_year_built=2025
        )
        apply_ci_scaling(
            results, bom, scaling_config=scaling_config, ci_model=self.ci_model
        )
        self.assertAlmostEqual(
            results.carbon_by_device["cpu0.main"].total().m, 100 * expected_factor
        )

    def test_device_not_matching_path_unchanged(self):
        """Test that devices not matching any scaling path remain unchanged."""
        results = self._make_results({"dram.main0": 100 * g})
        bom = self._make_bom(
            {"dram.main0": {"model": "dram", "fab_ci": "taiwan", "built": 2020}}
        )
        scaling_config = ScalingConfig(
            name="test", scaling_paths={"cpu": {"year": 2025}}
        )
        apply_ci_scaling(
            results, bom, scaling_config=scaling_config, ci_model=self.ci_model
        )
        self.assertAlmostEqual(results.carbon_by_device["dram.main0"].total().m, 100.0)

    def test_basic_ci_scaling(self):
        """Test year-based CI scaling applies correct scale factors per device path."""
        self.test_args.extend(f"-m {self.boms_dir}/server/dellr740/top.yaml".split())
        base_act = self.run_act()
        self.test_args.extend(
            f"--scaling-config {self.configs_dir}/ci_scaling/sample.yaml".split()
        )
        scaled_act = self.run_act()

        built = DEFAULT_BUILD_YEAR
        for dname, dev in base_act.bom.devices.items():
            base_carbon = base_act.results.carbon_by_device[dname]
            scaled_carbon = scaled_act.results.carbon_by_device[dname]

            if dname.startswith("cpu0.main"):
                expected_factor = self.ci_model.get_ci_scale_factor(
                    dev.fab_ci, built=built, new_year_built=2026
                )
                expected_carbon = base_carbon * expected_factor
            elif dname.startswith("ssd"):
                expected_factor = self.ci_model.get_ci_scale_factor(
                    dev.fab_ci, built=built, new_year_built=2024
                )
                expected_carbon = base_carbon * expected_factor
            elif dname.startswith("dram.main2"):
                expected_factor = self.ci_model.get_ci_scale_factor(
                    dev.fab_ci, built=built, new_year_built=2030
                )
                expected_carbon = base_carbon * expected_factor
            else:
                expected_carbon = base_carbon
            self.assertAlmostEqual(expected_carbon.total(), scaled_carbon.total())
