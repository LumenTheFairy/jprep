#!/usr/bin/env python

"""
A very basic JavaScript/TypeScript preprocessor.

Written by TheOnlyOne (@modest_ralts, https://github.com/LumenTheFairy).
"""

import argparse
from sys import stderr
import os
import re

# Setup logging
import logging
log = logging.getLogger('log')
formatter = logging.Formatter("[jprep: %(asctime)-15s] %(message)s")
handler = logging.StreamHandler()
handler.setFormatter(formatter)
log.addHandler(handler)
log.setLevel(logging.INFO)
LOG_VERBOSE_LEVEL_NUM = 15
logging.addLevelName(LOG_VERBOSE_LEVEL_NUM, "VERBOSE")
def log_verbose(self, message, *args, **kws):
    if self.isEnabledFor(LOG_VERBOSE_LEVEL_NUM):
        self._log(LOG_VERBOSE_LEVEL_NUM, message, args, **kws)
logging.Logger.verbose = log_verbose

DEFAULT_IN_DIR = "./"
DEFAULT_OUT_DIR = "./preprocessed/"

ID_CH = r'[\w$]'

def parseArguments():
    # Create argument parser
    parser = argparse.ArgumentParser(description="Preprocesses the given JavaScript/TypeScript files.")

    # Positional mandatory arguments
    parser.add_argument("files", nargs='+', help="list of files to preprocess")

    # Optional Arguments
    parser.add_argument(
        "-i", "--in_dir",
        default=DEFAULT_IN_DIR,
        help=f'directory the input files are relative to (defaults to "{DEFAULT_IN_DIR}")'
        )
    parser.add_argument(
        "-o", "--out_dir",
        default=DEFAULT_OUT_DIR,
        help=f'directory in which to write the output files (defaults to "{DEFAULT_OUT_DIR}")'
        )
    parser.add_argument(
        "-b", "--build",
        action="store_true",
        help="preprocess all files, even if the output modification is more recent than the source"
        )
    parser.add_argument("--verbose", action="store_true", help="display additional information")

    # Print version
    parser.add_argument("-v", "--version", action="version", version='%(prog)s - Version 1.0')

    # Parse arguments
    return parser.parse_args()

def atomic_streamed_file_process(in_path, out_path, process_func):
    """Effectively reads from the file at in_path, processes it with
process_func, and writes the result to out_path. However, if process_func
fails, we don't want to leave a partially written file on disk (especially
if that means the old file has already been discarded.) Yet, we still want to
be able to stream from one file to another to keep memory usage as low as
possible. This function achieves these by creating writing the result to a
temporary file, and only if process_func succeeds, it will replace the real
output file. Otherwise, the temporary file is simply discarded.
process_func is given a file open for reading, and a file open for writing,
and is expected to return the a boolean indicating its success."""
    with open(in_path, 'r') as in_file, open(out_path + '.temp', 'w') as out_file:
        success = process_func(in_file, out_file)
    if success:
        os.replace(out_path + '.temp', out_path)
    else:
        os.remove(out_path + '.temp')

def should_preprocess(in_path, out_path, full_build):
    """Determines if a file should be preprocessed.
A file should be preprocessed for any of the following reasons:
- We are doing a full build
- The file has never been preprocessed before
- The file has been modified since the last time it was preprocessed
- This script has been modified since the last time it ran"""

    if full_build:
        return True
    if not os.path.exists(out_path):
        return True
    if os.path.getmtime(in_path) > os.path.getmtime(out_path):
        return True
    if os.path.getmtime(__file__) > os.path.getmtime(out_path):
        return True
    return False

class DefinitionEntry:
    def __init__(self, value, choices):
        self.value = value
        self.choices = choices

class DefinitionEnvironment:
    def push_scope(self):
        self.scopes.append({})

    def pop_scope(self):
        self.scopes.pop()

    def __init__(self):
        self.scopes = []
        self.push_scope

    #TODO: write accessor functions

    def define(name, value=None, choices=None):
        self.scopes[-1][name] = DefinitionEntry(value, choices)

class PreprocessException(Exception):
    pass

