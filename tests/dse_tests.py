# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.tests.base_test_case import BaseTestCase


class DSETestCase(BaseTestCase):
    """Tests for design space exploration functionality"""

    def setUp(self):
        super().setUp()

    def test_ci_dse(self):
        """Check that the device build date is adjusted as expected"""
        self.test_args.extend(f"-m {self.boms_dir}/tests/built.yaml --dse".split())
        act, dse = self.run_act()

        # ensure that the values actually change between runs
        ci_inc_totals = [
            run.results.total_carbon.total() for run in dse.ci_inc_runs.values()
        ]
        ci_latest_totals = [
            run.results.total_carbon.total() for run in dse.ci_latest_runs.values()
        ]

        # ensure all values are unique and not duplicated which would indicate a regression
        self.assertEqual(len(ci_inc_totals), len(set(ci_inc_totals)))
        self.assertEqual(len(ci_latest_totals), len(set(ci_latest_totals)))

    def test_dse_manual_model(self):
        """Test that a manual model properly scales during design space exploration."""
        pass
