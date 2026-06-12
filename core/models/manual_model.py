# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.carbon import Carbon
from act.core.device_data import CARBON, CTYPE
from act.core.models.base_model import BaseModel


class ManualModel(BaseModel):
    """Model for directly passing through manually specified carbon emissions."""

    MODEL_NAME = "manual"
    REQUIRED_FIELDS = [CARBON, CTYPE]

    def get_carbon(self, device_data):
        self.validate_data(device_data)
        return Carbon(device_data.carbon, device_data.ctype)
