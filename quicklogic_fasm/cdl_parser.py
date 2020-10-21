#!/usr/bin/env python3
"""
This script provides utility function for parsing "CDL" files. They contain
statements with nested parentheses that require special handling.
"""

# =============================================================================


def split_cdl_line(line):
    """
    Splits a line of a "cdl" file into fields taking into account "{" and "}"
    brackets.

    >>> split_cdl_line("define WL_bank 0")
    ['define', 'WL_bank', '0']
    >>> split_cdl_line("define_WL_bank 0 -range {0 310}")
    ['define_WL_bank', '0', '-range', ['0', '310']]
    >>> split_cdl_line("define abc {10, {20, 30}, {40, 50}}")
    ['define', 'abc', ['10,', ['20,', '30'], ',', ['40,', '50']]]
    """

    def split(itr):
        fields = []
        temp = ""

        # Parse the field
        while True:

            # Get char
            try:
                c = next(itr)
            except StopIteration:
                break

            # Got an opening bracket
            if c == "{":

                # Split everything before the bracket
                temp = temp.strip()
                if temp:
                    fields.extend(temp.split())
                    temp = ""

                # Recurse
                fields.append(split(itr))

            # Got a closing bracket. Terminate
            elif c == "}":
                break

            # Collect chars
            else:
                temp += c

        # Split tailing string
        temp = temp.strip()
        if temp:
            fields.extend(temp.split())

        return fields

    # Split the line
    line = line.strip()
    return split(iter(line))

# =============================================================================


def read_and_parse_cdl_file(file_name):
    """
    Reads relevant information from a "cdl" file
    """

    if file_name is None:
        return None

    wl_map = {}
    bl_map = {}
    colclk_wl_map = {}

    # Parse line-by-line
    with open(file_name, "r") as fp:
        for line in fp:

            line = line.strip()
            if not line:
                continue

            if line.startswith("#"):
                continue

            fields = split_cdl_line(line)
            if not fields:
                continue

            # Row definition
            if fields[0] == "define_row":

                wl_idx = fields.index("-WL_range")

                row = 0
                for pair in fields[wl_idx+1]:
                    if isinstance(pair, list) and len(pair) == 2:
                        wl_map[row] = (int(pair[0]), int(pair[1]),)
                        row += 1

            # Clock column definition
            elif fields[0] == "define_colclk_instances":

                wl_idx = fields.index("-WL_Port")
                row_idx = fields.index("-row")

                wl = int(fields[wl_idx+1])
                row = int(fields[row_idx+1])

                colclk_wl_map[row] = (wl, wl,)

            # Column definition
            elif fields[0] == "define_column":

                bl_idx = fields.index("-BL_range")

                col = 0
                for pair in fields[bl_idx+1]:
                    if isinstance(pair, list) and len(pair) == 2:
                        bl_map[col] = (int(pair[0]), int(pair[1]),)
                        col += 1

    data = {
        "colclk_wl_map": colclk_wl_map,
        "wl_map": wl_map,
        "bl_map": bl_map,
    }

    return data
