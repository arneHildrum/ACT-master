#!/usr/bin/env python3
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import argparse
import datetime
import logging
import os
import sys

import yaml
from act.act import resolve_and_load_bom
from act.core.act_model import ACTModel
from act.core.gui.delta_dashboard import DeltaDashboard
from act.core.utils.arg_parser import get_clean_args, get_parser as get_act_parser
from act.core.utils.load_yaml_with_macros import parse_macros
from act.core.utils.logger import log, setup_logger

# Maximum number of experiments to compare
MAX_NUMBER_OF_EXPERIMENTS = 3

# Required YAML keys in supplied config file
REQUIRED_CONFIG_FILE_YAML_KEYS = ["name", "owner", "simulations", "args"]

setup_logger(loglevel=logging.INFO)


class ACTDelta:
    """
    ACT Delta tool for comparing multiple ACT simulation results.

    This tool runs multiple ACT simulations and generates a delta comparison dashboard.
    """

    def __init__(self, args, upload_fn=None):
        self.dashboard = None
        self.args = args
        self.out_dir = args.out_dir
        self.upload_fn = upload_fn

    def run(self):
        """Main execution method for ACT delta analysis."""
        self.check_raw_args()

        os.makedirs(self.args.out_dir, exist_ok=True)

        # Parse each simulation args
        sim_args_all = self.get_sim_args()

        # Run baseline simulation
        base_sim, resolved_baseline_args = self.run_sim(sim_args_all[0])

        # Save location of artifacts in a manifest
        output_manifest = {
            "act_delta": os.path.abspath(self.args.out_dir),
            "baseline": resolved_baseline_args["out_dir"],
        }

        # Run all experiment simulations
        delta_sims = []
        for idx, sim_args in enumerate(sim_args_all[1:], start=1):
            delta_sim, resolved_exp_args = self.run_sim(sim_args)
            delta_sims.append(delta_sim)
            output_manifest[f"experiment_{idx}"] = resolved_exp_args["out_dir"]

        # Generate delta dashboard
        self.dashboard = DeltaDashboard(
            out_dir=self.out_dir,
            base_sim=base_sim,
            delta_sims=delta_sims,
            dashboard_title="ACT Delta Results",
        )
        self.dashboard.generate_dashboard()

        # Upload delta dashboard unless --no-dashboard is set and upload function is available
        if not self.args.no_dashboard and self.upload_fn is not None:
            try:
                log.info("Uploading delta dashboard...")
                self.upload_fn(self.dashboard.packed_html_file)
                log.info("Delta dashboard uploaded successfully")
            except Exception as e:
                log.error(f"Failed to upload delta dashboard: {e}")
        else:
            log.info(
                f"Delta dashboard generated locally at: {self.dashboard.packed_html_file}"
            )

        # Print manifest file listing baseline and experiment output directories
        manifest = yaml.dump(output_manifest)
        log.info(f"Output file locations:\n\n{manifest}\n\n")

    def check_raw_args(self):
        """Run spot checks over unsanitized input arguments."""
        # Ensure that the number of experiments is less than the maximum
        assert len(self.args.experiment) <= MAX_NUMBER_OF_EXPERIMENTS, (
            f"Error: too many experiments specified {len(self.args.experiment)}. Max number of experiments is {MAX_NUMBER_OF_EXPERIMENTS}."
        )

    def get_sim_args(self):
        """
        Prepare args for simulation runs.
        Returns list of parsed argument objects for ACT runs.
        """
        sim_args_all = []

        for idx, act_args in enumerate([self.args.baseline] + self.args.experiment):
            # Parse the argument string using ACT's argument parser
            parsed_args = self.parse_act_args(act_args)

            if parsed_args is not None:
                # Store the index for unique output directory generation
                parsed_args._delta_idx = idx
                sim_args_all.append(parsed_args)

        return sim_args_all

    def parse_act_args(self, args_string):
        """
        Parse ACT argument string using the same parser as act.py.
        """
        # Split the argument string and parse using ACT's argument parser
        args_list = args_string.split()

        # Create a temporary parser to parse the ACT arguments
        act_parser = get_act_parser()

        try:
            # Parse the arguments using ACT's parser
            parsed_args = act_parser.parse_args(args_list)
            return parsed_args
        except SystemExit:
            # If parsing fails, log error and return None
            log.error(f"Failed to parse ACT arguments: {args_string}")
            return None

    def run_sim(self, parsed_args):
        """Run a simulation with the given ACT args using the same pattern as act.py."""
        if parsed_args is None:
            log.error("Cannot run simulation with invalid arguments")
            return None, None

        # Extract any macros specified at command line (same as act.py)
        macro_clauses = getattr(parsed_args, "macros", [])
        cl_macros = parse_macros(macro_clauses)

        # Use the same argument processing as act.py
        model_args, query_args = get_clean_args(parsed_args)

        # Ensure unique output directories for each simulation
        if hasattr(parsed_args, "_delta_idx"):
            idx = parsed_args._delta_idx
            if model_args.get("out_dir"):
                model_args["out_dir"] = f"{model_args['out_dir']}._{idx}"
            else:
                model_args["out_dir"] = f"act_out._{idx}"

        log.debug(
            f"Running ARC sim with model args: {model_args}, query args: {query_args}"
        )

        # Set timing attributes to avoid errors in SimInfoTable
        start_time = datetime.datetime.now()

        # Initialize the model (same as act.py)
        act_model = ACTModel(**model_args)
        act_model.start_time = start_time

        # Load BOM using the same function as act.py
        bom = resolve_and_load_bom(parsed_args, cl_macros)
        query_args.update(bom=bom)

        # Run the simulation
        try:
            carbon_result = act_model.get_carbon(**query_args)
            log.info(f"Simulation completed. Total carbon: {carbon_result.total()}")
        except Exception as e:
            log.error(f"Simulation failed: {e}")
            # Continue with the model even if simulation fails for delta comparison

        # Set end time after simulation
        act_model.end_time = datetime.datetime.now()

        return act_model, model_args


