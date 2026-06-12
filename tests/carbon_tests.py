# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.carbon import Carbon, SourceType
from act.core.utils.units import g, kg
from act.tests.base_test_case import BaseTestCase


class CarbonTests(BaseTestCase):
    """Tests for Carbon data structure operations and calculations"""

    def setUp(self):
        super().setUp()

    def test_carbon_result(self):
        """Coverage over carbon component tracking results"""
        x = Carbon(100 * g, SourceType.FABRICATION)
        y = Carbon(50 * g, SourceType.MATERIALS)
        z = Carbon(75 * g, SourceType.OPERATION)
        w = Carbon(32 * g, SourceType.MATERIALS)

        # check add operation over results
        radd = w + y
        self.assertEqual(radd.total(), 82 * g)

        # check subtract operation over results
        rsub = y - w
        self.assertEqual(rsub.total(), 18 * g)

        # check multiply by scalar operation over results
        scalar = 0.75
        rmul = w * scalar
        self.assertEqual(rmul.total(), scalar * 32 * g)

        # check component partials
        wxyz = w + x + y + z
        self.assertEqual(wxyz.total(), 257 * g)
        self.assertEqual(wxyz.partial(SourceType.FABRICATION), 100 * g)
        self.assertEqual(wxyz.partial(SourceType.MATERIALS), 82 * g)
        self.assertEqual(wxyz.partial(SourceType.OPERATION), 75 * g)
        self.assertEqual(wxyz.partial(SourceType.PACKAGING), 0 * g)

    def test_partial_utils(self):
        """Test partial retrieval and setting utilities for Carbon objects."""
        # partial either as source or string
        x = Carbon(100 * g, SourceType.FABRICATION)
        ps = x.partial("fabrication")
        pt = x.partial(SourceType.FABRICATION)

        self.assertEqual(ps, 100 * g)
        self.assertEqual(pt, 100 * g)

        # set the partial using multiple partials
        y = Carbon(50 * g, SourceType.MATERIALS)
        z = Carbon(57 * g, SourceType.OPERATION)
        w = y + z
        w.set_partials(x)
        self.assertEqual(w.partial(SourceType.FABRICATION), 100 * g)
        self.assertEqual(w.partial(SourceType.OPERATION), 57 * g)
        self.assertEqual(w.partial(SourceType.MATERIALS), 50 * g)

        # set a specific partial
        a = Carbon(
            result_dict={SourceType.FABRICATION: 5 * g, SourceType.OPERATION: 7 * g}
        )
        a.set_partial(SourceType.MATERIALS, 9 * g)
        a.set_partial("operation", 2 * g)
        self.assertEqual(a.partial(SourceType.FABRICATION), 5 * g)
        self.assertEqual(a.partial(SourceType.OPERATION), 2 * g)
        self.assertEqual(a.partial(SourceType.MATERIALS), 9 * g)

    def test_radd_with_sum(self):
        """Test __radd__ via sum() which starts with 0 + first_element"""
        x = Carbon(100 * g, SourceType.FABRICATION)
        y = Carbon(50 * g, SourceType.MATERIALS)
        z = Carbon(75 * g, SourceType.OPERATION)

        result = sum([x, y, z])

        self.assertEqual(result.total(), 225 * g)
        self.assertEqual(result.partial(SourceType.FABRICATION), 100 * g)
        self.assertEqual(result.partial(SourceType.MATERIALS), 50 * g)
        self.assertEqual(result.partial(SourceType.OPERATION), 75 * g)

    def test_radd_with_zero(self):
        """Test __radd__ returns self when adding 0 from the left"""
        x = Carbon(100 * g, SourceType.FABRICATION)
        self.assertIs(0 + x, x)

    def test_rmul_with_scalar(self):
        """Test __rmul__ for left-side scalar multiplication"""
        x = Carbon(100 * g, SourceType.FABRICATION)
        self.assertEqual((2 * x).total(), 200 * g)

    def test_rmul_with_zero(self):
        """Test __rmul__ returns self unchanged when multiplied by 0"""
        x = Carbon(100 * g, SourceType.FABRICATION)
        self.assertIs(0 * x, x)

    def test_types_method(self):
        """Test types() returns all SourceTypes present in the Carbon instance"""
        x = Carbon(
            result_dict={
                SourceType.FABRICATION: 100 * g,
                SourceType.MATERIALS: 50 * g,
                SourceType.OPERATION: 75 * g,
            }
        )
        types = x.types()

        self.assertEqual(len(types), 3)
        self.assertIn(SourceType.FABRICATION, types)
        self.assertIn(SourceType.MATERIALS, types)
        self.assertIn(SourceType.OPERATION, types)

    def test_as_str_dict(self):
        """Test as_str_dict() converts carbon data to string-keyed dict"""
        x = Carbon(100 * g, SourceType.FABRICATION)
        result = x.as_str_dict()

        self.assertIn("fabrication", result)
        self.assertIsInstance(result["fabrication"], str)

    def test_to_unit_conversion(self):
        """Test to() converts units in-place (1000g -> 1kg)"""
        x = Carbon(1000 * g, SourceType.FABRICATION)
        x.to(kg)

        self.assertEqual(x.partial(SourceType.FABRICATION).magnitude, 1.0)
        self.assertEqual(str(x.partial(SourceType.FABRICATION).units), "kilogram")

    def test_embodied_method(self):
        """Test embodied() sums only EMBODIED_SOURCES, excluding OPERATION"""
        x = Carbon(
            result_dict={
                SourceType.FABRICATION: 100 * g,
                SourceType.MATERIALS: 50 * g,
                SourceType.PACKAGING: 25 * g,
                SourceType.OPERATION: 75 * g,
            }
        )
        self.assertEqual(x.embodied(), 175 * g)

    def test_op_method(self):
        """Test op() sums only OPERATIONAL_SOURCES"""
        x = Carbon(
            result_dict={
                SourceType.FABRICATION: 100 * g,
                SourceType.OPERATION: 75 * g,
            }
        )
        self.assertEqual(x.op(), 75 * g)

    def test_init_with_none_ctype(self):
        """Test __init__ with ctype=None stores amount under None key"""
        x = Carbon(100 * g, ctype=None)

        self.assertIn(None, x.types())
        self.assertEqual(x.partial(None), 100 * g)

    def test_add_with_zero(self):
        """Test __add__ handles integer 0 as other operand"""
        x = Carbon(100 * g, SourceType.FABRICATION)
        self.assertEqual((x + 0).total(), 100 * g)

    def test_sub_with_zero(self):
        """Test __sub__ handles integer 0 as other operand"""
        x = Carbon(100 * g, SourceType.FABRICATION)
        self.assertEqual((x - 0).total(), 100 * g)
