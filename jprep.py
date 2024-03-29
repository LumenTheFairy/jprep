#!/usr/bin/env python

"""
A very basic JavaScript/TypeScript preprocessor.

Written by TheOnlyOne (@modest_ralts, https://github.com/LumenTheFairy).
"""

# Constants
DEFAULT_IN_DIR = "./"
DEFAULT_OUT_DIR = "./preprocessed/"

ID_CH = r'[\w$]'


import argparse
from sys import stderr
import os
from stat import S_IREAD, S_IRGRP, S_IROTH, S_IWUSR
import re
from enum import Enum, auto

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
        "-r", "--readonly",
        action="store_true",
        help='preprocessed files will be saved in readonly mode, to help prevent accidental edits'
        )
    parser.add_argument(
        "-c", "--configuration",
        default=None,
        help=f'configuration file which holds definitions that stay in scope for all preprocessed files'
        )
    parser.add_argument(
        "-b", "--build_off",
        action="store_true",
        help="only preprocess files that can be determined to need preprocessing"
        )
    parser.add_argument(
        "-s", "--strict_define",
        action="store_true",
        help="makes it an error for a define to have no value or a condition not to check against a value, or when a condition uses a value that has not been defined in the current scope"
        )
    parser.add_argument("--verbose", action="store_true", help="display additional information during preprocessing")

    # Print version
    parser.add_argument("-v", "--version", action="version", version='%(prog)s - Version 1.0')

    # Parse arguments
    return parser.parse_args()

EXIT_CODE = 0

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
        if os.path.exists(out_path):
            os.chmod(out_path, S_IWUSR|S_IREAD)
        try:
            os.replace(out_path + '.temp', out_path)
        finally:
            if args.readonly:
                os.chmod(out_path, S_IREAD|S_IRGRP|S_IROTH)
    else:
        os.remove(out_path + '.temp')

def should_preprocess(in_path, out_path, config_path, full_build):
    """Determines if a file should be preprocessed.
A file should be preprocessed for any of the following reasons:
- We are doing a full build
- The file has never been preprocessed before
- The file has been modified since the last time it was preprocessed
- The config file has been modified since the last run
- This script has been modified since the last time it ran"""
    if full_build:
        return True
    if not os.path.exists(out_path):
        return True
    if os.path.getmtime(in_path) > os.path.getmtime(out_path):
        return True
    if os.path.getmtime(__file__) > os.path.getmtime(out_path):
        return True
    if config_path and (os.path.getmtime(config_path) > os.path.getmtime(out_path)):
        return True
    return False

class PreprocessException(Exception):
    """An exception thrown by preprocess which indicates a parse error that should be reported"""
    def __init__(self, message, local_vars):
        self.message = message
        self.l = local_vars
    def __str__(self):
        if self.l.scan == 0:
            return f'{self.message}\nLine {self.l.prev_line_num}: {self.l.prev_line}'
        else:
            return f'{self.message}\nLine {self.l.line_num}: {self.l.in_line}'
    __repr__ = __str__

class DefinitionEntry:
    """Holds the value and possible choices for a defined name"""
    def __init__(self, value, choices):
        self.value = value
        self.choices = choices

class IfState(Enum):
    If = auto()
    ElseIf = auto()
    Else = auto()

class IfEntry:
    """Holds info about the current if directives"""
    def __init__(self, scope_depth):
        self.state = IfState.If
        self.seen_true = False
        self.in_true = False
        self.scope_depth = scope_depth

class ParsingEnvironment:
    """Holds all definitions in a stack of scopes, and keeps track of nested if directives"""

    def push_scope(self):
        """Enter a new scope"""
        self.scopes.append({})

    def pop_scope(self, ends_branch=False):
        """Leave the current scope"""
        if ((not ends_branch
            and self.in_if()
            and len(self.scopes) <= self.get_if_starting_scope_depth())
        or len(self.scopes) <= 1):
            raise PreprocessException('Attempted to leave final scope.', self.l)
        self.scopes.pop()

    def define(self, name, value=None, choices=None):
        """Adds or overwrites the definition of name in the current scope"""
        self.scopes[-1][name] = DefinitionEntry(value, choices)

    def undefine(self, name):
        """Removes a definition of name from the current scope"""
        if name not in self.scopes[-1]:
            raise PreprocessException(f'Cannot undefine "{name}"; it does not exist in the current scope.', self.l)
        del self.scopes[-1][name]

    def lookup(self, name):
        """Gets the entry for the most deeply nested definition of name, if there are any"""
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def get_scope_depth(self):
        return len(self.scopes)

    def get_if_depth(self):
        return len(self.if_stack)

    def push_if(self):
        """Enter a new if directive"""
        self.if_stack.append(IfEntry(len(self.scopes)))

    def pop_if(self):
        """Leave the current if directive"""
        self.if_stack.pop()

    def in_if(self):
        return bool(self.if_stack)

    def set_if_branch(self, flag):
        """Set the current if directive's truthfulness"""
        self.if_stack[-1].in_true = flag
        self.if_stack[-1].seen_true |= flag

    def set_if_state(self, state):
        self.if_stack[-1].state = state

    def get_if_state(self):
        return self.if_stack[-1].state

    def get_seen_true(self):
        return self.if_stack[-1].seen_true

    def get_in_true(self):
        for entry in self.if_stack:
            if not entry.in_true:
                return False
        return True

    def get_if_starting_scope_depth(self):
        return self.if_stack[-1].scope_depth

    def __init__(self):
        self.scopes = []
        self.if_stack = []
        self.push_scope()
        self.l = None

    @classmethod
    def from_base_env(cls, env):
        result = cls()
        result.scopes = env.scopes
        return result

