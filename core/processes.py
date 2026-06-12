# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass
from enum import Enum

from act.core.utils.units import nm, units


class LogicProcess(Enum):
    """Enumeration of supported logic manufacturing processes."""

    N65 = "65nm"
    N45 = "45nm"
    N40 = "40nm"
    N28 = "28nm"
    N20 = "20nm"
    N14 = "14nm"
    N10 = "10nm"
    N8 = "8nm"
    N7 = "7nm"
    N7_EUV = "7nm_EUV"
    N5 = "5nm"
    N3 = "3nm"
    N2 = "2nm"
    N2_BSP = "2nm_BSP"
    A14 = "14a"
    A10 = "10a"
    NA = "na"


@dataclass
class ProcessData:
    """Data class for storing process technology information.

    Attributes:
        size (units.Quantity): Process node size in nanometers.
        year (int): Year the process was released.
    """

    size: units.Quantity
    year: int


# bind the logic processes against the geometry and process release year
LOGIC_DATA = {
    # dates based on historical release cycle years from TSMC
    LogicProcess.N65: ProcessData(size=65 * nm, year=2006),
    LogicProcess.N45: ProcessData(size=45 * nm, year=2007),
    LogicProcess.N40: ProcessData(size=40 * nm, year=2008),
    LogicProcess.N28: ProcessData(size=28 * nm, year=2011),
    LogicProcess.N20: ProcessData(size=20 * nm, year=2014),
    LogicProcess.N14: ProcessData(size=14 * nm, year=2013),
    LogicProcess.N10: ProcessData(size=10 * nm, year=2016),
    LogicProcess.N8: ProcessData(size=8 * nm, year=None),  # no data available
    LogicProcess.N7: ProcessData(size=7 * nm, year=2018),
    LogicProcess.N7_EUV: ProcessData(size=7 * nm, year=2019),
    LogicProcess.N5: ProcessData(size=5 * nm, year=2020),
    LogicProcess.N3: ProcessData(size=3 * nm, year=2023),
    # dates based on projected roadmap from https://www.anandtech.com/show/21408/tsmc-roadmap-at-a-glance-n3x-n2p-a16-2025-2026
    LogicProcess.N2: ProcessData(size=2 * nm, year=2025),
    # assumes the same as N2
    LogicProcess.N2_BSP: ProcessData(size=2 * nm, year=2025),
    # projected from https://pr.tsmc.com/english/news/3228
    LogicProcess.A14: ProcessData(size=1.4 * nm, year=2028),
    # projected from https://www.extremetech.com/computing/tsmc-says-it-expects-to-produce-1nm-transistors-by-2030
    LogicProcess.A10: ProcessData(size=1 * nm, year=2030),
    LogicProcess.NA: None,
}


class DRAMProcess(Enum):
    """Enumeration of supported DRAM manufacturing processes."""

    DDR3_50NM = "ddr3_50nm"
    DDR3_40NM = "ddr3_40nm"
    DDR3_30NM = "ddr3_30nm"
    LPDDR3_30NM = "lpddr3_30nm"
    LPDDR3_20NM = "lpddr3_20nm"
    LPDDR2_20NM = "lpddr2_20nm"
    LPDDR4 = "lpddr4"
    DDR4_10NM = "ddr4_10nm"
    NA = "na"


class SSDProcess(Enum):
    """Enumeration of supported SSD/NAND manufacturing processes."""

    NAND_30NM = "nand_30nm"
    NAND_20NM = "nand_20nm"
    NAND_10NM = "nand_10nm"
    NAND_TLC_1Z = "nand_tlc_1z"
    NAND_TLC_V3 = "nand_tlc_v3"
    SEAGATE_3530 = "seagate_nytro_3530"
    SEAGATE_1551 = "seagate_nytro_1551"
    SEAGATE_3331 = "seagate_nytro_3331"
    WD_2016 = "western_digital_2016"
    WD_2017 = "western_digital_2017"
    WD_2018 = "western_digital_2018"
    WD_2019 = "western_digital_2019"
    NA = "na"


class HDDProcess(Enum):
    """Enumeration of supported HDD product models."""

    BARRACUDA = "BarraCuda"
    BARRACUDA2 = "BarraCuda2"
    BARRACUDA_PRO = "BarraCuda Pro"
    FIRECUDA = "FireCuda"
    FIRECUDA2 = "FireCuda2"
    IRONWOLF = "IronWolf"
    IRONWOLFPRO = "IronWolfPro"
    SKYHAWK3TB = "SkyWalk3TB"
    SKYHAWK_SURV = "Skyhawk Surveillance"
    SKYHAWK6TB = "Skyhawk-6TB"
    VIDEO_HDD = "VideoHDD"
    VIDEO_PHDD = "VideoPipelineHDD"
    EXOS2X14 = "Exos2x14"
    EXOSX12 = "Exosx12"
    EXOSX16 = "Exosx16"
    EXOS15 = "Exos15e900"
    EXOS10 = "Exos10e2400"
    EXOS500 = "Exos5e8"
    EXOS700 = "Exos7e8"
    NA = "na"


NOT_SCALING_PROCESSES = [LogicProcess.NA, DRAMProcess.NA, HDDProcess.NA, SSDProcess.NA]


def get_next_largest_logic_process(target_size):
    """Find the next largest available logic process for a given target size.

    Finds the smallest logic process node that is greater than or equal to
    the target size. This is used when a specific technology node is not
    available and needs to be rounded up to the nearest available node.

    Args:
        target_size (pint.Quantity): Target technology node size in nanometers.

    Returns:
        LogicProcess: The next largest available logic process, or LogicProcess.NA
                      if no suitable process is found.
    """
    candidates = []
    for process, process_data in LOGIC_DATA.items():
        if process_data is None:
            continue
        if process_data.size >= target_size:
            candidates.append((process, process_data.size))

    if not candidates:
        return LogicProcess.NA

    candidates.sort(key=lambda x: x[1])
    return candidates[0][0]


def resolve_logic_process_with_rounding(str_process):
    """Resolve a logic process string, rounding up to the nearest available node if needed.

    First attempts to directly resolve the process string to a LogicProcess enum value.
    If that fails, parses the string as a dimension (e.g., "15nm") and finds the next
    largest available logic process.

    Args:
        str_process (str): String representation of the process (e.g., "14nm", "15nm").

    Returns:
        tuple: (LogicProcess, bool) where the bool indicates if rounding occurred.
    """
    try:
        return LogicProcess(str_process), False
    except ValueError:
        try:
            target_size = units(str_process)
            rounded_process = get_next_largest_logic_process(target_size)
            return rounded_process, rounded_process != LogicProcess.NA
        except Exception:
            return LogicProcess.NA, False


def resolve_process(str_process, fallback=LogicProcess.NA):
    """Resolve a string process name to its corresponding process enum.

    Args:
        str_process (str): String representation of the process.
        fallback: Default process to return if no match is found.

    Returns:
        Union[LogicProcess, SSDProcess, HDDProcess, DRAMProcess]: The resolved process enum value.
    """
    process_enums = [LogicProcess, SSDProcess, HDDProcess, DRAMProcess]
    for process in process_enums:
        try:
            p = process(str_process)
            return p
        except ValueError:
            continue
    return fallback
