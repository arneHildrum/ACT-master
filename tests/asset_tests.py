# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import copy
import os

import pint
from act.core.act_result import BOM_SHEET, CARBON_SHEET, SUMMARY_SHEET
from act.core.carbon import Carbon
from act.core.utils.units import kg
from act.tests.base_test_case import BaseTestCase
from openpyxl import load_workbook


class AssetTests(BaseTestCase):
    """Tests for ACT asset export and import functionality"""

    def setUp(self):
        super().setUp()

    def test_spreadsheet_template_export(self):
        """Check that template export for bill of materials works"""
        output_file = f"{self.out_dir}/test.xlsx"
        base_args = copy.deepcopy(self.test_args)
        self.test_args.extend(f"--export-template {output_file}".split())
        template_act = self.run_act()
        self.assertTrue(os.path.exists(output_file))

        # ensure that the template re-imports properly even though it's empty
        self.test_args = base_args
        self.test_args.extend(f"-m {output_file}".split())
        act = self.run_act()

    def test_spreadsheet_import(self):
        """Check that the template import with a populated bill of materials works as expected"""
        import_file = f"{self.boms_dir}/tests/test_sheet.xlsx"
        self.test_args.extend(f"-m {import_file}".split())

        act = self.run_act()

        # spot check the loaded bill of materials specification
        bom = act.bom
        expected_devices = [
            "dut",
            "dram",
            "ssd",
            "hdd",
            "cap0",
            "fasteners",
            "heatsink",
            "pcb",
            "battery",
        ]
        for dev in expected_devices:
            self.assertIn(dev, bom.devices)

    def test_act_result_and_assets(self):
        """Quality control the ACT result spreadsheet result"""
        expected_yaml_file = f"{self.out_dir}/test_export.yaml"
        expected_xlsx_file = f"{self.out_dir}/test_export.xlsx"
        self.test_args.extend(
            f"-m {self.boms_dir}/server/dellr740/top.yaml --export-file {expected_yaml_file}".split()
        )
        act = self.run_act()

        # check the data structure integrity
        results = act.results
        self.assertIsNotNone(results.carbon_by_device)
        self.assertIsNotNone(results.timestamp)
        self.assertIsNotNone(results.duty_cycle)
        self.assertIsNotNone(results.life_cycle)
        self.assertIsNotNone(results.total_carbon)

        # check unit'ing integrity
        for carbon in results.carbon_by_device.values():
            self.assertIsInstance(carbon, Carbon)
        for amt in results.carbon_by_category.values():
            self.assertTrue(amt.check(kg))
            self.assertIsInstance(amt, pint.Quantity)

        # check carbon emissions totals add up and are consistent
        total = results.total_carbon
        total_by_device = sum(results.carbon_by_device.values()).total()
        total_by_category = sum(results.carbon_by_category.values())
        self.assertEqual(total.total(), total_by_device)
        self.assertEqual(total.total(), total_by_category)

        # spot check the exported assets
        self.assertTrue(os.path.exists(expected_yaml_file))
        self.assertTrue(os.path.exists(expected_xlsx_file))

        # check that the spreadsheet contents are not empty
        workbook = load_workbook(expected_xlsx_file)
        self.assertIn(SUMMARY_SHEET, workbook)
        self.assertIn(CARBON_SHEET, workbook)
        self.assertIn(BOM_SHEET, workbook)

        def is_sheet_empty(sheet):
            """Check if a spreadsheet sheet is empty."""
            is_empty = [
                cell.value for cells in workbook[sheet].rows for cell in cells
            ] == [None]
            return is_empty

        # make sure that the sheets are not empty
        self.assertFalse(is_sheet_empty(SUMMARY_SHEET))
        self.assertFalse(is_sheet_empty(CARBON_SHEET))
        self.assertFalse(is_sheet_empty(BOM_SHEET))
