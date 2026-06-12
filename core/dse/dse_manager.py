# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import copy
import logging
import os
import tempfile

from act.core.act_model import ACTModel, VIRTUAL_POWER_DEVICE
from act.core.gui.cards.dse_card import DSECard
from act.core.processes import LOGIC_DATA, LogicProcess
from act.core.scaling.scaling_config import ScalingConfig
from act.core.utils.logger import log


class DSEManager:
    """Design Space Exploration manager for projecting carbon emissions over time.

    Attributes:
        out_dir (str): Output directory for results.
        base_bom (BOM): The base bill of materials.
        model_args (dict): Arguments for ACTModel initialization.
        query_args (dict): Arguments for carbon queries.
        base_act (ACTModel): Base ACT model for baseline emissions.
        ci_latest_runs (dict[int, ACTModel]): Carbon intensity runs with latest year synchronization.
        ts_latest_runs (dict[int, ACTModel]): Technology scaling runs with latest year synchronization.
        ci_inc_runs (dict[int, ACTModel]): Carbon intensity runs with incremental year offsets.
        ts_inc_runs (dict[int, ACTModel]): Technology scaling runs with incremental year offsets.
    """

    def __init__(self, bom, model_args, query_args, base_act=None, out_dir=None):
        """Initialize the DSE Manager.

        Args:
            bom (BOM): The bill of materials used in the analysis.
            model_args (dict): Arguments for ACTModel initialization.
            query_args (dict): Arguments for carbon queries.
            base_act (ACTModel): Optional pre-computed base ACT model.
            out_dir (str): Output directory for results.
        """

        if out_dir is None:
            self.out_dir = tempfile.TemporaryDirectory(prefix="act_out_").name
        else:
            self.out_dir = out_dir

        if not os.path.exists(self.out_dir):
            os.makedirs(self.out_dir, exist_ok=True)

        self.base_bom = bom
        self.model_args = model_args
        self.query_args = query_args
        del query_args["bom"]

        self.base_act: ACTModel = base_act

        self.ci_latest_runs: dict[int, ACTModel] = {}
        self.ts_latest_runs: dict[int, ACTModel] = {}
        self.ci_inc_runs: dict[int, ACTModel] = {}
        self.ts_inc_runs: dict[int, ACTModel] = {}

    def run(self):
        """Execute all design space exploration analyses.

        Runs carbon intensity and technology scaling analyses with both
        latest-year synchronization and incremental year offsets.
        """
        # initialize a base ACT model for the baseline emissions
        if self.base_act is None:
            self.base_act = ACTModel(**self.model_args)
            self.base_act.get_carbon(**self.query_args, bom=self.base_bom)

        # disable logging over multiprocessing threads
        log.info("Executing design space exploration ACT runs...")
        current_level = log.level
        log.setLevel(logging.ERROR)

        # run each analysis and launch a bunch of concurrent threads
        self.run_latest_ci_analysis()
        self.run_inc_ci_analysis()
        self.run_latest_ts_analysis()
        self.run_inc_ts_analysis()

        # reset the log level after DSE sweeps are done
        log.setLevel(current_level)
        log.info("Done executing design space exploration ACT runs...")

    def run_latest_ci_analysis(self, num_years: int = 10):
        """Run carbon intensity analysis with synchronized latest manufacturing date.

        Sets the target dates to the latest manufacturing date and synchronizes
        it across all devices. Assumes static device technology nodes.

        Args:
            num_years (int): Number of years to project forward.
        """

        # autodetect the manufacturing date of the latest device
        max_year = self.get_latest_built_year()

        # run CI scaling by generating a scaling configuration for each target year
        for year in range(max_year, max_year + num_years):
            scaling_paths = {}
            for dname in self.base_act.bom.devices.keys():
                scaling_paths[dname] = {"year": year}
            scaling_config = ScalingConfig(
                name=f"DSE CI Run {year}", scaling_paths=scaling_paths
            )

            bom = copy.deepcopy(self.base_bom)
            act = ACTModel(**self.model_args, scaling_config=scaling_config)
            act.get_carbon(**self.query_args, bom=bom)
            self.ci_latest_runs[year] = act

    def run_inc_ci_analysis(self, num_years: int = 10):
        """Run carbon intensity analysis with incremental year offsets.

        Sets the target CI operating dates to be relative to each device's
        original build year.

        Args:
            num_years (int): Number of years to project forward.
        """
        self.ci_inc_runs[0] = self.base_act
        for delta in range(1, num_years + 1):
            scaling_paths = {}
            for dname, dev in self.base_act.bom.devices.items():
                scaling_paths[dname] = {"year": dev.built + delta}
            scaling_config = ScalingConfig(
                name=f"DSE CI Run +{delta}", scaling_paths=scaling_paths
            )

            bom = copy.deepcopy(self.base_bom)
            act = ACTModel(**self.model_args, scaling_config=scaling_config)
            act.get_carbon(**self.query_args, bom=bom)
            self.ci_inc_runs[delta] = act

    def _get_closest_logic_process(self, year):
        """Get the closest logic process for a given year.

        Args:
            year (int): Target year to find the closest process for.

        Returns:
            LogicProcess: The closest logic process available for the given year.
        """
        # get the closest logic tech process for the year where an entry in the logic model exists
        closest_delta = float("inf")
        closest_process = None
        for process, process_data in LOGIC_DATA.items():
            if process_data is None or process_data.year is None:
                continue
            delta = abs(process_data.year - year)
            if process_data.year <= year and delta < closest_delta:
                closest_delta = delta
                closest_process = process
        return closest_process

    def run_latest_ts_analysis(self, num_years: int = 10):
        """Run technology scaling analysis with synchronized latest year.

        Sets the target year to the bleeding edge tech node for the target year
        and synchronizes it across all devices. Assumes static carbon intensity.

        Args:
            num_years (int): Number of years to project forward.
        """

        # autodetect the manufacturing date of the latest device
        max_year = self.get_latest_built_year()

        # run the technology scaling
        for year in range(max_year, max_year + num_years):
            scaling_paths = {}
            for dname, dev in self.base_act.bom.devices.items():
                if (
                    type(dev.process) is LogicProcess
                    and dev.process is not LogicProcess.NA
                ):
                    scaling_paths[dname] = {
                        "process": self._get_closest_logic_process(year)
                    }
            scaling_config = ScalingConfig(
                name=f"DSE Tech Scaling Run {year}", scaling_paths=scaling_paths
            )

            bom = copy.deepcopy(self.base_bom)
            act = ACTModel(**self.model_args, scaling_config=scaling_config)
            act.get_carbon(**self.query_args, bom=bom)
            self.ts_latest_runs[year] = act

    def run_inc_ts_analysis(self, num_years: int = 10):
        """Run technology scaling analysis with incremental year offsets.

        Runs technology scaling with incremental updates relative to each
        device's original build year.

        Args:
            num_years (int): Number of years to project forward.
        """
        # run the technology scaling with incremental updates
        self.ts_inc_runs[0] = self.base_act
        for delta in range(1, num_years + 1):
            scaling_paths = {}
            for dname, dev in self.base_act.bom.devices.items():
                if (
                    type(dev.process) is LogicProcess
                    and dev.process is not LogicProcess.NA
                ):
                    scaling_paths[dname] = {
                        "process": self._get_closest_logic_process(dev.built + delta)
                    }
            scaling_config = ScalingConfig(
                name=f"DSE Tech Scaling +{delta}", scaling_paths=scaling_paths
            )

            bom = copy.deepcopy(self.base_bom)
            act = ACTModel(**self.model_args, scaling_config=scaling_config)
            act.get_carbon(**self.query_args, bom=bom)
            self.ts_inc_runs[delta] = act

    def get_latest_built_year(self):
        """Get the latest build year across all devices in the BOM.

        Returns:
            int: The maximum build year found among all devices.
        """
        bom = self.base_act.bom
        max_year = max(
            [
                dev.built
                for dname, dev in bom.devices.items()
                if dname != VIRTUAL_POWER_DEVICE
            ]
        )
        return max_year

    def get_dse_cards(self):
        """Generate dashboard cards for DSE results.

        Returns:
            list[DSECard]: List of dashboard cards for displaying DSE results.
        """
        cards = [DSECard(dse_manager=self)]
        return cards
