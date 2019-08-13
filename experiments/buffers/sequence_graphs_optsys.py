#!/usr/bin/env python
#
# This program parses experiments produced by
# etalon/experiments/buffers/optsys.py.

import copy
from os import path
import shelve
import sys
# Directory containing this program.
PROGDIR = path.dirname(path.realpath(__file__))
# For python_config.
sys.path.insert(0, path.join(PROGDIR, "..", "..", "etc"))
# For parse_logs.
sys.path.insert(0, path.join(PROGDIR, ".."))

import parse_logs as par
import python_config as pyc
import sequence_graphs as sqg

# Durations.
OLD_DUR = (1000 + 9000) * 6
NEW_LONG_DUR = (20 + 9000) * 6
STATIC_DUR = (20 + 180) * 6
RESIZE_DUR = (20 + 180) * 6

# Inset window bounds.
OLD_INS = None
NEW_LONG_INS = None
STATIC_INS = None
RESIZE_INS = None

STATIC_KEY = "static"
RESIZE_KEY = "resize"
LINES_KEY = "lines"
DB_FMT = "{}.db"
OLD_KEY_FMT = "old-{}"
NEW_LONG_KEY_FMT = "new-long-{}"

# Matches experiments with a particular CC mode, 1000 us nights, and 9000 us
# days (under TDF).
OLD_FMT = "*-{}-*-20000-180000-click.txt"
# Matches experiments with a particular CC mode, 20 us nights, and 9000 us days
# (under TDF).
NEW_LONG_FMT = "*-{}-*-400-180000-click.txt"
# Matches experiments with static buffers, 20 us nights, and 180 us days (under
# TDF).
STATIC_PTN = "/*-QUEUE-False-*-400-3600-click.txt"
# Matches experiments with dynamic buffers and CC mode "reno".
RESIZE_PTN = "/*-QUEUE-True-*-reno-*click.txt"


def rst_sqg(dur):
    # Reset global lookup tables.
    sqg.FILES = {}
    sqg.KEY_FN = {}
    # Reset experiment duration.
    par.DURATION = dur
    # Do not set sqg.DURATION because it get configured automatically based on
    # the actual circuit timings.


def main():
    exp = sys.argv[1]
    if not path.isdir(exp):
        print("The first argument must be a directory, but is: {}".format(exp))
        sys.exit(-1)

    # (1) Long days, static buffers. Show the cases where TCP ramp up is not
    #     a problem.
    for cc in ["reno", "cubic"]:
        # Old optical switches.
        rst_sqg(OLD_DUR)
        old_key = OLD_KEY_FMT.format(cc)
        sqg.FILES[old_key] = OLD_FMT.format(cc)
        # Pass "cc" as a default parameter to avoid the warning
        # "cell-var-from-loop".
        sqg.KEY_FN[old_key] = lambda fn, cc=cc: cc
        old_db = shelve.open(path.join(exp, DB_FMT.format(old_key)))
        old_db[old_key] = sqg.get_data(old_db, old_key)
        sqg.plot_seq(old_db[old_key], old_key, OLD_INS)
        old_db.close()

        # New optical switches, but using long days.
        rst_sqg(NEW_LONG_DUR)
        new_long_key = NEW_LONG_KEY_FMT.format(cc)
        sqg.FILES[new_long_key] = NEW_LONG_FMT.format(cc)
        # Pass "cc" as a default parameter to avoid the warning
        # "cell-var-from-loop".
        sqg.KEY_FN[new_long_key] = lambda fn, cc=cc: cc
        new_long_db = shelve.open(path.join(exp, DB_FMT.format(new_long_key)))
        new_long_db[new_long_key] = sqg.get_data(new_long_db, new_long_key)
        sqg.plot_seq(new_long_db[new_long_key], new_long_key, NEW_LONG_INS)
        new_long_db.close()

    sys.exit(0)

    # (2) Static buffers. Show that all the TCP variants perform poorly when
    #     nights/days are short.
    rst_sqg(STATIC_DUR)
    sqg.FILES[STATIC_KEY] = STATIC_PTN
    # Extract the CC mode.
    sqg.KEY_FN[STATIC_KEY] = lambda fn: fn.split("-")[7]
    static_db = shelve.open(path.join(exp, DB_FMT.format(STATIC_KEY)))
    static_db[STATIC_KEY] = sqg.get_data(static_db, STATIC_KEY)
    sqg.plot_seq(static_db[STATIC_KEY], STATIC_KEY, STATIC_INS)
    days = copy.deepcopy(static_db[STATIC_KEY][LINES_KEY])
    static_db.close()

    # (3) Dynamic buffers. Show that dynamic buffers help all TCP variants
    #     when nights/days are short. For now, only show this for reno.
    rst_sqg(RESIZE_DUR)
    sqg.FILES[RESIZE_KEY] = RESIZE_PTN
    # Extract how long in advance the buffers resize.
    sqg.KEY_FN[RESIZE_KEY] = lambda fn: int(fn.split("-")[6]) / pyc.TDF,
    resize_db = shelve.open(path.join(exp, DB_FMT.format(RESIZE_KEY)))
    resize_db[RESIZE_KEY] = sqg.get_data(resize_db, RESIZE_KEY)
    # Use the same circuit windows as in the static buffers graph.
    resize_db[RESIZE_KEY][LINES_KEY] = days
    sqg.plot_seq(resize_db[RESIZE_KEY], RESIZE_KEY, RESIZE_INS)
    resize_db.close()


if __name__ == "__main__":
    main()