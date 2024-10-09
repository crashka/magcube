#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Solve the purple magnetic cube puzzle in my mom's living room using CP-SAT.
"""

from typing import Self, Type
import sys
from os import environ

from ortools.sat.python.cp_model import IntVar, Domain, CpModel, CpSolver, OPTIMAL, FEASIBLE

DEBUG = int(environ.get('MAGCUBE_DEBUG') or 0)

# 2D types
Coord2dT = tuple[int, int]            # (x, y) coordinates
SquareT  = tuple[Coord2dT, Coord2dT]  # (position, polarity)
ShapeT   = tuple[SquareT, SquareT, SquareT]

# 3D types
CoordT   = tuple[int, int, int]   # (x, y, z) coordinates
BlockT   = tuple[CoordT, CoordT]  # (position, polarity)
PieceT   = tuple[BlockT, BlockT, BlockT]
PosKeyT  = tuple[CoordT, int]     # int represents piece ID

# all valid coordinates for the puzzle
COORDS = [(x, y, z) for x in range(3) for y in range(3) for z in range(3)]

# used as the base of a polarity vector
GRID_COORDS = [(c1, c2) for c1 in range(3) for c2 in range(3)]

#############
# BaseModel #
#############

class BaseModel(CpModel):
    """Abstract base class for local models.  Subclasses must implement ``build()`` and
    ``solution()`` methods (and optionally, ``__init__()``).
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
        for p_id, piece in enumerate(self.pieces):
            for blk_pos, blk_pol in piece:
                self.at_coord[blk_pos].append(p_id)

        self.model = CpModel()
        self.solver = None

    @property
    def npieces(self) -> int:
        """Number of pieces that the model was instantiated with.
        """
        return len(self.pieces)

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

##########
# ModelA #
##########

