# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import logging
import sys

from act.core.act_model import ACTModel
from act.core.bom import BOM, YAML_EXTENSION
from act.core.dse.dse_manager import DSEManager
from act.core.utils.arg_parser import get_clean_args, get_parser
from act.core.utils.load_yaml_with_macros import load_yaml_with_macros, parse_macros
from act.core.utils.logger import log, setup_logger
from act.core.utils.spreadsheet import Spreadsheet, XLSX_EXTENSION

SYMLINK_PATH = "latest_act_out"


def resolve_and_load_bom(args, cl_macros: dict):
    # if a bill of materials file is specified, use that instead of the cl arg values
    if args.materials is not None:
        if args.materials.endswith(YAML_EXTENSION):
            bom = BOM(
                **load_yaml_with_macros(args.materials, cl_macros=cl_macros),
                file=args.materials,
            )
        elif args.materials.endswith(XLSX_EXTENSION):
            spreadsheet = Spreadsheet(filepath=args.materials)
            bom = spreadsheet.import_bom()
        else:
            log.critical(
                f"Unrecognized file extension {args.materials}. Unable to load bill of materials from file. Exiting."
            )
            exit(-1)
    else:
        bom = None
    return bom


def main(upload_fn=None):
    # parse arguments and sanitize them
    parser = get_parser()
    args = parser.parse_args()

    # export the template spreadsheet and exit
    if args.export_template is not None:
        spreadsheet = Spreadsheet(args.export_template)
        spreadsheet.export_template()

        log.info(f"Template bill of materials exported to: {args.export_template}.")
        return None, None

    # setup logging and telemetry
    loglevel = getattr(logging, args.loglevel.upper())
    setup_logger(loglevel=loglevel)

    # extract any macros specified at command line
    macro_clauses = args.macros
    cl_macros = parse_macros(macro_clauses)

    model_args, query_args = get_clean_args(args)

    log.info("ACT model args: " + " ".join(sys.argv))

    # initialize the model
    model = ACTModel(**model_args)

    bom = resolve_and_load_bom(args, cl_macros)
    query_args.update(bom=bom)

    # query the model for the carbon estimate
    carbon = model.get_carbon(**query_args)
    log.info(f"Total carbon for this system configuration: {carbon.total()}")

    # if the design space exploration analysis is specified run and add to the dashboard assets
    if args.dse:
        dse_manager = DSEManager(
            bom, base_act=model, model_args=model_args, query_args=query_args
        )
        dse_manager.run()
        dse_cards = dse_manager.get_dse_cards()
    else:
        dse_manager = None
        dse_cards = None

    # renders and uploads the dashboard
    if not args.no_dashboard:
        model.generate_dashboard(extra_cards=dse_cards, upload_fn=upload_fn)

    log.info("ACT done executing...")

    return model, dse_manager


if __name__ == "__main__":
    main()
