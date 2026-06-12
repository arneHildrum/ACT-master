# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import importlib
import pkgutil


def import_submodules(module, path_exclusions=None):
    """Import all submodules of a module recursively.

    Args:
        module: The parent module to import submodules from.
        path_exclusions (list[str]): Optional list of module path prefixes to exclude.

    Returns:
        list: List of imported module objects.
    """
    _path_exclusions = path_exclusions if path_exclusions is not None else []

    imported_modules = []
    for _, module_name, _ in pkgutil.walk_packages(
        module.__path__, module.__name__ + "."
    ):
        if any(module_name.startswith(exclusion) for exclusion in _path_exclusions):
            continue
        module = importlib.import_module(module_name)
        imported_modules.append(module)

        # import all the module attributes which should pick up classes
        for attribute_name in dir(module):
            if not attribute_name.startswith("__"):
                globals()[attribute_name] = getattr(module, attribute_name)

    return imported_modules


def all_subclasses(cls):
    """Recursively find all subclasses of a given class.

    Args:
        cls: The parent class to find subclasses of.

    Returns:
        set: Set of all subclass types.
    """
    return set(cls.__subclasses__()).union(
        [s for c in cls.__subclasses__() for s in all_subclasses(c)]
    )
