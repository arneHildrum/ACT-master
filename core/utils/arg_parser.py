# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import argparse

from act.core.common import AbatementLevel, DEFAULT_BUILD_YEAR
from act.core.models.ci_model import DEFAULT_OP_LOCATION
from act.core.utils.units import units


def get_parser():
    """Create and configure the argument parser for ACT.

    Returns:
        argparse.ArgumentParser: Configured argument parser for ACT CLI.
    """
    parser = argparse.ArgumentParser(description="ACT carbon modeling tool.")

    # operational CL args
    add_op_args(parser)

    # YAML config files for DRAM and fabrication emissions with local power emissions calculated
    parser.add_argument(
        "--dram-energy-config",
        type=str,
        default=None,
        help=(
            "YAML file containing DRAM fabrication electricity "
            "per unit capacity, such as kWh / GB."
        ),
    )

    # YAML config files for DRAM and fabrication emissions without local power emissions calculated
    parser.add_argument(
        "--dram-non-electric-config",
        type=str,
        default=None,
        help=(
            "YAML file containing non-electric DRAM fabrication "
            "emissions per unit capacity, such as g / GB."
        ),
    )

    # YAML config files for SSD and fabrication emissions with local power emissions calculated
    parser.add_argument(
        "--ssd-energy-config",
        type=str,
        default=None,
        help=(
            "YAML file containing SSD fabrication electricity "
            "per unit capacity, such as kWh / GB."
        ),
    )

    # YAML config files for SSD and fabrication emissions without local power emissions calculated 
    parser.add_argument(
        "--ssd-non-electric-config",
        type=str,
        default=None,
        help=(
            "YAML file containing non-electric SSD fabrication "
            "emissions per unit capacity, such as g / GB."
        ),
    )

    parser.add_argument(
        "-o",
        "--out-dir",
        type=str,
        default=None,
        help="Output directory for result files",
    )

    # either a bill of materials file or intermediate result must be specified
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-m",
        "--materials",
        type=str,
        default=None,
        help="Bill of materials list file to add to the total emissions cost.",
    )
    group.add_argument(
        "--export-template",
        type=str,
        default=None,
        help="Exports a spreadsheet template for a bill of materials for the user to fill out.",
    )

    parser.add_argument(
        "-D",
        "--macros",
        default="",
        nargs="*",
        type=str,
        help='Preprocessor macro definitions. Must be defined as a series of VAR_NAME=STRING SUBSTITUTION. So -D X_VAR="x value" Y_VAR="y_value", etc. Command line macros will override any macros provided in the yaml files.',
    )

    parser.add_argument(
        "--test", action="store_true", help="Enables test flag to disable symlinks"
    )

    parser.add_argument(
        "--gpa",
        type=int,
        default=97,
        help=f"Gasses abatement percentage level for gasses per area parameter. Options: {[x.value for x in AbatementLevel]}",
    )

    parser.add_argument(
        "--scaling-config",
        type=str,
        default=None,
        help="A scaling configuration file to specify the target processes and CI for different devices in the system. See configs/* for examples of how to specify scaling targets.",
    )

    # telemetry args
    parser.add_argument(
        "-l",
        "--loglevel",
        type=str,
        default="info",
        help="Log level to report messages and telemetry.",
    )

    parser.add_argument(
        "--export-file", type=str, default=None, help="Output file for results from ACT"
    )

    parser.add_argument(
        "--no-dashboard",
        action="store_true",
        help="Suppress dashboard asset generation.",
    )

    parser.add_argument(
        "--dse",
        action="store_true",
        default=False,
        help="Runs the design space exploration analysis. Disabled by default to minimize run time.",
    )

    parser.add_argument(
        "--legacy",
        action="store_true",
        default=False,
        help="Run the legacy ACT v1 models where relevant to reproduce older results.",
    )

    return parser


def add_op_args(parser):
    """Add operational arguments to the parser.

    Args:
        parser (argparse.ArgumentParser): The parser to add arguments to.
    """
    # operational args
    parser.add_argument(
        "--op-power",
        default=None,
        type=str,
        nargs="+",
        help="Device operating power. Must have units of power (ex. 100mW, 10W etc.).",
    )

    parser.add_argument(
        "--op-ci",
        default=None,
        type=str,
        help=f"Carbon intensity configuration for device operation. By default will use {DEFAULT_OP_LOCATION}.",
    )

    parser.add_argument(
        "--op-year",
        default=DEFAULT_BUILD_YEAR,
        type=int,
        help=f"The operating year of the device for the purpose of calculating operational CI. Defaults to {DEFAULT_BUILD_YEAR}",
    )

    parser.add_argument(
        "--duty-cycle",
        type=float,
        default=None,
        help="Device duty cycle as a fraction from 0 to 1 which calculates the OPERATION energy cost.",
    )

    parser.add_argument(
        "--life-cycle",
        type=str,
        nargs="+",
        default=None,
        help="The estimated device life_cycle before it will be replaced. (ex., 2 years, 15 days).",
    )


def get_clean_args(args):
    """Process and clean parsed arguments into model and query argument dicts.

    Args:
        args (argparse.Namespace): Parsed command line arguments.

    Returns:
        tuple[dict, dict]: Tuple of (model_args, query_args) dictionaries.
    """
    op_power = units(" ".join(args.op_power)) if args.op_power is not None else None
    op_ci = args.op_ci if args.op_ci is not None else None

    model_args = {
        "out_dir": args.out_dir,
        "test": args.test,
        "scaling_file": args.scaling_config,
        "use_legacy": args.legacy,
        "dram_energy_config": args.dram_energy_config,
        "dram_non_electric_config": args.dram_non_electric_config,
        "ssd_energy_config": args.ssd_energy_config,
        "ssd_non_electric_config": args.ssd_non_electric_config,
    }

    query_args = {
        "op_ci": op_ci,
        "op_power": op_power,
        "op_year": args.op_year,
        "duty_cycle": args.duty_cycle,
        "life_cycle": units(" ".join(args.life_cycle))
        if args.life_cycle is not None
        else None,
        "export_file": args.export_file,
    }
    print("MODEL ARGS:", model_args)                                                                                                                        # Prints the model arguments for debugging purposes
    return model_args, query_args
