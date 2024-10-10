#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Quick utility to render pieces, for debugging.
"""

import sys

from magcube import build_pieces

########
# main #
########

def main() -> int:
    """Usage::

      $ python -m show_pieces <piece_id> [<piece_id> ...]

    where ``piece_id`` is the ID of one (or more) pieces to show.
    """
    show_polarity = True
    if len(sys.argv) == 1:
        print("Must specify at least one piece ID", file=sys.stderr)
        return 1
    show_pieces = [int(x) for x in sys.argv[1:]]

    to_render = []
    pieces = build_pieces()
    for p_id in show_pieces:
        blocks = [block for block in pieces[p_id]]
        to_render.append(blocks)
        print(f"{p_id:3d}: {blocks}")
    print("\nRendering in 3D...", end='')
    from render import render
    render(to_render, show_polarity)
    print("done")
    return 0

if __name__ == "__main__":
    sys.exit(main())
