# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from enum import Enum
from typing import Union

import pint
from act.core.utils.units import g


# track the type of each emissions component
class SourceType(Enum):
    PACKAGING = "packaging"  # cost from IC packaging process
    MATERIALS = "materials"  # cost of IC materials procurement
    OPERATION = "operation"  # cost of operating device
    FABRICATION = "fabrication"  # cost of powering and using the fab
    PASSIVES = "passive"  # cost of passives like capacitors, resistors, and diodes
    PCB = "pcb"  # PCB manufacturing cost
    MOSFET = "mosfet"  # mosfet cost
    CONNECTOR = "connector"  # connector passives cost
    OTHER = "other"  # miscellaneous source type


EMBODIED_SOURCES = [
    SourceType.PACKAGING,
    SourceType.MATERIALS,
    SourceType.FABRICATION,
    SourceType.PASSIVES,
    SourceType.PCB,
    SourceType.MOSFET,
    SourceType.CONNECTOR,
    SourceType.OTHER,
]
OPERATIONAL_SOURCES = [SourceType.OPERATION]


class Carbon:
    """
    A wrapper class around carbon results.
    Attributes:
        carbon_by_type (dict): A dictionary mapping SourceType to amounts of carbon.
    """

    def __init__(
        self,
        amount: pint.Quantity = None,
        ctype: SourceType = None,
        result_dict: dict[SourceType, pint.Quantity] = None,
    ) -> None:
        """
        Initializes a new instance of the Carbon class.
        Args:
            amount (pint.Quantity, optional): Amount of carbon with units of weight. Defaults to None.
            ctype (SourceType, optional): The emissions source type. If None is specifeid, will default to SourceType.OTHER
            result_dict (dict[SourceType, pint.Quantity], optional): A dictionary mapping SourceType to amounts of carbon. Used to initialize the object instead of the amount and ctype if provided.
        """
        # Initialize from dict if specified
        if result_dict is not None:
            self.carbon_by_type = result_dict
        else:
            assert amount.check(g), (
                f"Carbon amount must be in units of weight. Got {amount}. Make sure the quantity is unit'ed."
            )
            if ctype is not None and ctype not in SourceType:
                _ctype = SourceType.OTHER
            else:
                _ctype = ctype
            self.carbon_by_type = {_ctype: amount}

    def _get_other_keys(self, other: "Carbon") -> list[SourceType]:
        """
        Get the keys from another Carbon instance.
        Args:
            other (Carbon): The other Carbon instance.
        Returns:
            list[SourceType]: The keys from the other Carbon instance.
        """
        if other == 0:  # Handle zero that comes in through sums
            other_keys = []
        else:
            other_keys = list(other.carbon_by_type.keys())
        return other_keys

    def __add__(self, other: "Carbon") -> "Carbon":
        """
        Add another Carbon instance to this one.
        Args:
            other (Carbon): The other Carbon instance.
        Returns:
            Carbon: A new Carbon instance representing the sum of this one and the other.
        """
        # Add another carbon result
        new_result = {}
        keys = self._get_other_keys(other) + list(self.carbon_by_type.keys())
        for k in keys:
            x = self.carbon_by_type.get(k, 0 * g)
            y = other.carbon_by_type.get(k, 0 * g) if other != 0 else 0
            new_result[k] = x + y
        return Carbon(result_dict=new_result)

    def __radd__(self, other: int) -> "Carbon":
        """
        Add this Carbon instance to an integer (for sum) or other Carbon instances.
        Args:
            other (int): The integer.
        Returns:
            Carbon: This Carbon instance if the integer is 0, otherwise the result of adding this Carbon instance to the integer.
        """
        if other == 0:
            return self
        else:
            return self.__add__(other)

    def __sub__(self, other: "Carbon") -> "Carbon":
        """
        Subtract another Carbon instance from this one.
        Args:
            other (Carbon): The other Carbon instance.
        Returns:
            Carbon: A new Carbon instance representing the difference between this one and the other.
        """
        # Subtract another carbon result
        new_result = {}
        keys = self._get_other_keys(other) + list(self.carbon_by_type.keys())
        for k in keys:
            x = self.carbon_by_type.get(k, 0 * g)
            y = other.carbon_by_type.get(k, 0 * g) if other != 0 else 0
            new_result[k] = x - y
        return Carbon(result_dict=new_result)

    def __mul__(self, scalar: Union[int, float]) -> "Carbon":
        """
        Multiply the Carbon instance by a scalar value.
        Args:
            scalar (Union[int, float]): The scalar value to multiply by.
        Returns:
            Carbon: A new Carbon instance with the multiplied values.
        """
        new_result = {}
        keys = self.carbon_by_type.keys()
        for k in keys:
            new_result[k] = self.carbon_by_type[k] * scalar
        return Carbon(result_dict=new_result)

    def __rmul__(self, scalar: Union[int, float]) -> "Carbon":
        """
        Multiply the Carbon instance by a scalar value from the right.
        Note:
            If the scalar is 0, the original instance is returned unchanged.
        Args:
            scalar (Union[int, float]): The scalar value to multiply by.
        Returns:
            Carbon: A new Carbon instance with the multiplied values or the original instance if the scalar is 0.
        """
        if scalar == 0:
            return self
        else:
            return self.__mul__(scalar)

    def partial(self, ctype: Union[SourceType, str]) -> pint.Quantity:
        """
        Get the partial amount of carbon for a given SourceType.
        Args:
            ctype (SourceType): The SourceType.
        Returns:
            pint.Quantity: The partial amount of carbon.
        """
        _ctype = SourceType(ctype) if isinstance(ctype, str) else ctype
        return self.carbon_by_type.get(_ctype, 0 * g)

    def set_partials(self, other) -> None:
        """Override the partials with the carbon object provided. Preserves partials for source types not in the provided carbon"""
        for ctype in other.types():
            self.set_partial(ctype=ctype, amt=other.partial(ctype))

    def set_partial(self, ctype: SourceType, amt: pint.Quantity) -> None:
        assert amt.check(g)
        _ctype = SourceType(ctype) if isinstance(ctype, str) else ctype
        self.carbon_by_type[_ctype] = amt

    def total(self) -> pint.Quantity:
        """
        Get the total amount of carbon.
        Returns:
            pint.Quantity: The total amount of carbon.
        """
        # Return summed total over all carbon contribution components
        return sum([v for _, v in self.carbon_by_type.items()])

    def types(self) -> list[SourceType]:
        """
        Get the SourceTypes present in this Carbon instance.
        Returns:
            list[SourceType]: The SourceTypes.
        """
        return list(self.carbon_by_type.keys())

    def as_str_dict(self):
        """Return this data as a stringified dict"""
        return {
            ctype.value: str(amt.to_reduced_units())
            for ctype, amt in self.carbon_by_type.items()
        }

    def to(self, weight_unit):
        for ctype, amt in self.carbon_by_type.items():
            self.carbon_by_type[ctype] = amt.to(weight_unit)

    def embodied(self):
        return sum([self.partial(stype) for stype in EMBODIED_SOURCES])

    def op(self):
        return sum([self.partial(stype) for stype in OPERATIONAL_SOURCES])
