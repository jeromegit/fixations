#!/usr/bin/env python3

import argparse
import fileinput

from tabulate import tabulate, SEPARATING_LINE

from fixations.fix_utils import extract_fix_lines_from_str_lines, create_fix_lines_grid, \
    DEFAULT_FIX_VERSION, FIX_TAG_ID_SENDER_COMP_ID, FIX_TAG_ID_TARGET_COMP_ID


def extract_fix_lines_from_files(files):
    str_fix_lines = []
    for line in fileinput.input(files):
        str_fix_lines.append(line)

    return extract_fix_lines_from_str_lines(str_fix_lines)


def parse_args():
    ap = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument('-f', '--fix_version', type=str, nargs='?', const=1, default=DEFAULT_FIX_VERSION,
                    help="FIX version to be used")
    ap.add_argument('-g', '--grid_style', type=str, nargs='?', default='psql',
                    help="Grid/Tabulate grid style.\n"
                         "See 'Table format' section in https://github.com/astanin/python-tabulate")
    ap.add_argument('fix_files', nargs='*')

    return ap.parse_args()


def main():
    cli_args = parse_args()
    files_to_parse = cli_args.fix_files

    fix_tag_dict, fix_lines, used_fix_tags = extract_fix_lines_from_files(files_to_parse)
    if len(used_fix_tags) == 0:
        print("Could not find FIX lines.")
        exit(1)

    top_header_tags = [FIX_TAG_ID_SENDER_COMP_ID, FIX_TAG_ID_TARGET_COMP_ID]
    headers, rows = create_fix_lines_grid(fix_tag_dict, fix_lines, used_fix_tags, top_header_tags=top_header_tags)
    rows.insert(len(top_header_tags), SEPARATING_LINE)
    tablefmt = cli_args.grid_style
    print(tabulate(rows, headers=headers, stralign='left', tablefmt=tablefmt))


if __name__ == '__main__':
    main()
