#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Solve the purple magnetic cube puzzle in my mom's living room using CP-SAT.
"""

from typing import Self
import sys
from os import environ

from ortools.sat.python.cp_model import IntVar, Domain, CpModel, CpSolver, OPTIMAL, FEASIBLE

DEBUG = int(environ.get('MAGCUBE_DEBUG') or 0)

CoordT = tuple[int, ...]
BlockT = CoordT
PieceT = tuple[BlockT, ...]

# all valid coordinates for the puzzle
COORDS = ((x, y, z) for x in range(3) for y in range(3) for z in range(3))

class ModelBase(CpModel):
    """Abstract base class for local models.
    """
    pieces:   list[PieceT]
    at_coord: dict[CoordT, list[int]]  # value: list of piece IDs
    model:    CpModel
    solver:   CpSolver

    def __init__(self, pieces: list[PieceT]):
        """Constructor takes list of pieces as input.
        """
        super().__init__()
        self.pieces = pieces
        self.at_coord = {coord: [] for coord in COORDS}
        for p_id, piece in enumerate(pieces):
            for block_coord in piece:
                self.at_coord[block_coord].append(p_id)

        self.model = CpModel()
        self.solver = None

    def build(self) -> Self:
        """Add variables and constraints for the model.  Abstract method--must be
        implemented by the subclass.  Return ``self``, for method chaining.
        """
        raise NotImplementedError("Can't call abstract method")

    def solve(self) -> bool:
        """Return ``True`` if solution is found; ``False`` otherwise.
        """
        self.solver = CpSolver()
        if DEBUG:
            self.solver.parameters.log_search_progress = True
            if DEBUG > 1:
                self.solver.parameters.log_subsolver_statistics = True
        status = self.solver.solve(self.model)
        print(f"Status: {status} ({self.solver.status_name()})", file=sys.stderr)
        if info := self.solver.solution_info():
            print(f"Solution info: {info}", file=sys.stderr)
        return status in (OPTIMAL, FEASIBLE)

    def solution(self) -> list[int]:
        """Return list of pieces for the solution.  Abstract method--must be implemented
        by the subclass.
        """
        raise NotImplementedError("Can't call abstract method")

    def print_stats(self) -> None:
        """Print solver stats, for benchmarking and/or analysis.
        """
        if not self.solver:
            raise RuntimeError("Must solve before stats are available")

        print("\nSolver Stats", file=sys.stderr)
        print(f"- Conflicts : {self.solver.num_conflicts}", file=sys.stderr)
        print(f"- Branches  : {self.solver.num_branches}", file=sys.stderr)
        print(f"- Wall time : {self.solver.wall_time:.2f} secs", file=sys.stderr)

class Model0(ModelBase):
    """Constraints based on domains and combinations (``add_allowed_assignments()``).
    """
    blocks: dict[tuple, IntVar]
    piece_usage: list[IntVar]

    def build(self) -> Self:
        """Add variables and constraints for the model.  Return ``self``, for method
        chaining.
        """
        # Constraint #1 - The value for each block is constrained to the IDs for the pieces
        # that can occupy it
        self.blocks = {}
        for coord in COORDS:
            domain = Domain.from_values(self.at_coord[coord])
            self.blocks[coord] = self.model.new_int_var_from_domain(domain, f'block_{coord}')

        # Constraint #2 - Number of pieces (distinct values) in the solution must equal 9
        self.piece_usage = []
        for p_id, piece in enumerate(self.pieces):
            p_used = self.model.new_bool_var(f'used_{p_id}')
            self.model.add(p_used == any(var == p_id for var in self.blocks.values()))
            self.piece_usage.append(p_used)
        self.model.add(sum(self.piece_usage) == 9)
        return self

    def solution(self) -> list[int]:
        """Return list of pieces for the solution.
        """
        if not self.solver:
            raise RuntimeError("Must solve before solution is available")

        solution = [str(p_used) for p_used in self.piece_usage if self.solver.value(p_used)]
        return solution

class Model1(ModelBase):
    """Constraints based on domains and combinations (``add_allowed_assignments()``).
    """
    def build(self) -> Self:
        """Add variables and constraints for the model.  Return ``self``, for method
        chaining.
        """
        return self

    def solution(self) -> list[int]:
        """Return list of pieces for the solution.
        """
        return None

class Model2(ModelBase):
    """Constraints based on propositional logic and reification (``add_bool_and()`` and
    ``only_enforce_if()``).
    """
    def build(self) -> Self:
        """Add variables and constraints for the model.  Return ``self``, for method
        chaining.
        """
        return self

    def solution(self) -> list[int]:
        """Return list of pieces for the solution.
        """
        return None

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
    model = Model0(pieces)
    model.build()
    succ = model.solve()
    if not succ:
        return None
    model.print_stats()
    return model.solution()

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