# precompiled regexes
whitespace_re = re.compile(r'(?!\s)')
identifier_re = re.compile(ID_CH + '+' + r'(?!' + ID_CH + ')')
string_re = {}
string_re["'"] = re.compile(r"(?<!\\)'")
string_re['"'] = re.compile(r'(?<!\\)"')
end_comment_re = re.compile(r'\*/')
template_literal_re = re.compile(r'(?<!\\)`|(?<!\\)\$\{')
main_loop_re = re.compile(r'/\*\$|"|\'|//|/\*|\{|\}|`')


def same_text(s1, s2):
    """True if both strings are the same, ignoring case."""
    # note, unicodedata.normalize is a good idea to get this to work all the time,
    # but this is only used here to compare against our simple directive names
    return s1.casefold() == s2.casefold()

def do_preprocess(in_file, out_file, env):

    global EXIT_CODE

    class ParseMode(Enum):
        Output = auto()
        Skip = auto()

    # black python magic
    # will make it so the print(l) prints all local variables
    from itertools import chain
    class Debug(type):
      def __str__(self):
        return '\n'.join(
            ['preprocess local variables:'] + [
            f'  {var} = {val!r}'
            for (var, val)
             in chain(self.__dict__.items(),
                {'in_line[scan:]': self.in_line[self.scan:]}.items())
             if not var.startswith('__')
            ])
      __repr__ = __str__

    # This is a bit of an ugly trick to avoid putting 'nonlocal' in any nested functions
    # that only write to these (which I find easy to forget, and hard to track down; not a good combination)
    class LocalVariables(metaclass=Debug):
        # holds the line that was most recently read from in_file
        in_line = ''
        # current line number in in_file; 1 based
        line_num = 0
        # all characters in in_line before emit have been written to out_line or have been skipped
        emit = 0
        # all characters in in_line before scan have been parsed
        scan = 0
        # holds any partial line output. This is only written to if part of the line is skipped;
        # if emit is 0 at the end of a line, in_line can be written directly to out_file
        out_line = ''
        # current parse mode
        parse_mode = ParseMode.Output
        # for error reporting...
        prev_line = ''
        prev_line_num = 0
    l = LocalVariables

    env.l = l

    mode_stack = []
    # holds the scope depth at each template level
    template_literal_stack = []

    def push_mode(mode):
        mode_stack.append(l.parse_mode)
        l.parse_mode = mode

    def pop_mode():
        l.parse_mode = mode_stack.pop()

    #----------------------------------------------------------------------------------------------
    # Handle input and output and line transitions
    def read_line():
        l.prev_line = l.in_line
        l.prev_line_num = l.line_num
        l.in_line = in_file.readline()
        l.line_num += 1
        l.emit = 0
        l.scan = 0
        l.out_line = ''

    def write_output():
        if l.emit == 0:
            out_file.write(l.in_line)
        else:
            output = l.out_line + l.in_line[l.emit:]
            if not output.isspace():
                out_file.write(l.out_line + l.in_line[l.emit:])

    def append_output():
        l.out_line += l.in_line[l.emit:l.scan]
        l.emit = l.scan

    def move_to_next_line_if_necessary():
        if l.scan > len(l.in_line):
            raise Exception('Internal error')
        if l.in_line[l.scan:] == '\n' or l.in_line[l.scan:] == '':
            write_output()
            read_line()

    #----------------------------------------------------------------------------------------------
    # Parsing utility
    def parse_any(count=1):
        if l.parse_mode == ParseMode.Skip:
            append_output()
            l.emit = l.scan + count
        l.scan += count
        move_to_next_line_if_necessary()

    def parse_line():
        if l.parse_mode == ParseMode.Skip:
            l.emit = len(l.in_line) - 1
        l.scan = len(l.in_line) - 1
        move_to_next_line_if_necessary()

    def parse_until(regex):
        m = None
        while not m and l.in_line:
            m = regex.search(l.in_line[l.scan:])
            if m:
                parse_any(m.end(0))
            else:
                parse_line()

    #----------------------------------------------------------------------------------------------
    # Error reporting
    def report_error(message):
        raise PreprocessException(message, l)

    def report_choice_inclusion_error(name, value, choices):
        choices_format = ", ".join(map(lambda c: f'"{c}"', choices))
        report_error(f'"{value}" is not one of the required choices for "{name}": [{choices_format}]')

    #----------------------------------------------------------------------------------------------
    # Parsing atoms
    def try_parse_chars(s):
        if l.in_line[l.scan:].startswith(s):
            parse_any(len(s))
            return True
        return False

    def parse_chars(s, error_message):
        if not try_parse_chars(s):
            report_error(error_message)

    def try_parse_identifier():
        m = identifier_re.match(l.in_line[l.scan:])
        if not m:
            return None
        parse_any(m.end(0))
        return m[0]

    def parse_identifier(error_message):
        result = try_parse_identifier()
        if not result:
            report_error(error_message)
        return result

    def parse_whitespace():
        parse_until(whitespace_re)

    def parse_string(quote):
        parse_any(1)
        parse_until(string_re[quote])

    def parse_line_comment():
        parse_line()

    def parse_block_comment():
        parse_until(end_comment_re)

    def parse_template_literal():
        parse_any(1)
        parse_until(template_literal_re)
        if l.in_line[l.scan-1] != '`':
            template_literal_stack.append([env.get_scope_depth(), env.get_if_depth])

    #----------------------------------------------------------------------------------------------
    # Parsing directives
    def parse_note():
        parse_until(end_comment_re)

    def parse_define():
        name = parse_identifier('Expected a name at the beginning of the "define" directive.')
        parse_whitespace()
        value = None
        choices = None
        if try_parse_chars('='):
            parse_whitespace()
            value = parse_identifier('Expected a value after "=" in the "define" directive.')
            parse_whitespace()
        if try_parse_chars('<'):
            choices = []
            while True:
                parse_whitespace()
                choice = try_parse_identifier()
                if choice:
                    choices.append(choice)
                elif not choices:
                    report_error('There must be at least one choice after "<" in the "define" directive.')
                parse_whitespace()
                if not try_parse_chars(','):
                    break

        parse_whitespace()
        if not try_parse_chars('*/'):
            report_error('Only whitespace allowed at the end of a "define" directive.')

        if args.strict_define and not value:
            report_error('definitions must set a value when using --strict_define')

        old_definition = env.lookup(name)
        if old_definition:
            if old_definition.choices:
                if choices:
                    report_error(f'"{name}" already has a set of choices.')
                else:
                    choices = old_definition.choices

        if choices:
            if not value:
                report_error('A value must be given for a definition with choices.')
            if value not in choices:
                report_choice_inclusion_error(name, value, choices)
        env.define(name, value, choices)

    def parse_undefine():
        name = parse_identifier('Expected a name at the beginning of the "undefine" directive.')
        parse_whitespace()
        if not try_parse_chars('*/'):
            report_error(f'Only whitespace allowed at the end of a "{directive}" directive.')
        env.undefine(name)

    def parse_condition(directive):
        name = parse_identifier(f'Expected a name at the beginning of the "{directive}" directive.')
        parse_whitespace()
        value = None
        if try_parse_chars('='):
            parse_whitespace()
            value = parse_identifier(f'Expected a value after "=" in the "{directive}" directive.')
            parse_whitespace()
        if not try_parse_chars('*/'):
            report_error(f'Only whitespace allowed at the end of a "{directive}" directive.')
        return [name, value]

    def get_branch_parse_mode():
        if env.get_in_true():
            return ParseMode.Output
        else:
            return ParseMode.Skip

    def parse_if():
        [name, value] = parse_condition('if')

        definition = env.lookup(name)
        env.push_scope()
        env.push_if()
        if not definition:
            if args.strict_define:
                report_error('condition value must be defined when using --strict_define')
            env.set_if_branch(False)
        else:
            if args.strict_define and not value:
                report_error('condtion must test against a value when using --strict_define')
            if definition.choices and not value in definition.choices: # False even if value is None
                report_choice_inclusion_error(name, value, definition.choices)
            if definition.value == value:
                env.set_if_branch(True)
            else:
                env.set_if_branch(False)

        return get_branch_parse_mode()

    def parse_elseif():
        if not env.in_if():
            report_error('"elseif" directive outside of "if".')
        if env.get_scope_depth() != env.get_if_starting_scope_depth():
            report_error('if branches must have the same scopes at the start and end.')
        if env.get_if_state() == IfState.Else:
            report_error('"elseif" directive after "else".')

        [name, value] = parse_condition('elseif')
        pop_mode()

        definition = env.lookup(name)
        env.set_if_state(IfState.ElseIf)
        env.pop_scope(True)
        env.push_scope()
        if not definition:
            env.set_if_branch(False)
        else:
            if definition.choices and not value in definition.choices: # False even if value is None
                report_choice_inclusion_error(name, value, definition.choices)
            if env.get_seen_true():
                env.set_if_branch(False)
            elif definition.value == value:
                env.set_if_branch(True)
            else:
                env.set_if_branch(False)

        return get_branch_parse_mode()

    def parse_else():
        if not env.in_if():
            report_error('"else" directive outside of "if".')
        if env.get_scope_depth() != env.get_if_starting_scope_depth():
            report_error('if branches must have the same scopes at the start and end.')
        if env.get_if_state() == IfState.Else:
            report_error('"else" directive after "else".')

        parse_whitespace()
        if not try_parse_chars('*/'):
            report_error('Only whitespace allowed at the end of a "else" directive.')
        pop_mode()

        env.set_if_state(IfState.Else)
        env.pop_scope(True)
        env.push_scope()
        env.set_if_branch(not env.get_seen_true())

        return get_branch_parse_mode()

    def parse_fi():
        if not env.in_if():
            report_error('"fi" directive outside of "if".')
        if env.get_scope_depth() != env.get_if_starting_scope_depth():
            report_error('if branches must have the same scopes at the start and end.')

        parse_whitespace()
        if not try_parse_chars('*/'):
            report_error('Only whitespace allowed at the end of a "fi" directive.')
        pop_mode()

        env.pop_if()
        env.pop_scope(True)

    def parse_directive():
        result = False
        new_mode = None
        push_mode(ParseMode.Skip)
        parse_any(3)
        parse_whitespace()
        directive = parse_identifier('Directives must start with an identifier.')
        parse_whitespace()

        if same_text(directive, 'note'):
            parse_note()
        elif same_text(directive, 'define'):
            parse_define()
        elif same_text(directive, 'undefine'):
            parse_undefine()
        elif same_text(directive, 'if'):
            new_mode = parse_if()
        elif same_text(directive, 'elseif'):
            new_mode = parse_elseif()
        elif same_text(directive, 'else'):
            new_mode = parse_else()
        elif same_text(directive, 'fi'):
            parse_fi()
        else:
            report_error(f'"{directive}"" is not a recognized directive.')

        pop_mode()
        if new_mode:
            push_mode(new_mode)
        return result

    def handle_close_brace():
        if template_literal_stack and (template_literal_stack[-1][0] == env.get_scope_depth()):
            if env.in_if() and (env.get_if_depth != template_literal_stack[-1][1]):
                report_error('Reached the end of a template expression in the middle of an if directive branch.')
            template_literal_stack.pop()
            parse_template_literal()
        else:
            env.pop_scope()
            parse_any(1)


    def parse_file():
        while l.in_line:
            m = main_loop_re.search(l.in_line[l.scan:])
            if m:
                parse_any(m.start(0))
                if m[0] in ["'", '"']:
                    parse_string(l.in_line[l.scan])
                elif m[0] == '`':
                    parse_template_literal()
                elif m[0] == '//':
                    parse_line_comment()
                elif m[0] == '/*':
                    parse_block_comment()
                elif m[0] == '{':
                    env.push_scope()
                    parse_any(1)
                elif m[0] == '}':
                    handle_close_brace()
                elif m[0] == '/*$':
                    parse_directive()
            else:
                parse_line()


    try:
        read_line()
        parse_file()
        if env.in_if():
            report_error('Reached the end of the file in the middle of an if directive branches.')
    except PreprocessException as e:
        log.error(e)
        EXIT_CODE = -1
        return False
    return True

global_env = ParsingEnvironment()

def show_global_env():
    return '\n'.join(
        ['Configuration:'] + [
        f'  {name} = {entry.value}'
        for (name, entry)
         in global_env.scopes[0].items()
        ])

def preprocess(in_file, out_file):
    return do_preprocess(in_file, out_file, ParsingEnvironment.from_base_env(global_env))

def preprocess_config(config_path):
    class NullOut():
        def write(self, s):
            pass

    out_file = NullOut()

    with open(config_path, 'r') as in_file:
        return do_preprocess(in_file, out_file, global_env)

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

    # Read configuration file if there is one
    if args.configuration:
        preprocess_config(args.configuration)
        log.verbose(show_global_env())

    for filename in args.files:
        in_path = os.path.join(args.in_dir, filename)
        out_path = os.path.join(args.out_dir, filename)
        if should_preprocess(in_path, out_path, args.configuration, not args.build_off):
            atomic_streamed_file_process(in_path, out_path, preprocess)
            log.verbose(f'Preprocessed "{filename}".')
        else:
            log.verbose(f'Skipping "{filename}"; it is already up-to-date.')

    exit(EXIT_CODE)
