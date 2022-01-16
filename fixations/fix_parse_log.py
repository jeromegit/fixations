#!/usr/bin/env python3

import argparse
import fileinput
import re

from tabulate import tabulate

from fixations.fix_utils import extract_tag_dict_for_fix_version, FIX_TAG_ID_SENDING_TIME, FIX_TAG_ID_SENDER_COMP_ID, \
    FIX_TAG_ID_TARGET_COMP_ID, DEFAULT_FIX_VERSION


def parse_fix_line_into_kvs(line):
    fix_start = line.find('8=FIX')
    if fix_start == -1:
        return None
    fix_line = line[fix_start:]
    body_length_start = fix_line.find('9=')
    separator = fix_line[body_length_start - 1]
    kv_parts = fix_line.split(separator)
    kvs = {}
    for kv_part in kv_parts:
        if kv_part:
            kv = re.search("^(\d+)=(.*)", kv_part)
            if kv:
                tag_id, value = kv.group(1, 2)
                if tag_id in fix_tag_dict and value in fix_tag_dict[tag_id].values:
                    value = f"{value} ({fix_tag_dict[tag_id].values[value].name})"
                kvs[tag_id] = value
            else:
                print(f"ERROR: can't break:{kv_part} into key=value")
    #    print(f"{fix_line}:\n\t{kvs}")
    return kvs


def extract_fix_lines_from_files(files):
    used_fix_tags = {}
    fix_lines = []
    for line in fileinput.input(files):
        fix_tags = parse_fix_line_into_kvs(line.strip())
        if fix_tags:
            if FIX_TAG_ID_SENDING_TIME in fix_tags:
                for fix_tag_key in fix_tags.keys():
                    used_fix_tags[fix_tag_key] = 1
                fix_lines.append(fix_tags)
            else:
                print(f"ERROR: FIX line w/o SENDING_TIME tag(52): {line}")

    return fix_lines, used_fix_tags


def create_fix_lines_grid(fix_lines, used_fix_tags):
    rows = []
    for fix_tag in (FIX_TAG_ID_SENDER_COMP_ID, FIX_TAG_ID_TARGET_COMP_ID, *sorted(used_fix_tags, key=lambda k: int(k))):
        if fix_tag in fix_tag_dict:
            fix_tag_name = fix_tag_dict[fix_tag].name
        else:
            fix_tag_name = '???'
        cols = [fix_tag, fix_tag_name]
        for fix_tags in fix_lines:
            value = fix_tags[fix_tag] if fix_tag in fix_tags else ''
            cols.append(value)
        rows.append(cols)
    headers = ['TAG_ID', 'TAG_NAME']
    for fix_tags in fix_lines:
        time = fix_tags[FIX_TAG_ID_SENDING_TIME]
        headers.append(time)

    return headers, rows


def parse_args():
    ap = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument('-f', '--fix_version', type=str, nargs='?', const=1, default=DEFAULT_FIX_VERSION,
                    help="FIX version to be used")
    ap.add_argument('-g', '--grid_style', type=str, nargs='?', default='psql',
                    help="Grid/Tabulate grid style.\n"
                         "See 'Table format' section in https://github.com/astanin/python-tabulate")
    ap.add_argument('fix_files', nargs='*')

    return ap.parse_args()


if __name__ == '__main__':
    cli_args = parse_args()
    files_to_parse = cli_args.fix_files
    fix_tag_dict = extract_tag_dict_for_fix_version(cli_args.fix_version)

    fix_lines, used_fix_tags = extract_fix_lines_from_files(files_to_parse)
    if len(used_fix_tags) == 0:
        print("Could not find FIX lines.")
        exit(1)

    headers, rows = create_fix_lines_grid(fix_lines, used_fix_tags)
    tablefmt = cli_args.grid_style
    print(tabulate(rows, headers=headers, stralign='left', tablefmt=tablefmt))