class ModelA(BaseModel):
    """Constraints based on propositional logic and reification (``add_bool_and()`` and
    ``only_enforce_if()``).
    """
    piece_pos:  dict[PosKeyT, IntVar]
    piece_used: list[IntVar]               # indexed by piece ID
    xy_pol_pos: dict[Coord2dT, list[int]]  # value: list of piece IDs
    xy_pol_neg: dict[Coord2dT, list[int]]
    xz_pol_pos: dict[Coord2dT, list[int]]
    xz_pol_neg: dict[Coord2dT, list[int]]
    yz_pol_pos: dict[Coord2dT, list[int]]
    yz_pol_neg: dict[Coord2dT, list[int]]

    def __init__(self, pieces: list[PieceT]):
        """Constructor takes list of pieces as input.
        """
        super().__init__(pieces)
        self.piece_pos = {}
        self.piece_used = None
        self.xy_pol_pos = {(x, y): [] for (x, y) in GRID_COORDS}
        self.xy_pol_neg = {(x, y): [] for (x, y) in GRID_COORDS}
        self.xz_pol_pos = {(x, z): [] for (x, z) in GRID_COORDS}
        self.xz_pol_neg = {(x, z): [] for (x, z) in GRID_COORDS}
        self.yz_pol_pos = {(y, z): [] for (y, z) in GRID_COORDS}
        self.yz_pol_neg = {(y, z): [] for (y, z) in GRID_COORDS}
        # record the list of pieces with positive and negative polarities along each
        # polarity vector
        for p_id, piece in enumerate(self.pieces):
            for (x, y, z), (mx, my, mz) in piece:
                if mz:
                    self.xy_pol_pos[(x, y)].append(p_id)
                else:
                    self.xy_pol_neg[(x, y)].append(p_id)
                if my:
                    self.xz_pol_pos[(x, z)].append(p_id)
                else:
                    self.xz_pol_neg[(x, z)].append(p_id)
                if mx:
                    self.yz_pol_pos[(y, z)].append(p_id)
                else:
                    self.yz_pol_neg[(y, z)].append(p_id)

    def build(self) -> Self:
        """Add variables and constraints for the model.  Return ``self``, for method
        chaining.
        """
        # Constraint #0 - specify domain for (coord, p_id)
        for coord in COORDS:
            for p_id in range(self.npieces):
                self.piece_pos[coord, p_id] = self.model.new_bool_var(f'pos_{coord}_{p_id}')

        # Constraint #1 - specify variables for piece usage, and create associated
        # constraits for component blocks
        self.piece_used = [self.model.new_bool_var(f'used_{p_id}') for p_id in range(self.npieces)]
        for p_id, piece in enumerate(self.pieces):
            all_blocks = [self.piece_pos[blk_pos, p_id] for blk_pos, blk_pol in piece]
            no_blocks = [~self.piece_pos[blk_pos, p_id] for blk_pos, blk_pol in piece]
            self.model.add_bool_and(all_blocks).only_enforce_if(self.piece_used[p_id])
            self.model.add_bool_and(no_blocks).only_enforce_if(~self.piece_used[p_id])

        # Constraint #2 - ensure valid piece-block mapping for all puzzle coordinates
        for coord in COORDS:
            coord_pieces = (self.piece_pos[coord, p_id] for p_id in self.at_coord[coord])
            self.model.add(sum(coord_pieces) == 1)

        # Constraint #3 - specify variables for all polarity vectors, and ensure that all
        # pieces are aligned on vectors
        self.xy_polarity = {(x, y): self.model.new_bool_var(f'xy_pol_{(x, y)}')
                            for (x, y) in GRID_COORDS}
        self.xz_polarity = {(x, z): self.model.new_bool_var(f'xz_pol_{(x, z)}')
                            for (x, z) in GRID_COORDS}
        self.yz_polarity = {(y, z): self.model.new_bool_var(f'yz_pol_{(y, z)}')
                            for (y, z) in GRID_COORDS}

        for x, y in GRID_COORDS:
            xy_pos_pieces = [self.piece_used[p_id] for p_id in self.xy_pol_pos[(x, y)]]
            xy_neg_pieces = [self.piece_used[p_id] for p_id in self.xy_pol_neg[(x, y)]]
            self.model.add(sum(xy_pos_pieces) == 3).only_enforce_if(self.xy_polarity[(x, y)])
            self.model.add(sum(xy_neg_pieces) == 3).only_enforce_if(~self.xy_polarity[(x, y)])

        for x, z in GRID_COORDS:
            xz_pos_pieces = [self.piece_used[p_id] for p_id in self.xz_pol_pos[(x, z)]]
            xz_neg_pieces = [self.piece_used[p_id] for p_id in self.xz_pol_neg[(x, z)]]
            self.model.add(sum(xz_pos_pieces) == 3).only_enforce_if(self.xz_polarity[(x, z)])
            self.model.add(sum(xz_neg_pieces) == 3).only_enforce_if(~self.xz_polarity[(x, z)])

        for y, z in GRID_COORDS:
            yz_pos_pieces = [self.piece_used[p_id] for p_id in self.yz_pol_pos[(y, z)]]
            yz_neg_pieces = [self.piece_used[p_id] for p_id in self.yz_pol_neg[(y, z)]]
            self.model.add(sum(yz_pos_pieces) == 3).only_enforce_if(self.yz_polarity[(y, z)])
            self.model.add(sum(yz_neg_pieces) == 3).only_enforce_if(~self.yz_polarity[(y, z)])

        #self.model.add_assumption(self.piece_used[0])
        return self

    def solution(self) -> list[int]:
        """Return list of pieces for the solution.
        """
        return [p_id for p_id in range(self.npieces) if self.solver.value(self.piece_used[p_id])]

################
# build_pieces #
################

ROT_2D = {
    (0, 0): (0, 1),
    (0, 1): (1, 1),
    (1, 1): (1, 0),
    (1, 0): (0, 0)
}

REF_SHAPES = 4

def rot_coord(coord: Coord2dT) -> Coord2dT:
    """Rotate 2D coordinate (in 2x2 space) 90 degrees clockwise.  Works for either
    position or polarity.
    """
    return ROT_2D[coord]

def rot_shape(shape: ShapeT) -> ShapeT:
    """Rotate shape 90 degrees clockwise, both positionally and magnetically.
    """
    pos_0, pol_0 = shape[0]
    pos_1, pol_1 = shape[1]
    pos_2, pol_2 = shape[2]
    square_0 = rot_coord(pos_0), rot_coord(pol_0)
    square_1 = rot_coord(pos_1), rot_coord(pol_1)
    square_2 = rot_coord(pos_2), rot_coord(pol_2)
    return square_0, square_1, square_2

def tr_pos(pos: Coord2dT, vec: Coord2dT) -> Coord2dT:
    """Translate (move) position by specified 2D vector.
    """
    x, y = pos
    dx, dy = vec
    return x + dx, y + dy

def tr_shape(shape: ShapeT, vec: Coord2dT) -> ShapeT:
    """Translate (move) shape by specified 2D vector.
    """
    pos_0, pol_0 = shape[0]
    pos_1, pol_1 = shape[1]
    pos_2, pol_2 = shape[2]
    square_0 = tr_pos(pos_0, vec), pol_0
    square_1 = tr_pos(pos_1, vec), pol_1
    square_2 = tr_pos(pos_2, vec), pol_2
    return square_0, square_1, square_2

