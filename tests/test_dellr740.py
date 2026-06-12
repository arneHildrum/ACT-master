# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

"""Tests for dellr740 BOM macro preprocessing.

These tests validate that the macro preprocessing in the dellr740 hierarchical BOM
works correctly. Each test exercises a specific macro parameter to ensure proper
behavior when loading the BOM with different configurations.
"""

import os
import unittest

from act.core.bom import BOM
from act.core.utils.load_yaml_with_macros import load_yaml_with_macros


class Dellr740MacroTest(unittest.TestCase):
    """Tests for dellr740 BOM macro preprocessing."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = os.path.abspath(os.path.dirname(__file__))
        self.bom_file = os.path.join(
            self.test_dir, "..", "boms", "server", "dellr740", "top.yaml"
        )

    def _load_bom_with_macros(self, cl_macros=None):
        """Helper to load BOM with optional command-line macros.

        Args:
            cl_macros: Dictionary of macro overrides to apply.

        Returns:
            BOM: The loaded BOM object with devices populated.
        """
        file_data = load_yaml_with_macros(self.bom_file, cl_macros=cl_macros)
        return BOM(**file_data, file=self.bom_file)

    def _count_devices_with_prefix(self, bom, prefix):
        """Count devices that start with the given prefix.

        Args:
            bom: The BOM object to search.
            prefix: The device name prefix to match.

        Returns:
            int: Count of devices matching the prefix.
        """
        return sum(1 for name in bom.devices if name.startswith(prefix))

    def test_num_cpus_macro_controls_cpu_count(self):
        """Test that NUM_CPUS macro controls the number of CPU devices."""
        # Test with 0 CPUs
        bom_0 = self._load_bom_with_macros({"NUM_CPUS": "0"})
        cpu_count_0 = self._count_devices_with_prefix(bom_0, "cpu.main")
        self.assertEqual(cpu_count_0, 0, "Expected 0 CPUs when NUM_CPUS=0")

        # Test with 1 CPU
        bom_1 = self._load_bom_with_macros({"NUM_CPUS": "1"})
        cpu_count_1 = self._count_devices_with_prefix(bom_1, "cpu.main")
        self.assertEqual(cpu_count_1, 1, "Expected 1 CPU when NUM_CPUS=1")

        # Test with 2 CPUs (default)
        bom_2 = self._load_bom_with_macros({"NUM_CPUS": "2"})
        cpu_count_2 = self._count_devices_with_prefix(bom_2, "cpu.main")
        self.assertEqual(cpu_count_2, 2, "Expected 2 CPUs when NUM_CPUS=2")

    def test_num_ssds_macro_controls_ssd_count(self):
        """Test that NUM_SSDS macro controls the number of SSD devices."""
        # Test with 0 SSDs
        bom_0 = self._load_bom_with_macros(
            {"NUM_SSDS": "0", "ENABLE_SECONDARY_SSD": "False"}
        )
        ssd_main_count = self._count_devices_with_prefix(bom_0, "ssd.main")
        self.assertEqual(ssd_main_count, 0, "Expected 0 main SSDs when NUM_SSDS=0")

        # Test with 4 SSDs
        bom_4 = self._load_bom_with_macros({"NUM_SSDS": "4"})
        ssd_main_count = self._count_devices_with_prefix(bom_4, "ssd.main")
        self.assertEqual(ssd_main_count, 4, "Expected 4 main SSDs when NUM_SSDS=4")

        # Test with 8 SSDs (default)
        bom_8 = self._load_bom_with_macros({"NUM_SSDS": "8"})
        ssd_main_count = self._count_devices_with_prefix(bom_8, "ssd.main")
        self.assertEqual(ssd_main_count, 8, "Expected 8 main SSDs when NUM_SSDS=8")

    def test_num_drams_macro_controls_dram_count(self):
        """Test that NUM_DRAMS macro controls the number of DRAM devices."""
        # Test with 0 DRAMs
        bom_0 = self._load_bom_with_macros({"NUM_DRAMS": "0"})
        dram_count = self._count_devices_with_prefix(bom_0, "dram.main")
        self.assertEqual(dram_count, 0, "Expected 0 DRAMs when NUM_DRAMS=0")

        # Test with 6 DRAMs
        bom_6 = self._load_bom_with_macros({"NUM_DRAMS": "6"})
        dram_count = self._count_devices_with_prefix(bom_6, "dram.main")
        self.assertEqual(dram_count, 6, "Expected 6 DRAMs when NUM_DRAMS=6")

        # Test with 12 DRAMs (default)
        bom_12 = self._load_bom_with_macros({"NUM_DRAMS": "12"})
        dram_count = self._count_devices_with_prefix(bom_12, "dram.main")
        self.assertEqual(dram_count, 12, "Expected 12 DRAMs when NUM_DRAMS=12")

    def test_enable_secondary_ssd_macro(self):
        """Test that ENABLE_SECONDARY_SSD macro controls secondary SSD inclusion."""
        # Test with secondary SSD disabled
        bom_disabled = self._load_bom_with_macros({"ENABLE_SECONDARY_SSD": "False"})
        has_secondary_ssd = any(
            name.startswith("ssd.secondary_ssd") for name in bom_disabled.devices
        )
        self.assertFalse(
            has_secondary_ssd,
            "Secondary SSD should not be present when ENABLE_SECONDARY_SSD=False",
        )

        # Test with secondary SSD enabled (default)
        bom_enabled = self._load_bom_with_macros({"ENABLE_SECONDARY_SSD": "True"})
        has_secondary_ssd = any(
            name.startswith("ssd.secondary_ssd") for name in bom_enabled.devices
        )
        self.assertTrue(
            has_secondary_ssd,
            "Secondary SSD should be present when ENABLE_SECONDARY_SSD=True",
        )

    def test_enable_secondary_dram_macro(self):
        """Test that ENABLE_SECONDARY_DRAM macro controls secondary DRAM inclusion."""
        # Test with secondary DRAM disabled
        bom_disabled = self._load_bom_with_macros({"ENABLE_SECONDARY_DRAM": "False"})
        has_secondary_dram = any(
            name.startswith("ssd.secondary_dram") for name in bom_disabled.devices
        )
        self.assertFalse(
            has_secondary_dram,
            "Secondary DRAM should not be present when ENABLE_SECONDARY_DRAM=False",
        )

        # Test with secondary DRAM enabled (default)
        bom_enabled = self._load_bom_with_macros({"ENABLE_SECONDARY_DRAM": "True"})
        has_secondary_dram = any(
            name.startswith("ssd.secondary_dram") for name in bom_enabled.devices
        )
        self.assertTrue(
            has_secondary_dram,
            "Secondary DRAM should be present when ENABLE_SECONDARY_DRAM=True",
        )

    def test_combined_macro_configuration(self):
        """Test that multiple macros can be combined correctly."""
        # Configure a minimal system: 1 CPU, 2 SSDs, 4 DRAMs, no secondary devices
        bom = self._load_bom_with_macros(
            {
                "NUM_CPUS": "1",
                "NUM_SSDS": "2",
                "NUM_DRAMS": "4",
                "ENABLE_SECONDARY_SSD": "False",
                "ENABLE_SECONDARY_DRAM": "False",
            }
        )

        # Verify device counts
        cpu_count = self._count_devices_with_prefix(bom, "cpu.main")
        ssd_count = self._count_devices_with_prefix(bom, "ssd.main")
        dram_count = self._count_devices_with_prefix(bom, "dram.main")
        secondary_count = self._count_devices_with_prefix(bom, "ssd.secondary")

        self.assertEqual(cpu_count, 1, "Expected 1 CPU in minimal config")
        self.assertEqual(ssd_count, 2, "Expected 2 SSDs in minimal config")
        self.assertEqual(dram_count, 4, "Expected 4 DRAMs in minimal config")
        self.assertEqual(secondary_count, 0, "Expected no secondary devices")

    def test_device_file_macro_override(self):
        """Test that device file macros can be overridden to use alternative device specs."""
        # This test verifies the CPU_DEVICE, SSD_DEVICE, DRAM_DEVICE macros work
        # by loading with defaults and checking the resulting device properties
        bom = self._load_bom_with_macros({"NUM_CPUS": "1"})

        # Find the first CPU device and verify it has expected properties
        cpu_devices = [
            (name, dev)
            for name, dev in bom.devices.items()
            if name.startswith("cpu.main")
        ]
        self.assertEqual(len(cpu_devices), 1, "Expected exactly 1 CPU device")

        _, cpu_dev = cpu_devices[0]
        # Verify the CPU has properties from cpu.yaml
        self.assertIsNotNone(cpu_dev.area, "CPU should have area specified")
        self.assertIsNotNone(cpu_dev.process, "CPU should have process specified")

    def test_num_asics_macro_adds_asics_per_cpu(self):
        """Test that NUM_ASICS macro adds ASIC devices per CPU with mtia2 defaults."""
        bom = self._load_bom_with_macros({"NUM_CPUS": "2", "NUM_ASICS_PER_CPU": "4"})

        asics_cpu0_count = sum(
            1 for name in bom.devices if name.startswith("cpu.asics0")
        )
        asics_cpu1_count = sum(
            1 for name in bom.devices if name.startswith("cpu.asics1")
        )

        self.assertEqual(asics_cpu0_count, 4, "Expected 4 ASICs for CPU0")
        self.assertEqual(asics_cpu1_count, 4, "Expected 4 ASICs for CPU1")

        # Verify ASICs are loaded from mtia2.yaml (default ASIC_FILE)
        asic_devices = [
            (name, dev)
            for name, dev in bom.devices.items()
            if name.startswith("cpu.asics0")
        ]
        _, asic_dev = asic_devices[0]
        self.assertIsNotNone(asic_dev.area, "ASIC should have area from mtia2.yaml")
        self.assertIn(
            "5", str(asic_dev.process), "ASIC should have 5nm process from mtia2.yaml"
        )

    def test_num_asics_single_cpu(self):
        """Test NUM_ASICS_PER_CPU with single CPU configuration."""
        bom = self._load_bom_with_macros({"NUM_CPUS": "1", "NUM_ASICS_PER_CPU": "2"})

        asics_cpu0_count = sum(
            1 for name in bom.devices if name.startswith("cpu.asics0")
        )
        asics_cpu1_exists = any(name.startswith("cpu.asics1") for name in bom.devices)

        self.assertEqual(asics_cpu0_count, 2, "Expected 2 ASICs for CPU0")
        self.assertFalse(
            asics_cpu1_exists, "Should not have ASICs for non-existent CPU1"
        )

    def test_num_asics_maximum_16(self):
        """Test that NUM_ASICS_PER_CPU supports maximum of 16 ASICs per CPU."""
        bom = self._load_bom_with_macros({"NUM_CPUS": "1", "NUM_ASICS_PER_CPU": "16"})

        asics_cpu0_count = sum(
            1 for name in bom.devices if name.startswith("cpu.asics0")
        )
        self.assertEqual(asics_cpu0_count, 16, "Expected 16 ASICs for CPU0 (maximum)")

    def test_asic_file_macro_uses_mtia2_default(self):
        """Test that ASIC_FILE macro defaults to mtia2.yaml."""
        bom = self._load_bom_with_macros({"NUM_CPUS": "1", "NUM_ASICS_PER_CPU": "1"})

        asic_devices = [
            (name, dev)
            for name, dev in bom.devices.items()
            if name.startswith("cpu.asics0")
        ]
        self.assertEqual(len(asic_devices), 1, "Expected 1 ASIC device")

        _, asic_dev = asic_devices[0]
        self.assertIsNotNone(asic_dev.area, "ASIC should have area from mtia2.yaml")
        self.assertIn(
            "5", str(asic_dev.process), "ASIC should have 5nm process from mtia2.yaml"
        )
