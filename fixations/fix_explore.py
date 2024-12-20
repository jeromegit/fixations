#!/usr/bin/env python3
import argparse
import json
import sys
from dataclasses import dataclass
from typing import Dict, List, Tuple, Union, Set

from tabulate import tabulate

from fixations.fix_utils import extract_info_for_fix_version, get_list_of_available_fix_versions, \
    FixVersionInfo, FixTag, FIX_VERSION_ALL, FixTagValueClash

TABULATE_DEFAULT_FORMAT = 'grid'


def validate_fix_versions(fix_versions_csv: str) -> List[str]:
    available_fix_versions = get_list_of_available_fix_versions()

    valid_fix_versions: List[str] = []
    invalid_versions: List[str] = []
    for fix_version in fix_versions_csv.split(','):
        if fix_version in available_fix_versions:
            valid_fix_versions.append(fix_version)
        else:
            invalid_versions.append(fix_version)

    if invalid_versions:
        print(f"Invalid specified version(s):{', '.join(invalid_versions)}. Exiting")
        exit(1)

    return valid_fix_versions


def get_tags_and_infos_for_versions(fix_versions: List[str], fix_tags: Union[None, List[str]] = None) -> Tuple[
    Dict[str, FixVersionInfo], Dict[str, FixTag]]:
    fix_tags_of_interest: Set[str] = set(fix_tags if fix_tags else [])
    fix_version_infos: Dict[str, FixVersionInfo] = {}
    all_fix_tags_across_all_versions: Dict[str, FixTag] = {}
    for fix_version in fix_versions:
        fix_version_infos[fix_version] = extract_info_for_fix_version(fix_version)
        for fix_tag in fix_version_infos[fix_version].fix_tags_by_tag_id.values():
            if not fix_tags_of_interest or fix_tag.id in fix_tags_of_interest:
                all_fix_tags_across_all_versions[fix_tag.id] = fix_tag

    return fix_version_infos, all_fix_tags_across_all_versions


def show_tags_across_versions(fix_versions: Union[None, List[str]] = None, fix_tags: Union[None, List[str]] = None,
                              grid_style: str = TABULATE_DEFAULT_FORMAT) -> None:
    if fix_versions == None:
        fix_versions = get_list_of_available_fix_versions()

    fix_version_infos, all_fix_tags_across_all_versions = get_tags_and_infos_for_versions(fix_versions, fix_tags)

    versions_for_tags: List[List[str]] = []
    for fix_tag in sorted(all_fix_tags_across_all_versions.values(), key=lambda fix_tag: int(fix_tag.id)):
        versions_for_tag: List[str] = [fix_tag.id, fix_tag.name, fix_tag.type]
        for fix_version in fix_versions:
            if fix_tag.id in fix_version_infos[fix_version].fix_tags_by_tag_id:
                values = fix_version_infos[fix_version].fix_tags_by_tag_id[fix_tag.id].values.values()
                if values:
                    value_rows = "\n".join([f"{v.value}: {v.name}" for v in sorted(values, key=lambda v: v.value)])
                else:
                    value_rows = '✅'
                versions_for_tag.append(value_rows)
            else:
                versions_for_tag.append(' ')
        versions_for_tags.append(versions_for_tag)

    print(tabulate(versions_for_tags, headers=['TAG_ID', 'NAME', 'TYPE'] + fix_versions,
                   tablefmt=grid_style))


def print_all_fix_tag_value_clashes(all_fix_tag_value_clashes: List[FixTagValueClash]) -> None:
    if len(all_fix_tag_value_clashes):
        all_fix_tag_value_clashes_rows = []
        for c in all_fix_tag_value_clashes:
            all_fix_tag_value_clashes_rows.append([c.fix_tag_id, c.value, c.name, c.fix_version, c.fix_version_name])

        print(f"\n>>>>>>>> FOUND {len(all_fix_tag_value_clashes)} clashes! <<<<<<<<", file=sys.stderr)
        print(tabulate(all_fix_tag_value_clashes_rows,
                       headers=['TAG_ID', 'VALUE', 'NAME', 'FIX_VERSION', 'FIX_VERSION_NAME'],
                       tablefmt='psql'), file=sys.stderr)


def sort_by_tag_ids_and_values(fix_tags_by_tag_id: Dict[str, FixTag]) -> Dict[str, FixTag]:
    sorted_fix_tags_by_tag_id: Dict[str, FixTag] = {}
    for fix_tag_id in sorted(fix_tags_by_tag_id, key=int):
        fix_tag = fix_tags_by_tag_id[fix_tag_id]
        fix_tag.values = {v.value: v for v in sorted(fix_tag.values.values(), key=lambda v: v.value)}
        sorted_fix_tags_by_tag_id[fix_tag_id] = fix_tag

    return sorted_fix_tags_by_tag_id


def merge_fix_versions(fix_versions: List[str]) -> Tuple[FixVersionInfo, List[FixTagValueClash]]:
    all_versions_info: FixVersionInfo = extract_info_for_fix_version(fix_versions[0])
    all_versions_info.version = FIX_VERSION_ALL
    all_fix_tag_value_clashes: List[FixTagValueClash] = []
    for fix_version in fix_versions[1:]:
        fix_version_info = extract_info_for_fix_version(fix_version)
        fix_tag_value_clashes = all_versions_info.merge_with_other_fix_version_info(fix_version_info)
        all_fix_tag_value_clashes.extend(fix_tag_value_clashes)

    all_versions_info.fix_tags_by_tag_id = sort_by_tag_ids_and_values(all_versions_info.fix_tags_by_tag_id)

    return all_versions_info, all_fix_tag_value_clashes


def generate_all_info() -> None:
    fix_versions = get_list_of_available_fix_versions(include_fix_version_1_1=False)

    all_versions_info, all_fix_tag_value_clashes = merge_fix_versions(fix_versions)
    print_all_fix_tag_value_clashes(all_fix_tag_value_clashes)

    json_str = json.dumps(all_versions_info.fix_tags_by_tag_id, default=lambda o: o.to_dict(), indent=2)
    print(json_str)


def parse_args():
    fix_versions = get_list_of_available_fix_versions()
    ap = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ap.add_argument('-f', '--fix_versions', type=str, nargs='?', const=1,
                    help=f"CSV FIX versions to be used from this list:{', '.join(fix_versions)}")
    ap.add_argument('-g', '--grid_style', type=str, nargs='?', default=TABULATE_DEFAULT_FORMAT,
                    help="Tabulate grid style.\n"
                         "See 'Table format' section in https://github.com/astanin/python-tabulate")
    ap.add_argument('-a', '--generate_all_info', action='store_true',
                    help="Generate JSON info across *all* FIX versions")
    ap.add_argument('fix_tags', nargs='*', help="Optional list of FIX tags to focus on. All by default.")

    return ap.parse_args()


def main():
    cli_args = parse_args()

    if cli_args.generate_all_info:
        generate_all_info()
    else:
        fix_versions_csv = cli_args.fix_versions
        if fix_versions_csv:
            fix_versions = validate_fix_versions(fix_versions_csv)
        else:
            fix_versions = None

        show_tags_across_versions(fix_versions, cli_args.fix_tags, cli_args.grid_style)


if __name__ == '__main__':
    main()
