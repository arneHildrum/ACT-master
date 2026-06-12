# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.carbon import Carbon, SourceType
from act.core.common import ACT_ROOT, NA
from act.core.device_data import TYPE, WEIGHT
from act.core.models.base_model import BaseModel
from act.core.utils.load_yaml_with_macros import load_yaml_with_macros
from act.core.utils.logger import log
from act.core.utils.units import g, units

DEFAULT_MATERIALS_CONFIG = f"{ACT_ROOT}/models/materials/materials.yaml"
HEATSINK = "heatsink"


class MaterialsModel(BaseModel):
    """
    A model for estimating carbon emissions from materials.
    Attributes:
        model (dict): A dictionary mapping material types to their corresponding carbon costs.
    """

    MODEL_NAME = "materials"
    REQUIRED_FIELDS = [TYPE, WEIGHT]

    def __init__(self, model_file: str = DEFAULT_MATERIALS_CONFIG) -> None:
        """
        Initializes a new instance of the MaterialsModel class.
        Loads the materials data from a YAML file and constructs the model.
        Args:
            model_file (str, optional): The path to the materials data file. Defaults to DEFAULT_MATERIALS_CONFIG.
        """
        self.model_file = model_file
        model_data = load_yaml_with_macros(self.model_file, delete_macros=True)
        materials_data = model_data["materials"]

        # dynamically generate the materials enum
        self.material_types = [m.lower() for m in materials_data.keys()]

        self.model = {k.lower(): units(v) for k, v in materials_data.items()}
        for k, v in self.model.items():
            assert v.check(g / g), (
                f"Materials cost must be dimensionless. Got {v} for material {k}."
            )

    def get_carbon(self, device_data) -> Carbon:
        """
        Get the estimated carbon emissions from a given material and weight.
        Args:
            mat (str): The type of material.
            weight (pint.Quantity): The weight of the material.
        Returns:
            Carbon: The total carbon emissions from the material.
        Raises:
            AssertionError: If the weight is not in units of weight.
        """
        self.validate_data(device_data)

        mat = device_data.type
        weight = device_data.weight

        if mat.lower() == NA:
            log.error(
                "Material type was not specified. Reporting the carbon cost as zero."
            )
            return Carbon(0 * g, SourceType.MATERIALS)
        assert weight.check(g), f"Weight should be in units of weight but got {weight}"
        if mat.lower() not in self.model:
            valid_types = ", ".join(sorted(self.model.keys()))
            log.critical(
                f"Unknown material type '{mat}'. "
                f"Valid material types are: {valid_types}"
            )
            exit(-1)
        c_per_kg = self.model[mat.lower()]
        c = c_per_kg * weight
        return Carbon(c, SourceType.MATERIALS)
