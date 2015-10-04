#!/usr/bin/python

import fileinput
import re
import subprocess
import sys

IGNORED_FUNCS = [
        'dump\w*',
        'print\w*',
]

DEBUG_MACROS = [
        'DEBUG',
        '_DEBUG',
]

DEBUG_CONDITIONS = [
        'debug\w*\.isEnabled\s*\([\w\s]*\)\s*',
]

def log(msg):
    print >> sys.stderr, '[lcov post-process] ' + msg

def combine_regex(parts):
    regex = '('
    first = True
    for part in parts:
        if first:
            first = False
        else:
            regex += '|'
        regex += '(' + part + ')'
    return regex + ')'

IGNORED_FUNC_PATTERN = re.compile(r'(\W+::)*' + combine_regex(IGNORED_FUNCS) + '\s*\Z')
DEBUG_PATTERN        = re.compile(r'\A\s*' + combine_regex(DEBUG_MACROS) + '\s*');
CONDITION_PATTERN    = re.compile(r'\bif\s*\(\s*' + combine_regex(DEBUG_CONDITIONS) + '\s*\)\s*\{')
TRAILING_PATTERN     = re.compile(r'[;\s]*\Z')

def demangle_name(func_name):
    demangled = subprocess.check_output(['c++filt', func_name])
    return demangled.split(':')[-1].split('(')[0].split()[0]

def excluded(lines, pattern, lparen, rparen):
    excluded_ranges = []
    line_no = 1
    open_paren_stack = -1
    current_range_start = -1
    for line in lines:
        col = 0
        if current_range_start == -1:
            # not currently in a DEBUG, search for one in this line
            match = pattern.search(line)
            if match:
                current_range_start = line_no
                col = match.end() - 1
        if current_range_start != -1:
            # currently in a DEBUG
            while col < len(line):
                if line[col] == lparen:
                    open_paren_stack += 1
                elif line[col] == rparen:
                    if open_paren_stack == -1:
                        # shouldn't happen, give up
                        break
                    elif open_paren_stack == 0:
                        # found the end of the DEBUG
                        if TRAILING_PATTERN.match(line, col + 1):
                            excluded_ranges.append((current_range_start, line_no + 1))
                        current_range_start = -1
                        open_paren_stack = -1
                        break
                    else:
                        open_paren_stack -= 1
                col += 1
        line_no += 1
    return excluded_ranges

def get_excluded_lines_from_source(file_name):
    excluded_ranges = []
    with open(file_name) as f:
        lines = list(f.readlines())
        excluded_ranges += excluded(lines, DEBUG_PATTERN, '(', ')')
        excluded_ranges += excluded(lines, CONDITION_PATTERN, '{', '}')
    if excluded_ranges:
        log('excluding ranges in ' + file_name + ': ' + str(excluded_ranges))
    return excluded_ranges

def process_lcov(in_file, out_file):
    for line in in_file.readlines():
        output_line = True
        if line.startswith('SF:'):
            # start of source file
            file_name = line[len('SF:'):].split()[0]
            excluded_ranges = get_excluded_lines_from_source(file_name)
            removed_funcs = 0
            removed_funcs_hit = 0
            removed_lines = 0
            removed_lines_hit = 0
            removed_branches = 0
            removed_branches_hit = 0
        elif line.startswith('FN:'):
            # function
            line_no = int(line[len('FA:'):].split(',')[0])
            func_name = line.split(',')[-1].split()[0]
            basic_name = demangle_name(func_name)
            if IGNORED_FUNC_PATTERN.match(basic_name):
                if not excluded_ranges or excluded_ranges[-1][1] != -1:
                    excluded_ranges.append((line_no, -1))
                output_line = False
            else:
                if excluded_ranges and excluded_ranges[-1][1] == -1:
                    excluded_ranges[-1] = (excluded_ranges[-1][0], line_no)
                    log('excluding ranges in ' + file_name + ': ' + str(excluded_ranges[-1]))
        elif line.startswith('FNDA:'):
            # function coverage
            func_name = line.split(',')[-1].split()[0]
            basic_name = demangle_name(func_name)
            func_hit = line[len('FNDA:'):].split(',')[0] == '1'
            if IGNORED_FUNC_PATTERN.match(basic_name):
                output_line = False
                removed_funcs += 1
                if func_hit:
                    removed_funcs_hit += 1
        elif line.startswith('FNF:'):
            # functions found
            funcs = int(line.split(':')[1])
            line = 'FNF:' + str(funcs - removed_funcs) + '\n'
        elif line.startswith('FNH:'):
            # functions hit
            funcs = int(line.split(':')[1])
            line = 'FNH:' + str(funcs - removed_funcs_hit) + '\n'
        elif line.startswith('BRDA:'):
            # branch coverage
            line_no = int(line[len('BRDA:'):].split(',')[0])
            branch_hit = line.split(',')[-1] not in ['0', '-']
            for ex_range in excluded_ranges:
                if ex_range[0] <= line_no and \
                        (ex_range[1] == -1 or line_no < ex_range[1]):
                    output_line = False
                    removed_branches += 1
                    if branch_hit:
                        removed_branches_hit += 1
                    break
        elif line.startswith('BRF:'):
            # branches found
            branches = int(line.split(':')[1])
            line = 'BRF:' + str(branches - removed_branches) + '\n'
        elif line.startswith('BRH:'):
            # branches hit
            branches = int(line.split(':')[1])
            line = 'BRH:' + str(branches - removed_branches_hit) + '\n'
        elif line.startswith('DA:'):
            # line coverage
            line_no = int(line[len('DA:'):].split(',')[0])
            line_hit = line.split(',')[-1] == '1'
            for ex_range in excluded_ranges:
                if ex_range[0] <= line_no and \
                        (ex_range[1] == -1 or line_no < ex_range[1]):
                    output_line = False
                    removed_lines += 1
                    if line_hit:
                        removed_lines_hit += 1
                    break
        elif line.startswith('LF:'):
            # lines found
            lines = int(line.split(':')[1])
            line = 'LF:' + str(lines - removed_lines) + '\n'
        elif line.startswith('LH:'):
            # lines hit
            lines = int(line.split(':')[1])
            line = 'LH:' + str(lines - removed_lines_hit) + '\n'

        if output_line:
            out_file.write(line)

subprocess.check_call(['lcov', '--capture', '--rc', 'lcov_branch_coverage=1', '--directory', '.', '--output-file', 'lcov.info'])
with open('lcov.info', 'r') as in_file:
    with open('lcov.trimmed.info', 'w') as out_file:
        process_lcov(in_file, out_file)
subprocess.check_call(['genhtml', 'lcov.trimmed.info', '--rc', 'lcov_branch_coverage=1', '--output-directory', 'coverage'])
