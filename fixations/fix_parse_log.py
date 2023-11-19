#!/usr/bin/env python3
import requests

from typing import List

from fixations.fix_utils import extract_fix_lines_from_str_lines, create_fix_lines_grid, \
    DEFAULT_FIX_VERSION, FIX_TAG_ID_SENDER_COMP_ID, FIX_TAG_ID_TARGET_COMP_ID, CFG_UPLOAD_URL, get_cfg_value
from fixations.webfix import FORM_FIX_LINES, FORM_UPLOAD

import argparse
import fileinput

import tabulate

tabulate.PRESERVE_WHITESPACE = True


def extract_lines_from_files(files: List[str]) -> List[str]:
    lines = []
    for line in fileinput.input(files):
        lines.append(line)

    return lines


def upload_lines(lines: List[str]) -> None:
    upload_url = get_cfg_value(CFG_UPLOAD_URL)
    try:
        response = requests.head(upload_url)
    except requests.exceptions.ConnectionError:
        response = None
    assert response and response.status_code == 200, f"The URL:{upload_url} can't be reached!"

    response = requests.get(upload_url, params={FORM_UPLOAD: True, FORM_FIX_LINES: ''.join(lines)})

    if response.status_code == 200:
        print(response.text)


def parse_args():
    ap = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument('-f', '--fix_version', type=str, nargs='?', const=1, default=DEFAULT_FIX_VERSION,
                    help="FIX version to be used")
    ap.add_argument('-g', '--grid_style', type=str, nargs='?', default='psql',
                    help="Grid/Tabulate grid style.\n"
                         "See 'Table format' section in https://github.com/astanin/python-tabulate")
    ap.add_argument('-u', '--upload', action='store_true', help="Upload data to webfix")
    ap.add_argument('fix_files', nargs='*')

    return ap.parse_args()


def main():
    cli_args = parse_args()
    files_to_parse = cli_args.fix_files

    lines_from_files = extract_lines_from_files(files_to_parse)
    fix_tag_dict, fix_lines, used_fix_tags, _ = extract_fix_lines_from_str_lines(lines_from_files)
    if len(used_fix_tags) == 0:
        print("Could not find FIX lines.")
        exit(1)

    top_header_tags = [FIX_TAG_ID_SENDER_COMP_ID, FIX_TAG_ID_TARGET_COMP_ID]
    headers, rows = create_fix_lines_grid(fix_tag_dict, fix_lines, used_fix_tags, top_header_tags=top_header_tags)
    rows.insert(len(top_header_tags), tabulate.SEPARATING_LINE)
    tablefmt = cli_args.grid_style
    print(tabulate.tabulate(rows, headers=headers, stralign='left', tablefmt=tablefmt))

    if cli_args.upload:
        upload_lines(lines_from_files)


if __name__ == '__main__':
    main()