def get_parser():
    """Create argument parser for ACT delta tool."""
    parser = argparse.ArgumentParser(
        description="Runs ACT baseline and one/more experiments to generate delta comparison stats"
    )
    parser.add_argument(
        "--baseline",
        type=str,
        help="ACT arguments for a baseline simulation run",
    )
    parser.add_argument(
        "--experiment",
        type=str,
        action="append",
        help="ACT arguments for an experiment simulation run to be compared against the baseline",
    )
    parser.add_argument(
        "-o",
        "--out-dir",
        type=str,
        default="act_delta_out",
        help="Output directory for resulting delta statistics",
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        default=False,
        help="Upload delta dashboard for sharing (requires upload integration)",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        help="Path to config file; overrides CLI args with values from specified file before starting delta run",
    )

    return parser


def load_args(parser):
    """Parse CLI args and override them with updated values from config file if specified."""
    args = parser.parse_args()

    # Override arguments from config YAML file if `--config` flag is specified
    if args.config:
        # Load updated argument values from file
        try:
            args.config = os.path.abspath(os.path.expanduser(args.config))
            log.info(f"Overriding CLI arguments with values from file: {args.config}")
            with open(args.config, "r") as fd:
                config_override = yaml.safe_load(fd)

            # Check if loaded config is valid
            if not config_override:
                log.error(f"Error: loaded empty config from file {args.config}")
                sys.exit(1)
            if not all(
                req_key in config_override.keys()
                for req_key in REQUIRED_CONFIG_FILE_YAML_KEYS
            ):
                log.error(
                    f"Error: config file YAML missing required keys: {', '.join(REQUIRED_CONFIG_FILE_YAML_KEYS)}"
                )
                sys.exit(1)

            # Print config name and owner info
            log.info(
                f"Running configuration `{config_override['name']}`; for support contact: `{config_override['owner']}`."
            )

            # Override baseline and experiment definitions
            updated_parser_defaults = {
                "baseline": config_override["simulations"]["baseline"],
                "experiment": config_override["simulations"]["experiment"],
            }

            # Override act_delta cli args
            updated_parser_defaults.update(config_override["args"])

            parser.set_defaults(**updated_parser_defaults)
            args = parser.parse_args()
        except FileNotFoundError:
            log.error(f"Error: config file not found: {args.config}")
            sys.exit(1)
        except Exception as e:
            log.error(f"Error: can not process YAML: {e}")
            sys.exit(1)

    # Check that baseline and experiment are provided
    if not args.baseline or not args.experiment:
        log.error(
            "Error: `experiment` and `baseline` arguments are required. Specify them via CLI or config file."
        )
        sys.exit(1)

    return args


def main(upload_fn=None):
    """Main entry point for ACT delta tool."""
    # Process arguments
    parser = get_parser()
    args = load_args(parser)

    # Print delta simulation args for visibility
    args_str = "".join([f"\t{k}: {v}\n" for k, v in vars(args).items()])
    log.info(f"Delta simulation arguments: \n\n {args_str}")

    # Run the delta simulation
    act_delta = ACTDelta(args=args, upload_fn=upload_fn)
    act_delta.run()


if __name__ == "__main__":
    main()
