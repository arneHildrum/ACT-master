# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.carbon import Carbon, SourceType
from act.core.common import CARBON_PER_IC_PACKAGE
from act.core.device_data import FAB_YIELD, N_ICS, PROCESS, SIZE
from act.core.models.base_model import BaseModel
from act.core.utils.logger import log
from act.core.utils.units import byte


class StorageModel(BaseModel):
    """Base model for calculating storage-related carbon emissions.

    This model provides common functionality for storage devices (DRAM, SSD, HDD)
    based on capacity and manufacturing process.

    Attributes:
        fab_model (dict): Dictionary mapping process types to carbon per capacity.
    """

    MODEL_NAME = "storage"
    REQUIRED_FIELDS = [PROCESS, FAB_YIELD, N_ICS, SIZE]

    def __init__(self, fab_model: dict) -> None:
        """
        Initializes a new instance of the StorageModel class.
        Args:
            fab_model (dict): A dictionary representing the fabrication model.
        """
        self.fab_model = fab_model

    def _check_process(self, process: str) -> None:
        """
        Checks if a process exists in the fabrication model.
        Args:
            process (str): The name of the process to check.
        Raises:
            SystemExit: If the process does not exist in the fabrication model.
        """
        if process not in self.fab_model:
            log.error(
                f"Target storage process {process} not found. Fab model: {self.fab_model}"
            )
            exit(-1)

    def _check_yield(self, fab_yield: float) -> None:
        """
        Checks if the fabrication yield is valid.
        Args:
            fab_yield (float): The fabrication yield to check.
        Raises:
            SystemExit: If the fabrication yield is not a float between 0 and 1.
        """
        if type(fab_yield) is not float or fab_yield <= 0 or fab_yield > 1:
            log.error(
                f"Fab yield must be a float greater than 0 up to 1.0. Got {fab_yield}."
            )
            exit(-1)

    def get_cpg(self, process: str, fab_yield: float) -> float:
        """
        Calculates the carbon per gigabyte for a given process and fabrication yield.
        Args:
            process (str): The name of the process.
            fab_yield (float): The fabrication yield.
        Returns:
            float: The carbon per gigabyte.
        """
        self._check_process(process)
        self._check_yield(fab_yield)
        return self.fab_model[process] / fab_yield

    def get_carbon(self, device_data) -> Carbon:
        """
        Calculates the total carbon emissions for a given process, size, and fabrication yield.
        Args:
            process (str): The name of the process.
            size: The size of the storage device.
            fab_yield (float, optional): The fabrication yield. Defaults to DEFAULT_STORAGE_FAB_YIELD.
            n_ics (int, optional): The number of ICs. Defaults to 0.
        Returns:
            Carbon: The total carbon emissions.
        """
        self.validate_data(device_data)

        process = device_data.process
        size = device_data.size
        fab_yield = device_data.fab_yield
        n_ics = device_data.n_ics

        self._check_yield(fab_yield)
        if not size.check(byte):
            log.error(f"Capacity must have units of storage. Got {size}")
            exit(-1)
        self._check_process(process)
        return Carbon(
            size * self.get_cpg(process, fab_yield), SourceType.FABRICATION
        ) + Carbon(n_ics * CARBON_PER_IC_PACKAGE, SourceType.PACKAGING)