def preprocess(in_file, out_file):

    env = DefinitionEnvironment()

    # TODO: clean up this nonlocal mess
    in_line = ''
    line_num = 0
    in_start = 0
    in_end = 0
    out_line = ''

    def report_error(message):
        raise PreprocessException(f'(Line {line_num}) {message}')

    def write_output():
        nonlocal in_line, line_num, in_start, in_end, out_line
        if in_start == 0:
            out_file.write(in_line)
        else:
            output = out_line + in_line[in_start:]
            if not output.isspace():
                out_file.write(out_line + in_line[in_start:])

    def read_line():
        nonlocal in_line, line_num, in_start, in_end, out_line
        in_line = in_file.readline()
        line_num += 1
        in_start = 0
        in_end = 0
        out_line = ''

    def append_output():
        nonlocal in_line, line_num, in_start, in_end, out_line
        out_line += in_line[in_start:in_end]
        in_start = in_end

    def move_to_next_line_if_necessary():
        nonlocal in_line, line_num, in_start, in_end, out_line
        if in_end >= len(in_line):
            raise Exception('Internal error')
        if in_line[in_end:] == '\n':
            write_output()
            read_line()

    def advance(count=1):
        nonlocal in_line, line_num, in_start, in_end, out_line
        in_end += count
        move_to_next_line_if_necessary()

    def advance_line():
        nonlocal in_line, line_num, in_start, in_end, out_line
        in_end = len(in_line) - 1
        move_to_next_line_if_necessary()

    def skip(count=1):
        nonlocal in_line, line_num, in_start, in_end, out_line
        append_output()
        in_start = in_end + count
        in_end = in_start
        move_to_next_line_if_necessary()

    def advance_until(regex):
        nonlocal in_line, line_num, in_start, in_end, out_line
        m = None
        while not m and in_line:
            m = re.search(regex, in_line[in_end:])
            if m:
                advance(m.end(0))
            else:
                advance_line()

    def skip_until(regex):
        nonlocal in_line, line_num, in_start, in_end, out_line
        m = None
        while not m and in_line:
            m = re.search(regex, in_line[in_end:])
            if m:
                skip(m.end(0))
            else:
                in_start = len(in_line) - 1
                advance_line()

    def try_skip_string(s):
        nonlocal in_line, line_num, in_start, in_end, out_line
        if in_line[in_end:].startswith(s):
            skip(len(s))
            return True
        return False

    def skip_whitespace():
        nonlocal in_line, line_num, in_start, in_end, out_line
        skip_until(r'(?!\s)')

    def try_read_identifier():
        nonlocal in_line, line_num, in_start, in_end, out_line
        m = re.search(ID_CH + '+' + r'(?!' + ID_CH + ')', in_line[in_end:])
        if not m:
            return None
        skip(m.end(0))
        return m[0]

    def read_identifier(error_message):
        nonlocal in_line, line_num, in_start, in_end, out_line
        result = try_read_identifier()
        if not result:
            report_error(error_message)
        return result

    def parse_string(quote):
        nonlocal in_line, line_num, in_start, in_end, out_line
        advance()
        advance_until(r'(?<!\\)' + quote)

    def parse_line_comment():
        nonlocal in_line, line_num, in_start, in_end, out_line
        advance_line()

    def parse_block_comment():
        nonlocal in_line, line_num, in_start, in_end, out_line
        advance_until(r'\*/')

    def parse_note():
        nonlocal in_line, line_num, in_start, in_end, out_line
        skip_until(r'\*/')

    def parse_define():
        nonlocal in_line, line_num, in_start, in_end, out_line
        name = read_identifier('Expected a name at the begining of the "define" directive.')
        skip_whitespace()
        value = None
        choices = None
        if try_skip_string('='):
            skip_whitespace()
            value = read_identifier('Expected a value after "=" in the "define" directive.')
            skip_whitespace()
        if try_skip_string('<'):
            choices = []
            while True:
                skip_whitespace()
                choice = try_read_identifier()
                if choice:
                    choices.append(choice)
                elif not choices:
                    report_error('There must be at least one choice after "<" in the "define" directive.')
                skip_whitespace()
                if not try_skip_string(','):
                    break

        skip_whitespace()
        if not try_skip_string('*/'):
            report_error('Only whitespace allowed at the end of a "define" directive.')
        # TODO: if there is a value and choice, make sure the value is one of the choices
        # TODO: add define to the environment


    def parse_directive():
        nonlocal in_line, line_num, in_start, in_end, out_line
        skip(3)
        skip_whitespace()
        directive = read_identifier('Directives must start with an identifier.')
        skip_whitespace()

        if directive == 'note':
            parse_note()
        elif directive == 'define':
            parse_define()
        # TODO: if
        else:
            end = in_line[in_end:].find('*/')
            skip(end + 2)

    read_line()
    while in_line:
        # TODO: template literals
        m = re.search(r'/\*\$|"|\'|//|/\*|\{|\}', in_line[in_end:])
        if m:
            advance(m.start(0))
            if m[0] in ["'", '"']:
                parse_string(in_line[in_end])
            elif m[0] == '//':
                parse_line_comment()
            elif m[0] == '/*':
                parse_block_comment()
            elif m[0] == '{':
                env.push_scope()
            elif m[0] == '}':
                env.pop_scope()
            elif m[0] == '/*$':
                parse_directive()
        else:
            advance_line()
    return True

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

    for filename in args.files:
        in_path = os.path.join(args.in_dir, filename)
        out_path = os.path.join(args.out_dir, filename)
        if should_preprocess(in_path, out_path, args.build):
            try:
                atomic_streamed_file_process(in_path, out_path, preprocess)
            except PreprocessException as e:
                log.error(e)
        else:
            log.verbose(f'Skipping "{filename}"; it is already up-to-date.')
