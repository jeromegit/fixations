#!/usr/bin/env python3

import re
import sys

from tabulate import tabulate

from fix_utils import extract_tag_dict_for_fix_version, FIX_TAG_ID_SENDING_TIME

fix_tag_dict = extract_tag_dict_for_fix_version()


def parse_fix_line_into_kvs(line):
    fix_start = line.find('8=FIX')
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

log_file_path = sys.argv[1]
used_fix_tags = {}
tag_lines = []
with open(log_file_path) as log_fd:
    for line in log_fd.readlines():
        fix_tags = parse_fix_line_into_kvs(line.strip())
        if FIX_TAG_ID_SENDING_TIME in fix_tags:
            time = fix_tags[FIX_TAG_ID_SENDING_TIME]
            for fix_tag_key in fix_tags.keys():
                used_fix_tags[fix_tag_key] = 1
            tag_lines.append(fix_tags)
        else:
            print(f"ERROR: FIX line w/o SENDING_TIME tag(52): {line}")


rows = []
for fix_tag in ('49', '56', *sorted(used_fix_tags, key=lambda k: int(k))):
    if fix_tag in fix_tag_dict:
        fix_tag_name = fix_tag_dict[fix_tag].name
    else:
        fix_tag_name = '???'
    cols = [fix_tag, fix_tag_name]
    for fix_tags in tag_lines:
        value = fix_tags[fix_tag] if fix_tag in fix_tags else ''
        cols.append(value)
    rows.append(cols)
headers = ['TAG_ID', 'TAG_NAME']
for fix_tags in tag_lines:
    time = fix_tags[FIX_TAG_ID_SENDING_TIME]
    headers.append(time)

print(tabulate(rows, headers=headers, stralign='left', tablefmt='psql'))




