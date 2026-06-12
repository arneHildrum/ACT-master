# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import sys

import numpy as np

UNKNOWN = -1


def main():
    with open(sys.argv[1]) as handle:
        _data = handle.readlines()

    data = []
    for line in _data:
        fields = line.strip().split(",")
        data.append(fields)

    np_data = np.array(data)

    headers = [
        "65nm",
        "45nm",
        "40nm",
        "28nm",
        "20nm",
        "16nm",
        "14nm",
        "10nm",
        "8nm",
        "7nm",
        "7nm_EUV",
        "5nm",
        "3nm",
        "2nm",
        "14a",
        "10a",
    ]
    nheaders = len(headers)

    base_col_idx = 2
    base_row_idx = 3

    factor_data = np_data[
        base_row_idx : base_row_idx + nheaders, base_col_idx : base_col_idx + nheaders
    ]
    rows, cols = factor_data.shape
    assert rows == cols

    # cast to float
    for r in range(rows):
        for c in range(cols):
            if factor_data[r, c] == "":
                factor_data[r, c] = UNKNOWN
    factor_data = factor_data.astype(dtype=float)

    for _ in range(nheaders):
        reflect_factors(factor_data)
        calculate(factor_data)

    # Convert each element in the row to a string and join with a tab
    for row in factor_data:
        print("\t".join(map(str, row)))

    with open("scale_factors.csv", "w") as handle:
        header = ",".join([""] + headers)
        handle.write(header + "\n")
        for n in range(nheaders):
            label = headers[n]
            data = [label] + factor_data[n, :].astype(str).tolist()
            line = ",".join(data)
            handle.write(line + "\n")


def reflect_factors(factor_data):
    rows, cols = factor_data.shape
    for r in range(rows):
        for c in range(cols):
            if factor_data[r, c] != UNKNOWN:
                continue
            else:
                if factor_data[c, r] is not None:
                    factor_data[r, c] = 1 / factor_data[c, r]


def calculate(factor_data):
    rows, cols = factor_data.shape

    # do some jank brute force propagation
    for r in range(rows):
        for c in range(cols):
            if factor_data[r, c] == UNKNOWN:
                if c - 1 > 0:
                    if (
                        factor_data[r, c - 1] != UNKNOWN
                        and factor_data[c, c - 1] != UNKNOWN
                    ):
                        factor_data[r, c] = (
                            factor_data[r, c - 1] / factor_data[c, c - 1]
                        )
                        continue
                if r - 1 > 0:
                    if (
                        factor_data[r - 1, c] != UNKNOWN
                        and factor_data[r, r - 1] != UNKNOWN
                    ):
                        factor_data[r, c] = (
                            factor_data[r - 1, c] * factor_data[r, r - 1]
                        )
                        continue
                if c + 1 < cols:
                    if (
                        factor_data[r, c + 1] != UNKNOWN
                        and factor_data[c, c + 1] != UNKNOWN
                    ):
                        factor_data[r, c] = (
                            factor_data[r, c + 1] / factor_data[c, c + 1]
                        )
                        continue
                if r + 1 < rows:
                    if (
                        factor_data[r, r + 1] != UNKNOWN
                        and factor_data[c, r + 1] != UNKNOWN
                    ):
                        factor_data[r, c] = (
                            factor_data[r, r + 1] / factor_data[c, r + 1]
                        )
                        continue


if __name__ == "__main__":
    main()