def build_pieces() -> list:
    """Generate full list of distinct (positionally and magnetically) puzzle pieces.

    Each piece is composed of three blocks, arranged in the shape of an L.  Each block is
    described by its 3D position (within a 3x3x3 space) plus 3 dimensions of polarity
    (assumed to be the same for all blocks within a piece--to be verified!).

    For polarity, ``1`` indicates directionally positive polarity for an axis, ``0``
    indicates directionally negative polarity.
    """
    xy_shapes = []  # list[ShapeT]
    xy_pieces = []  # list[PieceT]
    xz_pieces = []
    yz_pieces = []

    # base everything off of initial reference shape; NOTE that first square is the one in
    # the middle (important later for setting the origin of the piece when rendering)
    sq_0 = (0, 0), (1, 0)
    sq_1 = (1, 0), (1, 0)
    sq_2 = (0, 1), (1, 0)
    sh_0 = (sq_0, sq_1, sq_2)
    xy_shapes.append(sh_0)

    # create rotations (and validate full cycling)
    xy_shapes.append(rot_shape(xy_shapes[-1]))
    xy_shapes.append(rot_shape(xy_shapes[-1]))
    xy_shapes.append(rot_shape(xy_shapes[-1]))
    assert len(xy_shapes) == REF_SHAPES
    assert rot_shape(xy_shapes[-1]) == sh_0

    # now create translations of the shapes to complete xy_shapes
    for vec in (1, 0), (1, 1), (0, 1):
        for shape in xy_shapes[:REF_SHAPES]:
            xy_shapes.append(tr_shape(shape, vec))

    # generate xy_pieces from shapes
    for z in range(3):
        # xy_pieces
        for shape in xy_shapes:
            xy_pieces.append(tuple(((px, py, z), (mx, my, 1))
                                   for (px, py), (mx, my) in shape))

        # add flipped xy_pieces--flipping along center block diagonal (so "arm" blocks
        # swap spots), which actually means just reversing all of the polarities
        for shape in xy_shapes:
            xy_pieces.append(tuple(((px, py, z), (mx ^ 0x01, my ^ 0x01, 0))
                                   for (px, py), (mx, my) in reversed(shape)))

    # generate xz_pieces from xy_pieces
    for piece in xy_pieces:
        xz_pieces.append(tuple(((px, pz, py), (mx, mz ^ 0x01, my))
                               for (px, py, pz), (mx, my, mz) in piece))

    # generate yz_pieces from xz_pieces
    for piece in xz_pieces:
        yz_pieces.append(tuple(((py, px, pz), (my ^ 0x01, mx, mz))
                               for (px, py, pz), (mx, my, mz) in piece))

    return xy_pieces + xz_pieces + yz_pieces

##############
# fit_pieces #
##############

def fit_pieces(pieces: list, model_cls: Type = ModelA) -> list | None:
    """Return list of pieces that fit the 3x3 cube, or ``None`` if no solution is found.
    Optional second argument designates the model class to use for solving.

    For now, we are stopping after the first solution, though later we may want to explore
    for the number of distinct solutions (barring rotations).
    """
    model = model_cls(pieces)
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

      $ python -m magcube [<model>]

    where ``model`` is the designation of the model to use ('A' [default], 'B', 'C', etc.)
    """
    show_polarity = True
    model_id = 'A'
    if len(sys.argv) > 1:
        model_id = sys.argv[1]
        if len(sys.argv) > 2:
            print(f"Invalid arg(s): {' '.join(sys.argv[2:])}", file=sys.stderr)
            return 1

    cls_name = f'Model{model_id.capitalize()}'
    if cls_name not in globals():
        print(f"Model '{model_id}' does not exist", file=sys.stderr)
        return 1
    model_cls = globals()[cls_name]
    if not issubclass(model_cls, BaseModel):
        print(f"'{cls_name}' is not a valid model class", file=sys.stderr)
        return 1

    pieces = build_pieces()
    solution = fit_pieces(pieces, model_cls)
    if not solution:
        print("\nSolution not found")
        return 1

    to_render = []
    print(f"\nSolution (piece: coords):")
    for p_id in solution:
        blocks = [block for block in pieces[p_id]]
        to_render.append(blocks)
        print(f"{p_id:3d}: {blocks}")
    print("\nRendering in 3D...")
    from render import render
    render(to_render, show_polarity)
    return 0

if __name__ == "__main__":
    sys.exit(main())
