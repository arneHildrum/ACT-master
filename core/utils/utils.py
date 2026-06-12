# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.common import DEFAULT_DUTY_CYCLE, DEFAULT_LIFE_CYCLE, DEFAULT_OP_YEAR
from act.core.models.ci_model import DEFAULT_OP_LOCATION
from act.core.utils.logger import log
from act.core.utils.units import mW


def resolve_op_power(cl_op_power, bom):
    """Resolve operating power from command line or BOM.

    Args:
        cl_op_power (pint.Quantity): Command line operating power.
        bom (BOM): Bill of materials.

    Returns:
        pint.Quantity: Resolved operating power.
    """
    # resolve the operating power
    if cl_op_power is not None:
        _op_power = cl_op_power
    elif bom.op_power is not None:
        _op_power = bom.op_power
    else:
        log.warning(
            "No operating power was specified. Using zero power which will result in zero operational carbon cost. If this is not intended, please specify an operating power in the BOM, API, or CL args."
        )
        _op_power = 0 * mW
    return _op_power


def resolve_op_ci(cl_op_ci, bom):
    """Resolve operational carbon intensity from command line or BOM.

    Args:
        cl_op_ci (str): Command line carbon intensity setting.
        bom (BOM): Bill of materials.

    Returns:
        str: Resolved carbon intensity location or source.
    """
    # resolve the CI with precedence
    if cl_op_ci is not None:
        _op_ci = cl_op_ci
    elif bom.op_ci is not None:
        _op_ci = bom.op_ci
    else:
        _op_ci = DEFAULT_OP_LOCATION
    return _op_ci


def resolve_duty_cycle(cl_duty_cycle, bom):
    """Resolve duty cycle from command line or BOM.

    Args:
        cl_duty_cycle (float): Command line duty cycle.
        bom (BOM): Bill of materials.

    Returns:
        float: Resolved duty cycle.
    """
    if cl_duty_cycle is not None:
        _duty_cycle = cl_duty_cycle
    elif bom.duty_cycle is not None:
        _duty_cycle = bom.duty_cycle
    else:
        _duty_cycle = DEFAULT_DUTY_CYCLE
    return _duty_cycle


def resolve_life_cycle(cl_life_cycle, bom):
    """Resolve life cycle from command line or BOM.

    Args:
        cl_life_cycle (pint.Quantity): Command line life cycle.
        bom (BOM): Bill of materials.

    Returns:
        pint.Quantity: Resolved life cycle.
    """
    if cl_life_cycle is not None:
        _life_cycle = cl_life_cycle
    elif bom.life_cycle is not None:
        _life_cycle = bom.life_cycle
    else:
        _life_cycle = DEFAULT_LIFE_CYCLE
    return _life_cycle


def resolve_op_year(cl_op_year, bom):
    """Resolve operating year from command line or BOM.

    Args:
        cl_op_year (int): Command line operating year.
        bom (BOM): Bill of materials.

    Returns:
        int: Resolved operating year.
    """
    if cl_op_year is not None:
        _op_year = cl_op_year
    elif bom.op_year is not None:
        _op_year = bom.op_year
    else:
        _op_year = DEFAULT_OP_YEAR
    return _op_year
