#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Solve the purple magnetic cube puzzle in my mom's living room using CP-SAT.
"""

import sys
from os import environ

from ortools.sat.python import cp_model

DEBUG = int(environ.get('MAGCUBE_DEBUG') or 0)

def build_pieces() -> list:
    """Generate full list of magnetically correct pieces
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
        for shape in xy_shapes:
            xy_pieces.append(tuple((x, y, i) for x, y in shape))

        for shape in xz_shapes:
            xz_pieces.append(tuple((x, i, z) for x, z in shape))

        for shape in yz_shapes:
            yz_pieces.append(tuple((i, y, z) for y, z in shape))

    return xy_pieces + xz_pieces + yz_pieces

def fit_pieces(pieces: list) -> list | None:
    """Return list of pieces that fit the 3x3 cube, or ``None`` if no solution is found.

    For now, we are stopping after the first solution, though later we may want to explore
    for the number of distinct solutions (barring rotations).

    We model this by creating an integer variable for each subcube (block) in the puzzle,
    whose value contains a piece number (``range(len(pieces))``).  Contraints are created
    to ensure that the right number of pieces are selected, and the block values (piece
    IDs) are compatible with the location of the block.
    """
    npieces = len(pieces)

    coords = ((x, y, z) for x in range(3) for y in range(3) for z in range(3))
    at_coord = {coord: [] for coord in coords}  # value: list of piece IDs
    for p_id, piece in enumerate(pieces):
        for block_coord in piece:
            at_coord[block_coord].append(p_id)
    domains = {coord: cp_model.Domain.from_values(at_coord[coord]) for coord in coords}

    model = cp_model.CpModel()

    # Constraint #1 - The value for each block is constrained to the IDs for the pieces
    # that can occupy it
    blocks = {}
    for coord in coords:
        blocks[coord] = model.new_int_var_from_domain(domains[coord], f'block({coord})')

    # Constraint #2 - Number of pieces (distinct values) in the solution must equal 9
    piece_usage = []
    for p_id in range(npieces):
        p_used = model.new_bool_var(f'used({p_id})')
        model.add(p_used == any(var == p_id for var in blocks.values()))
        piece_usage.append(p_used)
    model.add(sum(piece_usage) == 9)

    solver = cp_model.CpSolver()
    if DEBUG:
        solver.parameters.log_search_progress = True
        if DEBUG > 1:
            solver.parameters.log_subsolver_statistics = True
    status = solver.solve(model)
    print(f"Status: {status} ({solver.status_name(status)})", file=sys.stderr)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None

    print("\nSolver Stats", file=sys.stderr)
    print(f"- Conflicts : {solver.num_conflicts}", file=sys.stderr)
    print(f"- Branches  : {solver.num_branches}", file=sys.stderr)
    print(f"- Wall time : {solver.wall_time:.2f} secs", file=sys.stderr)

    solution = [str(p_used) for p_used in piece_usage if solver.value(p_used)]
    return solution

########
# main #
########

def main() -> int:
    """Usage::

      $ python -m magcube
    """
    pieces = build_pieces()
    solution = fit_pieces(pieces)
    if not solution:
        print("Solution not found", file=sys.stderr)
        return 1

    print(solution)
    return 0

if __name__ == "__main__":
    sys.exit(main())
