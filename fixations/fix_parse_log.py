#!/usr/bin/env python3
import argparse
import fileinput
from typing import List

import requests
import tabulate

from fixations.fix_utils import DEFAULT_FIX_VERSION, CFG_UPLOAD_URL, get_cfg_value, \
    create_table_from_fix_lines
from fixations.webfix import FORM_FIX_LINES, FORM_UPLOAD

tabulate.PRESERVE_WHITESPACE = True


def extract_lines_from_files(files: List[str]) -> List[str]:
    lines = []
    for line in fileinput.input(files):
        lines.append(line)

    return lines


def upload_lines(lines: List[str]) -> None:
    upload_url = get_cfg_value(CFG_UPLOAD_URL)
    assert upload_url, f"The configuration key:{CFG_UPLOAD_URL} must be specified to be able to use the -u option"

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
    table = create_table_from_fix_lines(lines_from_files, cli_args.grid_style)
    if not table:
        print("Could not find FIX lines.")
        exit(1)
    print(table)

    if cli_args.upload:
        upload_lines(lines_from_files)


if __name__ == '__main__':
    main()
