# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import numpy as np
from act.core.common import ACT_ROOT, DEFAULT_BUILD_YEAR
from act.core.utils.load_yaml_with_macros import load_yaml_with_macros
from act.core.utils.logger import log
from act.core.utils.units import g, kWh, units
from sklearn.linear_model import LinearRegression

DEFAULT_LOCATION_CONFIG = (
    f"{ACT_ROOT}/models/carbon_intensity/ember/carbon-intensity-electricity.csv"
)
DEFAULT_SOURCE_CONFIG = f"{ACT_ROOT}/models/carbon_intensity/source.yaml"
LEGACY_LOCATION_CONFIG = f"{ACT_ROOT}/models/carbon_intensity/location.yaml"

NORMALIZED_UNIT = g / kWh

DEFAULT_FAB_SOURCE = "coal"
DEFAULT_OP_LOCATION = "usa"
DEFAULT_FAB_LOCATION = "taiwan"
DEFAULT_CAP_LOCATION = "japan"


class CIModel:
    """Carbon intensity model for electricity generation.

    This model provides carbon intensity values based on geographic location
    and year, using data from the Ember dataset. It supports extrapolation
    for years not in the dataset.

    Attributes:
        location_config (str): Path to the Ember dataset file.
        source_config (str): Path to the energy source configuration file.
        default_year (int): Default year for carbon intensity lookups.
        use_legacy (bool): Whether to use legacy location data.
        carbon_data (dict): Carbon intensity data by location and year.
        source_data (dict): Carbon intensity data by energy source.
    """

    def __init__(
        self,
        location_config: str = DEFAULT_LOCATION_CONFIG,
        source_config: str = DEFAULT_SOURCE_CONFIG,
        default_year=DEFAULT_BUILD_YEAR,
        use_legacy=False,
    ):
        """Initialize the Carbon Intensity Model.

        Args:
            location_config (str): Path to the Ember dataset CSV file.
            source_config (str): Path to the energy source YAML configuration.
            default_year (int): Default year for carbon intensity lookups.
            use_legacy (bool): If True, use legacy location data instead of Ember.
        """
        self.location_config = location_config
        self.source_config = source_config
        self.default_year = default_year
        self.use_legacy = use_legacy

        # data dicts
        self.carbon_data = dict()
        self.source_data = dict()

        # track the loaded years, entity locations, and sources
        self.years = set()
        self.entities = set()
        self.sources = set()

        # cache any regression calculation requests
        self.linear_models = dict()

        # load the model data
        with open(self.location_config) as handle:
            lines = handle.readlines()[1:]  # strip header line

        # the country, code, year, and carbon intensity are the first four fields
        for line in lines:
            fields = line.split(",")
            entity, code, year, ci = fields[0:4]

            # carbon intensity is specified as g / kWh
            _ci = float(ci) * g / kWh

            # force entity as lower to make capitalization agnostic
            _entity = entity.lower()
            self.entities.add(_entity)

            _year = int(year)
            self.years.add(_year)

            if _entity not in self.carbon_data:
                self.carbon_data[_entity] = {_year: _ci}
            else:
                self.carbon_data[_entity][_year] = _ci

        # load the source data
        self.source_data = {
            k.lower(): units(v)
            for k, v in load_yaml_with_macros(
                self.source_config, delete_macros=True
            ).items()
        }
        self.sources.update(list(self.source_data.keys()))

        # load the legacy location data from built year ACT to support legacy models
        self.legacy_data = {
            k.lower(): units(v)
            for k, v in load_yaml_with_macros(
                LEGACY_LOCATION_CONFIG, delete_macros=True
            ).items()
        }

    def get_ci(self, loc_or_src: str, year: int = DEFAULT_BUILD_YEAR):
        """Get the carbon intensity for a location or energy source.

        Args:
            loc_or_src (str): The location name or energy source.
            year (int): The year for carbon intensity lookup.

        Returns:
            pint.Quantity: Carbon intensity in g/kWh.

        Raises:
            SystemExit: If the specified location is not found in the dataset.
        """
        # resolve whether the provided configuration is location or source
        if loc_or_src.lower() in self.sources:
            entity, year, source = None, None, loc_or_src
        else:
            entity, year, source = loc_or_src, year, None

        # if the entity is specified, extract the CI from location data
        if entity is not None:
            _entity = entity.lower()

            if self.use_legacy:  # support for legacy location CIs
                ci = self.legacy_data[_entity]
            else:  # otherwise extract from the Ember CI database
                # ensure the entity location exists
                if _entity not in self.entities:
                    log.critical(
                        f"The location specified location {_entity} was not found in the dataset. Valid entity locations are: {self.entities}."
                    )
                    exit(-1)
                entity_data = self.carbon_data[_entity]

                # ensure the year for the entity location exists
                if year is None:
                    ci = entity_data[self.default_year]
                elif year not in entity_data:
                    # if the year doesn't exist, extrapolate the value based on a linear interpolation
                    ci = self.extrapolate(entity, year)
                else:
                    ci = entity_data[year]

            # dimensional analysis check
            assert ci.check(g / kWh)
            return ci

        # otherwise extract from the source data which should be agnostic to the year
        else:
            return self.source_data[source.lower()]

    def extrapolate(self, loc, year: int):
        """Extrapolate carbon intensity for a year not in the dataset.

        Uses linear regression on existing data points to predict the
        carbon intensity for the specified year.

        Args:
            loc (str): The location to extrapolate for.
            year (int): The target year.

        Returns:
            pint.Quantity: Extrapolated carbon intensity in g/kWh.
        """

        if loc in self.linear_models:
            model = self.linear_models[loc]
        else:
            # get all the data points for the new_year_built location
            carbon_data = self.carbon_data[loc]

            x_values, y_values = [], []
            for k, v in carbon_data.items():
                x_values.append([k])
                y_values.append(v.to(NORMALIZED_UNIT).m)
            _x_values, _y_values = np.array(x_values), np.array(y_values)

            model = LinearRegression()
            model.fit(_x_values, _y_values)
            self.linear_models[loc] = model

        _predict = model.predict(np.array([[year]]))
        predict = _predict[0] * NORMALIZED_UNIT

        # carbon neutral is the best we can do so put the floor at zero
        predict = max(predict, 0 * g / kWh)

        return predict

    def get_ci_scale_factor(
        self,
        src_or_loc: str,
        built: int = None,
        new_year_built: int = None,
        new_src_or_loc=None,
    ):
        """Calculate the carbon intensity scale factor between two years.

        Args:
            src_or_loc (str): The fabrication location or energy source.
            built (int): The original build year.
            new_year_built (int): The target year for comparison.
            new_src_or_loc (str): Optional new location/source for comparison.

        Returns:
            float: Scale factor representing CI change from built to new_year_built.
        """
        if new_src_or_loc is None:
            new_src_or_loc = src_or_loc
        if built is None:
            built = DEFAULT_BUILD_YEAR
        if new_year_built is None:
            new_year_built = built

        built_ci = self.get_ci(src_or_loc, year=built)
        new_year_built_ci = self.get_ci(new_src_or_loc, year=new_year_built)

        return (new_year_built_ci / built_ci).m
