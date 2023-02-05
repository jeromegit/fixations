#!/usr/bin/env python3

import configparser
import json
import os.path
import pathlib
import re
import shutil
from dataclasses import dataclass, field
from functools import cache
from typing import Dict
from xml.dom.minidom import parse

from dataclasses_json import dataclass_json

DEFAULT_FIX_VERSION = "4.2"
FIX_TAG_ID_SENDING_TIME = "52"
FIX_TAG_ID_SENDER_COMP_ID = "49"
FIX_TAG_ID_TARGET_COMP_ID = "56"
SESSION_LEVEL_TAGS = ['8', '34', '9', '10']

DEFAULT_CFG_FILE_PATH = os.environ["HOME"] + "/.fixations.ini"
DEFAULT_DATA_DIR_PATH = os.environ["HOME"] + "/.fixations"
DEFAULT_FIX_DEFINITIONS_DIR = "fix_repository_2010_edition_20200402"
FIXATION_CFG_FILE_ENV = "FIXATION_CFG_FILE"
DEFAULT_STORE_PATH = DEFAULT_DATA_DIR_PATH + '/store.db'
#
CFG_FILE_SECTION_MAIN = "main"
CFG_FILE_KEY_DATA_DIR_PATH = "data_dir_path"
CFG_FILE_KEY_FIX_DEFINITIONS_PATH = "fix_definitions_path"
CFG_FILE_KEY_FIX_VERSION = "fix_version"
CFG_FILE_KEY_STORE_PATH = "store_path"

# Global variable initialized at the bottom of this file
cfg = None


@dataclass_json
@dataclass
class FixTagValue:
    value: str
    name: str
    desc: str


@dataclass_json
@dataclass
class FixTag:
    id: str
    name: str
    type: str
    desc: str
    values: Dict[str, FixTagValue] = field(default_factory=dict)


def cfg_init():
    if not os.path.exists(DEFAULT_CFG_FILE_PATH):
        defaults_init()
    possible_cfg_files = [DEFAULT_CFG_FILE_PATH]
    if FIXATION_CFG_FILE_ENV in os.environ:
        possible_cfg_files = [os.environ[FIXATION_CFG_FILE_ENV], *possible_cfg_files]

    found_cfg_file = None
    for cfg_file in possible_cfg_files:
        if os.path.exists(cfg_file):
            found_cfg_file = cfg_file
            break
    assert found_cfg_file, \
        f"Can't find a valid config file, based on this list ofp potential files:{possible_cfg_files}."
    cfg.read(found_cfg_file)


def get_cfg_value(key, section=CFG_FILE_SECTION_MAIN):
    assert section in cfg, f"Section:{section} doesn't exist in your configuration file"
    section = cfg[section]
    if key in section:
        value = section.get(key)
    else:
        print(f"ERROR: key:{key} doesn't exist in section:{section} in your configuration file")
        value = None

    return value


def get_store_path():
    store_path = get_cfg_value(CFG_FILE_KEY_STORE_PATH)
    if store_path:
        return store_path
    else:
        return DEFAULT_STORE_PATH


def defaults_init():
    if not os.path.exists(DEFAULT_DATA_DIR_PATH):
        module_path = os.path.realpath(__file__)
        src_fix_definition_path = os.path.dirname(module_path) + "/" + DEFAULT_FIX_DEFINITIONS_DIR
        dest_fix_definition_path = DEFAULT_DATA_DIR_PATH + "/" + DEFAULT_FIX_DEFINITIONS_DIR
        assert shutil.copytree(src_fix_definition_path,
                               dest_fix_definition_path) == dest_fix_definition_path, \
            f"Can't copy FIX definitions from {src_fix_definition_path} to {dest_fix_definition_path}"

    if not os.path.exists(DEFAULT_CFG_FILE_PATH):
        fix_definition_dir = DEFAULT_DATA_DIR_PATH + "/" + DEFAULT_FIX_DEFINITIONS_DIR
        print(f"Creating default config file:{DEFAULT_CFG_FILE_PATH}... Edit the file as needed.")
        with open(DEFAULT_CFG_FILE_PATH, "w") as cfg_fd:
            cfg_fd.writelines(line + "\n" for line in [f"[{CFG_FILE_SECTION_MAIN}]",
                                                       f"{CFG_FILE_KEY_DATA_DIR_PATH} = {DEFAULT_DATA_DIR_PATH}",
                                                       f"{CFG_FILE_KEY_FIX_DEFINITIONS_PATH} = {fix_definition_dir}",
                                                       f"{CFG_FILE_KEY_FIX_VERSION} = {DEFAULT_FIX_VERSION}",
                                                       f"{CFG_FILE_KEY_STORE_PATH} = {DEFAULT_STORE_PATH}"
                                                       ])


