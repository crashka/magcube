#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Render solution to magcube puzzle in 3D using VPython.
"""

import sys

from vpython import (canvas, vector, box, cone, compound, color, slider, wtext,
                     event_return, rate)
from vpython.no_notebook import stop_server

def hex2rgb(val: int) -> vector:
    """Return color value as an RGB vector.
    """
    r = val >> 16 & 0xff
    g = val >> 8 & 0xff
    b = val & 0xff
    return vector(r, g, b) / 0xff

# from https://www.patternfly.org/charts/colors-for-charts/
blues   = [0x8bc1f7, 0x519de9, 0x0066cc, 0x004b95, 0x002f5d]
greens  = [0xbde2b9, 0x7cc674, 0x4cb140, 0x38812f, 0x23511e]
cyans   = [0xa2d9d9, 0x73c5c5, 0x009596, 0x005f60, 0x003737]
purples = [0xb2b0ea, 0x8481dd, 0x5752d1, 0x3c3d99, 0x2a265f]
golds   = [0xf9e0a2, 0xf6d173, 0xf4c145, 0xf0ab00, 0xc58c00]
oranges = [0xf4b678, 0xef9234, 0xec7a08, 0xc46100, 0x8f4700]
reds    = [0xc9190b, 0xa30000, 0x7d1007, 0x470000, 0x2c0000]
blacks  = [0xf0f0f0, 0xd2d2d2, 0xb8bbbe, 0x8a8d90, 0x6a6e73]
colors  = blues[:-1] + purples[:1] + cyans[:-1]

palette = [hex2rgb(val) for val in colors]
palette_sz = len(palette)

BLOCK_OFFSET  = vector(1, 1, 1)
BLOCK_SIZE    = vector(1, 1, 1) * 0.99
BLOCK_OPACITY = 0.4  # only applied if showing polarity

ARROW_SIZE    = vector(0.25, 0.1, 0.1)
ARROW_OFFSET  = 0.125
ARROW_AXES    = [vector(1, 0, 0), vector(0, 1, 0), vector(0, 0, 1)]
ARROW_SHIFTS  = [-0.25, 0.25]
ARROW_COLORS  = [color.red, color.green, color.blue]
ARROW_SHINE   = 0.0

CANVAS_SIZE   = {'width': 900, 'height': 600}

CoordT  = tuple[int, ...]  # ints represent individual coordinates
BlockT  = CoordT
PieceT  = tuple[BlockT, ...]

def render(solution: list[PieceT], show_polarity: bool = False) -> None:
    """Create and display interactive 3d rendering of puzzle solution.
    """
    def explode(evt: slider) -> None:
        """Slider callback: explode pieces relative to the origin (0, 0, 0).
        """
        nonlocal pieces, ref_pos
        wt.text = f"{evt.value:.2f}"
        for idx, piece in enumerate(pieces):
            piece.pos = ref_pos[idx] * evt.value

    def key_pressed(evt: event_return) -> None:
        """Keydown callback: change ``running`` indicator if 'q' is pressed.
        """
        nonlocal running
        if evt.key == 'q':
            running = False

    pieces = []
    scene = canvas(**CANVAS_SIZE)
    running = True
    scene.bind('keydown', key_pressed)

    for idx, piece in enumerate(solution):
        blocks = []
        arrows = []
        blk_col = palette[idx % palette_sz]
        for block in piece:
            blk_pos, blk_pol = block
            pos = vector(*blk_pos) - BLOCK_OFFSET
            blocks.append(box(pos=pos, size=BLOCK_SIZE, color=blk_col))
            if show_polarity:
                blocks[-1].opacity = BLOCK_OPACITY
                for axis_idx, polarity in enumerate(blk_pol):
                    axis_gen = (1 if i == axis_idx else 0 for i in range(3))
                    axis = vector(*(axis_gen)) * (1 if polarity else -1)
                    for shift in ARROW_SHIFTS:
                        arrow_pos = pos + axis * (shift - ARROW_OFFSET)
                        arrow_col = ARROW_COLORS[axis_idx]
                        arrows.append(cone(size=ARROW_SIZE, axis=axis, pos=arrow_pos,
                                           color=arrow_col, shininess=ARROW_SHINE))
        origin = blocks[0].pos
        pieces.append(compound(blocks + arrows, origin=origin))

    ref_pos = [vector(piece.pos) for piece in pieces]

    scene.caption = ("\nUse Ctrl+Click (or Right-Click) to rotate, Shift+Click to drag, " +
                     "Scroll to zoom in or out\n")
    scene.append_to_caption("\nExplode pieces:  ")
    sl = slider(bind=explode, min=1.0, max=4.0, step=0.01, value=1.0)
    wt = wtext(text=f"{sl.value:.2f}")
    scene.append_to_caption("\n\n(Press 'q' to quit)")

    while (running):
        rate(30)
    stop_server()  # issues a sys.exit() somewhere in its bowels (yuk!)
    assert False, "NOTREACHED"

########
# main #
########

example_solution = [
    [((0, 1, 0), (1, 1, 0)), ((0, 0, 0), (1, 1, 0)), ((1, 1, 0), (1, 1, 0))],
    [((1, 0, 0), (0, 1, 0)), ((2, 0, 0), (0, 1, 0)), ((1, 0, 1), (0, 1, 0))],
    [((0, 0, 2), (1, 1, 0)), ((0, 0, 1), (1, 1, 0)), ((1, 0, 2), (1, 1, 0))],
    [((0, 1, 2), (0, 1, 0)), ((0, 1, 1), (0, 1, 0)), ((0, 2, 2), (0, 1, 0))],
    [((1, 1, 1), (0, 1, 0)), ((2, 1, 1), (0, 1, 0)), ((1, 1, 2), (0, 1, 0))],
    [((0, 2, 0), (0, 1, 0)), ((1, 2, 0), (0, 1, 0)), ((0, 2, 1), (0, 1, 0))],
    [((1, 2, 2), (1, 1, 0)), ((1, 2, 1), (1, 1, 0)), ((2, 2, 2), (1, 1, 0))],
    [((2, 2, 0), (1, 1, 0)), ((2, 2, 1), (1, 1, 0)), ((2, 1, 0), (1, 1, 0))],
    [((2, 0, 2), (0, 1, 0)), ((2, 0, 1), (0, 1, 0)), ((2, 1, 2), (0, 1, 0))]
]

def main() -> int:
    """Display an example solution for the magcube problem.

    Usage::

      $ python -m render [<show_polarity>]

    where magnetic polarity is shown if non-empty value for ``show_polarity`` is
    specified.
    """
    show_polarity = False
    if len(sys.argv) > 1:
        show_polarity = True
        if len(sys.argv) > 2:
            print(f"Invalid arg(s): {' '.join(sys.argv[2:])}", file=sys.stderr)
            return 1

    render(example_solution, show_polarity)
    return 0

if __name__ == "__main__":
    sys.exit(main())
