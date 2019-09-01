#!/usr/bin/env python

"""
A very basic JavaScript/TypeScript preprocessor.

Written by TheOnlyOne (@modest_ralts, https://github.com/LumenTheFairy).
"""

import argparse
from sys import stderr
import os

# Setup logging
import logging
log = logging.getLogger('log')
formatter = logging.Formatter("[jprep: %(asctime)-15s] %(message)s")
handler = logging.StreamHandler()
handler.setFormatter(formatter)
log.addHandler(handler)
log.setLevel(logging.INFO)
LOG_VERBOSE_LEVEL_NUM = 5
logging.addLevelName(LOG_VERBOSE_LEVEL_NUM, "VERBOSE")
def log_verbose(self, message, *args, **kws):
    if self.isEnabledFor(LOG_VERBOSE_LEVEL_NUM):
        self._log(LOG_VERBOSE_LEVEL_NUM, message, args, **kws)
logging.Logger.verbose = log_verbose

DEFAULT_OUT_DIR = "./preprocessed/"

def parseArguments():
    # Create argument parser
    parser = argparse.ArgumentParser(description="Preprocesses the given JavaScript/TypeScript files.")

    # Positional mandatory arguments
    parser.add_argument("files", nargs='+', help="list of files to preprocess")

    # Optional Arguments
    parser.add_argument("-o", "--out_dir", default=DEFAULT_OUT_DIR, help="directory in which to write the output files")
    parser.add_argument("--verbose", action="store_true", help="display additional information")

    # Print version
    parser.add_argument("-v", "--version", action="version", version='%(prog)s - Version 1.0')

    # Parse arguments
    args = parser.parse_args()

    return args

if __name__ == '__main__':
    # Parse the arguments
    args = parseArguments()

    # Verbose flag takes effect
    if args.verbose:
        log.setLevel(LOG_VERBOSE_LEVEL_NUM)
    log.verbose('Starting.')

    # Create the output directory if it does not exist
    if not os.path.exists(args.out_dir):
        os.makedirs(args.out_dir)
        log.verbose(f'Output directory "{args.out_dir}" created.')

    # TODO: preprocess files