def get_xml_text(nodelist):
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data)
    return ''.join(rc)


def extract_tag_data_from_xml_field(field_):
    data = []
    for tag_name in ('Tag', 'Name', 'Type', 'Description'):
        value = get_xml_text(field_.getElementsByTagName(tag_name)[0].childNodes)
        data.append(value)
    return data


def extract_tag_data_from_xml_enum(enum):
    data = []
    for tag_name in ('Tag', 'SymbolicName', 'Value', 'Description'):
        value = get_xml_text(enum.getElementsByTagName(tag_name)[0].childNodes)
        data.append(value)
    return data


def path_for_fix_path(version=None, file=None):
    root_dir = get_cfg_value(CFG_FILE_KEY_FIX_DEFINITIONS_PATH)
    if version:
        path = f"{root_dir}/FIX.{version}/Base"
        if file:
            path = path + "/" + file
    else:
        path = root_dir

    return path


def get_list_of_available_fix_versions():
    root_path = path_for_fix_path()
    root_dir = pathlib.Path(root_path)
    versions = []
    for entry in root_dir.glob("FIX.*"):
        if os.path.isdir(entry):
            dir_name = os.path.basename(entry)
            version = re.search(r"FIX.(.*)", dir_name)
            versions.append(version.group(1))

    return versions


def extract_elements_from_file_by_tag_name(fix_version, file, tag_name):
    fields_file = path_for_fix_path(fix_version, file)
    doc = parse(fields_file)
    elements = doc.getElementsByTagName(tag_name)
    return elements


@cache
def extract_tag_dict_for_fix_version(fix_version=DEFAULT_FIX_VERSION):
    versions = get_list_of_available_fix_versions()
    assert fix_version in versions, f"The specified FIX version:{fix_version} is not valid. Use one of these {versions}"

    # Extract all FIX tags from Fields XML file
    fields = extract_elements_from_file_by_tag_name(fix_version, "Fields.xml", "Field")
    tag_dict_by_id = {}
    for field_ in fields:
        tag_id, name, tag_type, desc = extract_tag_data_from_xml_field(field_)
        tag_dict_by_id[tag_id] = FixTag(tag_id, name, tag_type, desc, {})

    # Extract all FIX tag values from Enums XML file and attach them to the tag dictionary
    enums = extract_elements_from_file_by_tag_name(fix_version, "Enums.xml", "Enum")
    for enum in enums:
        tag_id, name, value, desc = extract_tag_data_from_xml_enum(enum)
        fix_tag_value = FixTagValue(value, name, desc)
        if tag_id in tag_dict_by_id:
            tag_dict_by_id[tag_id].values[value] = fix_tag_value
        else:
            # Somehow the quality of the data is not that great and some enum values reference tags that don't exist
            #            print(f"ERROR: id:{id} for name:{name}, value:{value}, desc:{desc} doesn't exist")
            pass

    return tag_dict_by_id


def tag_dict_to_json(tag_dict_):
    dict_of_objects = {k: (v.to_json() if type(v) == FixTag else v) for k, v in tag_dict_.items()}
    json_object = json.dumps(dict_of_objects, indent=3)
    return json_object


def load_tag_dict_from_json_file(json_file):
    with open(json_file) as json_file_fd:
        tag_dict_ = json.load(json_file_fd)
    return tag_dict_


def save_tag_dict_to_json_file(tag_dict_, json_file):
    json_object = tag_dict_to_json(tag_dict_)
    with open(json_file, 'w') as json_file_fd:
        json_file_fd.write(json_object)


def determine_fix_version(str_fix_lines):
    for line in str_fix_lines:
        match = re.search(r"8=FIX\.([.0-9]+)", line)
        if match:
            version = match.group(1)
            return version

    return None


def get_fix_tag_dict_for_lines(str_fix_lines):
    version = determine_fix_version(str_fix_lines)
    assert version, "ERROR: can't extract FIX version from lines starting with line:{str_fix_lines[0]}"
    fix_tag_dict = extract_tag_dict_for_fix_version(version)

    return fix_tag_dict


