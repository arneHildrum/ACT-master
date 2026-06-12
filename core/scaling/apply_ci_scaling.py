# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.models.ci_model import CIModel


def apply_ci_scaling(act_results, bom, scaling_config=None, ci_model=None):
    """Apply carbon intensity scaling to ACT results.

    Scales carbon emissions based on changes in manufacturing year or location
    as specified in the scaling configuration.

    Args:
        act_results (ACTResult): The ACT results to scale.
        bom (BOM): The bill of materials.
        scaling_config (ScalingConfig): Configuration specifying scaling parameters.
        ci_model (CIModel): Optional carbon intensity model.
    """
    if scaling_config is None:
        return
    if ci_model is None:
        ci_model = CIModel()

    for dname in act_results.carbon_by_device:
        for path, data in scaling_config.scaling_paths.items():
            if (data.year is None and data.location is None) or not dname.startswith(
                path
            ):  # skip if no year is specified
                continue

            # check for a supply chain location change
            dev = bom.devices[dname]
            if data.location is not None:
                new_fab_ci = data.location
            else:
                new_fab_ci = dev.fab_ci

            if data.year is not None:
                new_year_built = data.year
            else:
                new_year_built = None

            # scale the carbon emissions by the relative CI factor otherwise
            built = dev.built
            fab_ci = dev.fab_ci
            ci_scale_factor = ci_model.get_ci_scale_factor(
                src_or_loc=fab_ci,
                new_src_or_loc=new_fab_ci,
                built=built,
                new_year_built=new_year_built,
            )

            assert ci_scale_factor >= 0
            act_results.carbon_by_device[dname] *= ci_scale_factor
