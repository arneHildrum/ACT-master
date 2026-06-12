# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.gui.plots.base_table import BaseTable
from act.core.utils.units import g, kg, km, mi, Mton, ton, year

# flying per kilogram is cited at 90 g / kilometer
FLYING_PER_KILOMETER = 90 * g / km

# EPA driving emissions per mile and miles per year per person as of 2023- https://www.epa.gov/greenvehicles/greenhouse-gas-emissions-typical-passenger-vehicle
DRIVING_PER_MILE = 400 * g / mi
US_DRIVING_MILES_PER_YEAR = 11500 * mi / year


class ScalingTable(BaseTable):
    """A table that displays carbon emissions scaling analysis.

    This table shows how carbon emissions scale with different numbers of users,
    and provides comparisons with other emission sources like flying and driving.
    """

    def __init__(self, act):
        """Initialize the Scaling Table.

        Args:
            act (ACTModel): The ACT analysis object containing carbon results.
        """
        self.carbon_results = act.results.carbon_by_device
        self.life_cycle = act.life_cycle
        super().__init__()

        # carbon per user
        tunits = kg / year
        funits = str(tunits.units)
        fmillion_ton = "Million " + str((ton / year).units)

        # calculate the carbon per year for various numbers of users
        device_carbon = sum(self.carbon_results.values()).total()
        cpu = device_carbon / self.life_cycle
        cp_thousand = 1000 * cpu
        cp_million = 1000000 * cpu
        cp_billion = 1000000000 * cpu

        # energy sector estimates and comparisons
        # US energy-related emissions: https://www.eia.gov/environment/emissions/carbon/
        us_energy_2023 = 4807 * Mton / year

        # add estimated cost per aviation kilometer for context
        # recent data of number of miles or km traveled by air per person varies due to impact of the pandemic and data availability but the order of magnitude is around 1000-2000 miles or 1500-4000 km
        us_km_per_person = 2000 * km / year
        us_flying_per_person = FLYING_PER_KILOMETER * us_km_per_person
        us_flying_per_million = us_flying_per_person * 1000000

        # calculate the average emissions from driving per person per year in the US
        us_driving_per_person = DRIVING_PER_MILE * US_DRIVING_MILES_PER_YEAR
        us_driving_per_million = us_driving_per_person * 1000000

        self.data_dict = {
            "Carbon Per Device (Operation + Embodied)": "%.2f" % device_carbon.to(kg).m
            + " kg",
            "Estimated Device Lifetime": str(self.life_cycle.to(year)),
            "Device Carbon Per User / Year": "%.2f " % cpu.to(tunits).m + funits,
            "Flying (US) - Carbon per Person / Year": "%.2f "
            % (us_flying_per_person).to(tunits).m
            + str(funits),
            "Driving (US) - Carbon per Person / Year": "%.2f "
            % (us_driving_per_person).to(tunits).m
            + funits,
            "Device Carbon Per 1000 Users / Year": "%.2f "
            % cp_thousand.to(ton / year).m
            + str((ton / year).units),
            "Device Carbon Per Million Users / Year": "%.2f "
            % cp_million.to(ton / year).m
            + str((ton / year).units),
            "Flying (US) - Carbon per Million People / Year": "%.2f "
            % us_flying_per_million.to(ton / year).m
            + str((ton / year).units),
            "Driving (US) - Carbon per Million People / Year": "%.2f "
            % us_driving_per_million.to(ton / year).m
            + str((ton / year).units),
            "Device Carbon Per Billion Users / Year": "%.2f "
            % (cp_billion.to(ton / year).m / 1000000)
            + fmillion_ton,
            "US Energy Sector Emissions (2023)": "%.2f "
            % (us_energy_2023.to(ton / year).m / 1000000)
            + fmillion_ton,
        }

        self.header = ["Analysis", "Value"]

    def get_html(self):
        """Generate the HTML representation of the scaling table.

        Returns:
            str: HTML representation of the table with left-aligned columns.
        """
        return super().get_html(align={x: "l" for x in self.header})
