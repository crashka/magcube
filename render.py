#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Render solution to magcube puzzle in 3D using VPython.
"""

import sys

from vpython import canvas, vector, box, compound, slider, wtext, event_return, rate
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

BLOCK_OFFSET = vector(1, 1, 1)
BLOCK_SIZE = vector(1, 1, 1) * 0.99

CANVAS_SIZE = {'width': 900, 'height': 600}

CoordT  = tuple[int, ...]  # ints represent individual coordinates
BlockT  = CoordT
PieceT  = tuple[BlockT, ...]
        
def render(solution: list[PieceT]) -> None:
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

    for idx, coords in enumerate(solution):
        blocks = []
        color = palette[idx % palette_sz]
        for coord in coords:
            pos = vector(*coord) - BLOCK_OFFSET
            blocks.append(box(pos=pos, size=BLOCK_SIZE, color=color))
        origin = blocks[0].pos
        pieces.append(compound(blocks, origin=origin))

    ref_pos = [vector(piece.pos) for piece in pieces]

    scene.caption = "\nUse right-click/drag to rotate image, scroll to zoom in or out\n"
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
    [(1, 0, 0), (1, 1, 0), (2, 0, 0)],
    [(2, 2, 0), (2, 1, 0), (1, 2, 0)],
    [(1, 1, 1), (1, 2, 1), (2, 1, 1)],
    [(0, 0, 2), (0, 1, 2), (1, 0, 2)],
    [(1, 2, 2), (1, 1, 2), (0, 2, 2)],
    [(2, 0, 1), (2, 0, 2), (1, 0, 1)],
    [(0, 2, 1), (0, 2, 0), (0, 1, 1)],
    [(0, 0, 0), (0, 0, 1), (0, 1, 0)],
    [(2, 2, 2), (2, 2, 1), (2, 1, 2)]
]

def main() -> int:
    """Display an example solution for the magcube problem.

    Usage::

      $ python -m render
    """
    render(example_solution)
    return 0

if __name__ == "__main__":
    sys.exit(main())
