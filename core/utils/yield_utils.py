# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import math
from enum import auto, Enum

from act.core.utils.logger import log
from act.core.utils.units import cm2, mm2

DEFAULT_DEFECT_DENSITY = 0.15 / cm2


def check_args(area, density):
    """Validate area and density arguments for yield calculations.

    Args:
        area (pint.Quantity): Die area.
        density (pint.Quantity): Defect density.

    Raises:
        SystemExit: If arguments have incorrect units.
    """
    if not area.check(mm2):
        log.error(f"Yield area must have area units. Got {area}")
        exit(-1)
    if not density.check(1 / mm2):
        log.error(f"Yield defect density must have units of 1 / area. Got {density}")
        exit(-1)


class Distribution(Enum):
    """Distribution types for Murphy yield model."""

    TRIANGLE = auto()
    RECT = auto()


def poisson_model(area, density):
    """Calculate die yield using the Poisson model.

    Args:
        area (pint.Quantity): Die area.
        density (pint.Quantity): Defect density.

    Returns:
        float: Calculated die yield.
    """
    check_args(area, density)
    die_yield = math.e ** (-area * density)
    return die_yield


def murphy_model(area, density, dist=Distribution.TRIANGLE):
    """Calculate die yield using the Murphy model.

    Args:
        area (pint.Quantity): Die area.
        density (pint.Quantity): Defect density.
        dist (Distribution): Distribution type (TRIANGLE or RECT).

    Returns:
        float: Calculated die yield.
    """
    check_args(area, density)
    _dist = Distribution(dist)
    if _dist == Distribution.TRIANGLE:
        die_yield = 1 - math.e ** (-area * density) / (area * density) ** 2
    else:
        die_yield = (1 - math.e ** (-2 * area * density)) / (2 * area * density)
    return die_yield


def exponential_model(area, density):
    """Calculate die yield using the exponential model.

    Args:
        area (pint.Quantity): Die area.
        density (pint.Quantity): Defect density.

    Returns:
        float: Calculated die yield.
    """
    check_args(area, density)
    die_yield = 1 / (1 + area * density)
    return die_yield
