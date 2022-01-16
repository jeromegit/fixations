#!/usr/bin/env python3

import configparser
import json
import os.path
import pathlib
import re
import shutil
from dataclasses import dataclass, field
from typing import Dict
from xml.dom.minidom import parse

from dataclasses_json import dataclass_json

DEFAULT_FIX_VERSION = "4.2"
FIX_TAG_ID_SENDING_TIME = "52"
FIX_TAG_ID_SENDER_COMP_ID = "49"
FIX_TAG_ID_TARGET_COMP_ID = "56"

DEFAULT_CFG_FILE_PATH = os.environ["HOME"] + "/.fixations.ini"
DEFAULT_DATA_DIR_PATH = os.environ["HOME"] + "/.fixations"
DEFAULT_FIX_DEFINITIONS_DIR = "fix_repository_2010_edition_20200402"
FIXATION_CFG_FILE_ENV = "FIXATION_CFG_FILE"
#
CFG_FILE_SECTION_MAIN = "main"
CFG_FILE_KEY_DATA_DIR_PATH = "data_dir_path"
CFG_FILE_KEY_FIX_DEFINITIONS_PATH = "fix_definitions_path"
CFG_FILE_KEY_FIX_VERSION = "fix_version"

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
    assert key in section, f"key:{key} doesn't exist in section:{section} in your configuration file"
    value = section.get(key)

    return value


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
                                                       f"{CFG_FILE_KEY_FIX_VERSION} = {DEFAULT_FIX_VERSION}"
                                                       ])


def get_xml_text(nodelist):
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data)
    return ''.join(rc)


def extract_tag_data_from_xml_field(field):
    data = []
    for tag_name in ('Tag', 'Name', 'Type', 'Description'):
        value = get_xml_text(field.getElementsByTagName(tag_name)[0].childNodes)
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


def extract_tag_dict_for_fix_version(fix_version=DEFAULT_FIX_VERSION):
    versions = get_list_of_available_fix_versions()
    assert fix_version in versions, f"The specified FIX version:{fix_version} is not valid. Use one of these {versions}"

    # Extract all FIX tags from Fields XML file
    fields = extract_elements_from_file_by_tag_name(fix_version, "Fields.xml", "Field")
    tag_dict_by_id = {}
    for field in fields:
        id, name, type, desc = extract_tag_data_from_xml_field(field)
        #        tag_dict_by_id[id] = {'id': id, 'name': name, 'type': type, 'desc': desc, 'values': {}}
        tag_dict_by_id[id] = FixTag(id, name, type, desc, {})

    # Extract all FIX tag values from Enums XML file and attach them to the tag dictionary
    enums = extract_elements_from_file_by_tag_name(fix_version, "Enums.xml", "Enum")
    for enum in enums:
        id, name, value, desc = extract_tag_data_from_xml_enum(enum)
        #        tag_dict_by_id[id]['values'][value] = {'value': value, 'name': name, 'desc': desc}
        fix_tag_value = FixTagValue(value, name, desc)
        if id in tag_dict_by_id:
            tag_dict_by_id[id].values[value] = fix_tag_value
        else:
            # Somehow the quality of the data is not that great and some enum values reference tags that don't exist
#            print(f"ERROR: id:{id} for name:{name}, value:{value}, desc:{desc} doesn't exist")
            pass

    return tag_dict_by_id


def tag_dict_to_json(tag_dict):
    dict_of_objects = {k: (v.to_json() if type(v) == FixTag else v) for k, v in tag_dict.items()}
    json_object = json.dumps(dict_of_objects, indent=3)
    return json_object


def load_tag_dict_from_json_file(json_file):
    with open(json_file) as json_file_fd:
        tag_dict = json.load(json_file_fd)
    return tag_dict


def save_tag_dict_to_json_file(tag_dict, json_file):
    json_object = tag_dict_to_json(tag_dict)
    with open(json_file, 'w') as json_file_fd:
        json_file_fd.write(json_object)

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
