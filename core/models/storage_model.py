# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.carbon import Carbon, SourceType
from act.core.common import CARBON_PER_IC_PACKAGE
from act.core.device_data import (
    BUILT,
    FAB_CI,
    FAB_YIELD,
    N_ICS,
    PROCESS,
    SIZE,
)
from act.core.models.base_model import BaseModel
from act.core.models.ci_model import CIModel
from act.core.utils.logger import log
from act.core.utils.units import byte, g, kWh


class StorageModel(BaseModel):
    """Base model for DRAM, SSD and HDD fabrication emissions.

    The legacy model uses one total carbon-per-capacity factor:

        carbon_per_capacity / fab_yield

    An optional location-aware model instead uses:

        (
            fab_carbon_intensity * energy_per_capacity
            + non_electric_carbon_per_capacity
        ) / fab_yield

    Processes absent from the location-aware tables continue to use the
    legacy total factor.
    """

    MODEL_NAME = "storage"

    BASE_REQUIRED_FIELDS = [PROCESS, FAB_YIELD, N_ICS, SIZE]
    REQUIRED_FIELDS = BASE_REQUIRED_FIELDS

    def __init__(
        self,
        fab_model: dict,
        energy_model: dict | None = None,
        non_electric_model: dict | None = None,
        ci_model: CIModel | None = None,
    ) -> None:
        """
        Args:
            fab_model:
                Legacy mapping from process to total carbon per capacity,
                normally in g / GB.

            energy_model:
                Optional mapping from process to manufacturing electricity
                per capacity, normally in kWh / GB.

            non_electric_model:
                Optional mapping from process to non-electric fabrication
                emissions per capacity, normally in g / GB.

            ci_model:
                Carbon-intensity model used to resolve fab_ci and built.
        """

        self.fab_model = fab_model
        self.energy_model = energy_model or {}
        self.non_electric_model = non_electric_model or {}

        energy_processes = set(self.energy_model)
        non_electric_processes = set(self.non_electric_model)

        if energy_processes != non_electric_processes:
            missing_non_electric = (
                energy_processes - non_electric_processes
            )
            missing_energy = (
                non_electric_processes - energy_processes
            )

            raise ValueError(
                "Storage energy and non-electric models must contain "
                "the same processes. "
                f"Missing non-electric entries: {missing_non_electric}. "
                f"Missing energy entries: {missing_energy}."
            )

        self.ci_model = ci_model

        if self.energy_model and self.ci_model is None:
            self.ci_model = CIModel()

        # fab_ci and built are required only when at least one process has
        # a decomposed, location-aware model.
        self.REQUIRED_FIELDS = list(self.BASE_REQUIRED_FIELDS)

        if self.energy_model:
            self.REQUIRED_FIELDS.extend([FAB_CI, BUILT])

    def _supported_processes(self) -> set:
        return set(self.fab_model) | set(self.energy_model)

    def _check_process(self, process) -> None:
        if process not in self._supported_processes():
            log.error(
                f"Target storage process {process} not found. "
                f"Supported processes: {self._supported_processes()}"
            )
            exit(-1)

    def _check_yield(self, fab_yield: float) -> None:
        if (
            type(fab_yield) is not float
            or fab_yield <= 0
            or fab_yield > 1
        ):
            log.error(
                "Fab yield must be a float greater than 0 and no "
                f"greater than 1.0. Got {fab_yield}."
            )
            exit(-1)

    def _has_location_model(self, process) -> bool:
        return (
            process in self.energy_model
            and process in self.non_electric_model
        )

    def get_cpg(
        self,
        process,
        fab_yield: float,
        fab_ci: str | None = None,
        year: int | None = None,
    ):
        """Return fabrication carbon per unit storage capacity.

        Despite the historical method name, the returned value is not
        necessarily normalized specifically to GB; Pint handles compatible
        capacity units.
        """

        self._check_process(process)
        self._check_yield(fab_yield)

        if self._has_location_model(process):
            if fab_ci is None:
                log.error(
                    f"Storage process {process} has a location-aware model "
                    "but no fab_ci was provided."
                )
                exit(-1)

            if year is None:
                log.error(
                    f"Storage process {process} has a location-aware model "
                    "but no built year was provided."
                )
                exit(-1)

            assert self.ci_model is not None

            energy_per_capacity = self.energy_model[process]
            non_electric_per_capacity = (
                self.non_electric_model[process]
            )

            if not energy_per_capacity.check(kWh / byte):
                log.error(
                    "Storage manufacturing electricity must have units "
                    "of energy per storage capacity, such as kWh / GB. "
                    f"Got {energy_per_capacity} for {process}."
                )
                exit(-1)

            if not non_electric_per_capacity.check(g / byte):
                log.error(
                    "Storage non-electric emissions must have units "
                    "of carbon mass per storage capacity, such as g / GB. "
                    f"Got {non_electric_per_capacity} for {process}."
                )
                exit(-1)

            fab_carbon_intensity = self.ci_model.get_ci(
                fab_ci,
                year=year,
            )

            electricity_carbon = (
                fab_carbon_intensity * energy_per_capacity
            )

            carbon_per_capacity = (
                electricity_carbon + non_electric_per_capacity
            )

            return carbon_per_capacity / fab_yield

        # Backward-compatible behavior for processes that do not have
        # decomposed electricity/non-electric data.
        return self.fab_model[process] / fab_yield

    def get_carbon(self, device_data) -> Carbon:
        """Calculate fabrication and packaging emissions."""

        self.validate_data(device_data)

        process = device_data.process
        size = device_data.size
        fab_yield = device_data.fab_yield
        n_ics = device_data.n_ics
        fab_ci = device_data.fab_ci
        year = device_data.built

        self._check_yield(fab_yield)
        self._check_process(process)

        if not size.check(byte):
            log.error(
                f"Capacity must have units of storage. Got {size}"
            )
            exit(-1)

        carbon_per_capacity = self.get_cpg(
            process=process,
            fab_yield=fab_yield,
            fab_ci=fab_ci,
            year=year,
        )

        fabrication_carbon = size * carbon_per_capacity
        packaging_carbon = n_ics * CARBON_PER_IC_PACKAGE

        return Carbon(
            fabrication_carbon,
            SourceType.FABRICATION,
        ) + Carbon(
            packaging_carbon,
            SourceType.PACKAGING,
        )