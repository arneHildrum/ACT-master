# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from abc import abstractmethod

from act.core.utils.logger import log


class BaseModel:
    """Base class for carbon emission models.

    This class provides a foundation for implementing device-specific
    carbon emission models. Subclasses must implement the get_carbon method.

    Attributes:
        BASE_MODEL_NAME (str): Default model name for the base class.
        MODEL_NAME (str): Name of the model (must be overridden in subclasses).
        REQUIRED_FIELDS (list): List of required device data fields.
    """

    BASE_MODEL_NAME = "base"
    MODEL_NAME = BASE_MODEL_NAME
    REQUIRED_FIELDS = []

    def __init__(self):
        """Initialize the base model.

        Raises:
            ValueError: If MODEL_NAME is not overridden in the subclass.
        """
        if self.MODEL_NAME == self.BASE_MODEL_NAME:
            raise ValueError(
                "Model MODEL_NAME must be set to distinguish it from other models."
            )

    @abstractmethod
    def get_carbon(self, device_data):
        """Calculate carbon emissions for a device.

        Args:
            device_data (DeviceData): Device specification data.

        Returns:
            Carbon: The calculated carbon emissions.

        Raises:
            NotImplementedError: If not implemented by subclass.
        """
        raise NotImplementedError(
            "Model get_carbon() method was not implemented. This must be implemented in subclasses of BaseModel."
        )

    def validate_data(self, device_data):
        """Validate that required fields are present in device data.

        Args:
            device_data (DeviceData): Device specification data to validate.

        Raises:
            SystemExit: If required fields are missing.
        """
        errors = 0
        for field in self.REQUIRED_FIELDS:
            field_val = getattr(device_data, field)
            if field_val is None:
                log.error(
                    f"For device {device_data.name}, model {self.__class__.__name__} get_carbon() requires a field {field} but got {field_val}. Cannot calculate carbon emissions. Please fix before continuing analysis."
                )
                errors += 1
        if errors > 0:
            log.critical(
                "Carbon modeling analysis encountered errors when analyzing bill of materials. Please fix the above issues. Aborting..."
            )
            exit(-1)
