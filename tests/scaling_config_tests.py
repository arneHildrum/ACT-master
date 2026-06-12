# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.processes import DRAMProcess, HDDProcess, LogicProcess, SSDProcess
from act.core.scaling.scaling_config import ScalingConfig, ScalingEntry
from act.tests.base_test_case import BaseTestCase
from parameterized import parameterized


class ScalingConfigTest(BaseTestCase):
    """Tests for scaling configuration loading and resolution"""

    @parameterized.expand(
        [
            ("logic", "14nm", LogicProcess.N14),
            ("dram", "lpddr4", DRAMProcess.LPDDR4),
            ("ssd", "nand_20nm", SSDProcess.NAND_20NM),
            ("hdd", "BarraCuda", HDDProcess.BARRACUDA),
        ]
    )
    def test_entry_process_resolution(self, name, process_str, expected):
        """Verify ScalingEntry resolves process strings to correct enum types."""
        entry = ScalingEntry(process=process_str)
        self.assertEqual(entry.process, expected)

    def test_entry_process_none_and_other_fields(self):
        """Verify ScalingEntry defaults process to None and stores year/location."""
        entry = ScalingEntry(year=2025, location="taiwan")
        self.assertIsNone(entry.process)
        self.assertEqual(entry.year, 2025)
        self.assertEqual(entry.location, "taiwan")

    def test_compatible_with_conversion(self):
        """Verify compatible_with is converted to list if not already."""
        config_list = ScalingConfig(name="test", compatible_with=["a", "b"])
        self.assertEqual(config_list.compatible_with, ["a", "b"])

        config_single = ScalingConfig(name="test", compatible_with="single")
        self.assertEqual(config_single.compatible_with, ["single"])

    def test_scaling_paths_loaded(self):
        """Verify scaling_paths dict entries are converted to ScalingEntry objects."""
        config = ScalingConfig(
            name="test",
            scaling_paths={"path1": {"process": "14nm", "year": 2025}},
        )
        self.assertIn("path1", config.scaling_paths)
        self.assertIsInstance(config.scaling_paths["path1"], ScalingEntry)
        self.assertEqual(config.scaling_paths["path1"].process, LogicProcess.N14)
        self.assertEqual(config.scaling_paths["path1"].year, 2025)
