#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Solve the purple magnitic cube puzzle in my mom's living room using CP-SAT.
"""

import sys

from ortools.sat.python import cp_model

def build_pieces() -> list:
    """
    """
    xy_shapes = []  # list[tuple[tuple]] (shapes, squares, 2d-coords)
    xz_shapes = []
    yz_shapes = []
    xy_pieces = []  # list[tuple[tuple]] (pieces, blocks, 3d-coords)
    xz_pieces = []
    yz_pieces = []
    
    # xy_shapes - type #1
    centers_1 = (0, 0), (0, 1), (1, 1), (1, 0)
    for cx, cy in centers_1:
        rt = cx, cy + 1
        dn = cx + 1, cy
        shape = (cx, cy), rt, dn
        xy_shapes.append(shape)

    # xy_shapes - type #2
    centers_2 = (1, 1), (1, 2), (2, 2), (2, 1)
    for cx, cy in centers_2:
        lf = cx, cy - 1
        up = cx - 1, cy
        shape = (cx, cy), lf, up
        xy_shapes.append(shape)

    # xz_shapes
    for shape in xy_shapes:
        xz_shapes.append(tuple((x, 2 - y) for x, y in shape))
        
    # yz_shapes
    for shape in xz_shapes:
        yz_shapes.append(tuple((2 - x, z) for x, z in shape))
        
    # generate pieces from shapes
    for i in range(3):
        z = i
        for shape in xy_shapes:
            xy_pieces.append(tuple((x, y, z) for x, y in shape))

        y = i
        for shape in xz_shapes:
            xz_pieces.append(tuple((x, y, z) for x, z in shape))

        x = i
        for shape in yz_shapes:
            yz_pieces.append(tuple((x, y, z) for y, z in shape))

    return xy_pieces + xz_pieces + yz_pieces
        
########
# main #
########

def main() -> int:
    """Usage::
    
      $ python -m magcube
    """
    pieces = build_pieces()
    return 0

if __name__ == "__main__":
    sys.exit(main())
