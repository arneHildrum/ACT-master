# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import copy
import glob

from act.core.utils.logger import log
from act.tests.base_test_case import BaseTestCase
from parameterized import parameterized

NUM_YAML_TEST_SHARDS = 8


class BOMCoverageTests(BaseTestCase):
    """Detects all bill of materials yaml files and runs them through ACT to ensure stability"""

    def setUp(self):
        super().setUp()

    @staticmethod
    def _chunk_list(cl, n_chunks):
        """Return a list of n_chunks number of sublists from cl."""
        return list(cl[i::n_chunks] for i in range(n_chunks))

    def _detect_test_files(self, extension):
        """Glob and test all materials files in the BOM directory."""
        included = set(glob.glob(f"{self.boms_dir}/**/*.{extension}", recursive=True))
        excluded = set(
            glob.glob(f"{self.boms_dir}tests/failing/**/*.{extension}", recursive=True)
        )
        boms = list(included - excluded)

        self.assertGreater(len(boms), 0)  # make sure at least one is detected
        return boms

    def _run_bom_coverage_shard(self, shard_index):
        """Execute coverage tests over this shard of files."""
        all_bom_yamls = self._detect_test_files(extension="yaml")
        self.assertGreater(len(all_bom_yamls), 0)

        # chunk the list into shards
        bom_chunks = self._chunk_list(all_bom_yamls, NUM_YAML_TEST_SHARDS)

        # extract those for this test and ensure non-zero chunks
        boms = bom_chunks[shard_index]
        self.assertGreater(len(boms), 0)

        # run ACT for every detected BOM yaml
        base_args = copy.deepcopy(self.test_args)
        for bom in boms:
            log.info(f"Testing {bom}...")
            self.test_args = copy.deepcopy(base_args)
            self.test_args.extend(f"-m {bom}".split())
            self.run_act()

    @parameterized.expand([(i,) for i in range(NUM_YAML_TEST_SHARDS)])
    def test_all_bom_execution_shard(self, shard_index):
        """Test that all BOM YAML files in the shard execute successfully."""
        self._run_bom_coverage_shard(shard_index)

    def test_all_xlsx_files(self):
        """Test that all BOM xlsx spreadsheet files execute successfully."""
        spreadsheets = self._detect_test_files(extension="xlsx")
        self.assertGreater(len(spreadsheets), 0)
        base_args = copy.deepcopy(self.test_args)
        for sheet in spreadsheets:
            log.info(f"Testing {sheet}...")
            self.test_args = copy.deepcopy(base_args)
            self.test_args.extend(f"-m {sheet}".split())
            self.run_act()