def parse_fix_line_into_kvs(line, fix_tag_dict):
    match = re.search(r"8=FIX\.([.0-9]+)", line)
    if not match:
        return None

    fix_start, fix_end = match.span()
    body_length_start = line.find('9=')
    separator = line[fix_end:body_length_start]

    fix_line = line[fix_start:]
    kv_parts = fix_line.split(separator)
    kvs = {}
    for kv_part in kv_parts:
        if kv_part:
            kv = re.search(r"^(\d+)=(.*)", kv_part)
            if kv:
                tag_id, value = kv.group(1, 2)
                if tag_id in fix_tag_dict and value in fix_tag_dict[tag_id].values:
                    value = f"{value} ({fix_tag_dict[tag_id].values[value].name})"
                kvs[tag_id] = value
            else:
                print(f"ERROR: can't tokenize:'{kv_part}' into a key=value pair using separator:'{separator}'")
    #    print(f"{fix_line}:\n\t{kvs}")
    return kvs


def extract_version_from_first_fix_line(str_fix_lines):
    for line in str_fix_lines:
        if len(line.strip()) > 0:
            version = determine_fix_version(str_fix_lines)
            return version

    return None


def extract_timestamp(line, fix_tags=None):
    # assume that the there's a timestamp before the beginning of the FIX k/v tags
    match = re.search(r"(\d*\d:\d\d:\d\d[,.0-9]*).*8=FIX\.\d+", line)
    if match:
        return match.group(1), None
    else:
        if fix_tags and FIX_TAG_ID_SENDING_TIME in fix_tags:
            return fix_tags[FIX_TAG_ID_SENDING_TIME], None
        else:
            error = f"ERROR: FIX line w/o timestamp and SENDING_TIME tag{FIX_TAG_ID_SENDING_TIME}: {line}"
            return None, error


def extract_fix_lines_from_str_lines(str_fix_lines):
    if len(str_fix_lines):
        version = extract_version_from_first_fix_line(str_fix_lines)
        if version:
            fix_tag_dict = extract_tag_dict_for_fix_version(version)
            used_fix_tags = {}
            fix_lines = []
            for line in str_fix_lines:
                fix_tags = parse_fix_line_into_kvs(line.strip(), fix_tag_dict)
                if fix_tags:
                    timestamp, error = extract_timestamp(line, fix_tags)
                    if timestamp:
                        for fix_tag_key in fix_tags.keys():
                            used_fix_tags[fix_tag_key] = 1
                        fix_lines.append((timestamp, fix_tags))
                    else:
                        print(error)

            return fix_tag_dict, fix_lines, used_fix_tags

    return {}, [], {}


def create_header_for_fix_lines(fix_lines, show_date):
    headers = ['TAG_ID', 'TAG_NAME']
    for (timestamp, fix_tags) in fix_lines:
        if show_date is False:
            timestamp = remove_date_from_datetime(timestamp)
        headers.append(timestamp)

    return headers


def create_fix_lines_grid(fix_tag_dict, fix_lines, used_fix_tags,
                          with_session_level_tags=True, top_header_tags=[], show_date=False):
    rows = []
    for fix_tag in (*top_header_tags, *sorted(used_fix_tags, key=lambda k: int(k))):
        if fix_tag in SESSION_LEVEL_TAGS and with_session_level_tags is False:
            continue
        if fix_tag in fix_tag_dict:
            fix_tag_name = fix_tag_dict[fix_tag].name
        else:
            fix_tag_name = '???'
        cols = [fix_tag, fix_tag_name]
        for (timestamp, fix_tags) in fix_lines:
            value = fix_tags[fix_tag] if fix_tag in fix_tags else ''
            if 'time' in fix_tag_name.lower() and show_date is False:
                value = remove_date_from_datetime(value)
            cols.append(value)
        rows.append(cols)

    headers = create_header_for_fix_lines(fix_lines, show_date)

    return headers, rows


def remove_date_from_datetime(dt_str):
    # assume that the format is ISO 8601-ish and strip anything before the hh:mm:ss
    found_timestamp = re.search(r'(\d+:\d+:\d+.*)', dt_str)
    if found_timestamp:
        return found_timestamp.group(1)
    else:
        return dt_str


# -- Configuration --------
cfg = configparser.ConfigParser()
cfg_init()

if __name__ == '__main__':
    all_versions = get_list_of_available_fix_versions()
    print("\n".join(all_versions))
    tag_dict = extract_tag_dict_for_fix_version("4.2")
    json_file_path = "/tmp/fix_tags.json"
    save_tag_dict_to_json_file(tag_dict, json_file_path)
    tag_dict = load_tag_dict_from_json_file(json_file_path)
    print(tag_dict_to_json(tag_dict))
