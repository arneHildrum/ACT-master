# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import logging
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

from act.act import main
from act.core.act_model import ACTModel
from act.core.common import AbatementLevel
from act.core.models.ci_model import DEFAULT_FAB_LOCATION
from act.core.utils.logger import setup_logger
from act.core.utils.units import kg


class BaseTestCase(unittest.TestCase):
    def setUp(self):
        # temp_dir for tests
        self.temp_dir = tempfile.TemporaryDirectory(prefix="act_out_")
        self.out_dir = self.temp_dir.name

        self.test_dir = os.path.abspath(os.path.dirname(__file__))
        self.test_args = ["./act", "--test", "--no-dashboard"]
        self.boms_dir = f"{self.test_dir}/../boms/"
        self.results_dir = f"{self.test_dir}/../results"
        self.configs_dir = f"{self.test_dir}/../configs"

        self.gpa = AbatementLevel.GPA95
        self.fab_ci = DEFAULT_FAB_LOCATION
        self.act_model = ACTModel(use_legacy=True)

        setup_logger(loglevel=logging.INFO)

    def run_act(self, loglevel=logging.INFO):
        setup_logger(loglevel=loglevel)
        with patch.object(sys, "argv", self.test_args):
            act, dse = main()
            if dse is None:
                return act
            else:
                return act, dse

    def _filtered_total(self, prefix, results):
        total = 0 * kg
        entries = 0
        for sname, carbon in results.items():
            if sname.startswith(prefix):
                total += carbon.total()
                entries += 1
        return total
