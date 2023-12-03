#!/usr/bin/env python3

import configparser
import json
import os.path
import pathlib
import re
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import cache
from string import Template
from typing import Dict, Union, List, Tuple, Set
from xml.dom.minicompat import NodeList
from xml.dom.minidom import parse

import requests as requests
import tabulate
from dataclasses_json import dataclass_json

DEFAULT_FIX_VERSION = "4.2"
FIX_TAG_ID_SENDING_TIME = "52"
FIX_TAG_ID_SENDER_COMP_ID = "49"
FIX_TAG_ID_TARGET_COMP_ID = "56"
SESSION_LEVEL_TAGS = ['8', '34', '9', '10']
VERSION_RE = r"8=FIXT*\.([.0-9SP]+)"
START_OF_BLOCK_CHARACTER = '\u229F '

# cfg key
CFG_FILE_SECTION_MAIN = "main"
CFG_FILE_KEY_DATA_DIR_PATH = "data_dir_path"
CFG_FILE_KEY_FIX_DEFINITIONS_PATH = "fix_definitions_path"
CFG_FILE_KEY_FIX_VERSION = "fix_version"
CFG_FILE_KEY_STORE_PATH = "store_path"
CFG_FILE_KEY_LOOKUP_URL_TEMPLATE = "lookup_url_template"
CFG_ADDITIONAL_FIX_DEFINITIONS_URL = "additional_fix_definition_url"
CFG_ADDITIONAL_FIX_DEFINITIONS_CACHE_PATH = "additional_fix_definition_path"
CFG_UPLOAD_URL = "upload_url"

# cfg / default values
DEFAULT_CFG_FILE_PATH = os.environ["HOME"] + "/.fixations.ini"
DEFAULT_DATA_DIR_PATH = os.environ["HOME"] + "/.fixations"
DEFAULT_FIX_DEFINITIONS_DIR = "fix_repository_2010_edition_20200402"
FIXATION_CFG_FILE_ENV = "FIXATION_CFG_FILE"
DEFAULT_STORE_PATH = DEFAULT_DATA_DIR_PATH + '/store.db'
DEFAULT_LOOKUP_URL_TEMPLATE = 'https://www.onixs.biz/fix-dictionary/${fix_version}/tagnum_${tag_num}.html'
DEFAULT_ADDITIONAL_FIX_DEFINITIONS_CACHE_PATH = "/tmp/additional_fix_definitions.txt"

# Global variable initialized at the bottom of this file
Cfg = None


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


@dataclass_json
@dataclass
class FixComponent:
    id: str  # componentId it's part of
    tag: str  # the tag can be numeric FIX tag or a (sub)group name
    indent: int
    position: str


@dataclass_json
@dataclass
class FixBlock:
    id: str
    name: str
    count_tag: str  # to be used as block's common tag
    start_tag: str  # to be used as start of block
    components_by_position: Dict[int, FixComponent] = field(default_factory=dict)
    tag_ids: set[str] = field(default_factory=set)


@dataclass
class FixVersionInfo:
    version: str
    fix_tags_by_tag_id: Dict[str, FixTag] = field(default_factory=dict)

    fix_blocks_by_id: Dict[int, 'FixBlock'] = field(default_factory=dict)
    fix_blocks_by_name: Dict[str, 'FixBlock'] = field(default_factory=dict)
    fix_blocks_by_count_tag: Dict[int, 'FixBlock'] = field(default_factory=dict)


# Caches
Xml_elements_cache: Dict[str, NodeList] = {}
Additional_tag_cache: Dict[str, Dict[str, FixTag]] = {}
Additional_tag_cache_expiry_time = 0
DEFAULT_CACHE_EXPIRY_TIME_OFFSET = 60 * 60  # 1 hour


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
        f"Can't find a valid config file, based on this list of potential files:{possible_cfg_files}."
    Cfg.read(found_cfg_file)


def get_cfg_value(key, section=CFG_FILE_SECTION_MAIN, warn_when_missing=True):
    assert section in Cfg, f"Section:{section} doesn't exist in your configuration file"
    section = Cfg[section]
    if key in section:
        value = section.get(key)
    else:
        if warn_when_missing:
            print(f"ERROR: key:{key} doesn't exist in section:{section} in your configuration file")
        value = None

    return value


def get_store_path():
    return get_cfg_for_key(CFG_FILE_KEY_STORE_PATH, DEFAULT_STORE_PATH)


def get_lookup_url_template():
    return get_cfg_for_key(CFG_FILE_KEY_LOOKUP_URL_TEMPLATE, DEFAULT_LOOKUP_URL_TEMPLATE)


def get_lookup_url_template_for_js(fix_version):
    url_template = Template(get_lookup_url_template())
    if fix_version == '1.1':
        fix_version = 'FIXT1.1'
    url_template_for_js = url_template.substitute({'fix_version': fix_version, 'tag_num': '${tag_num}'})

    return url_template_for_js


def get_cfg_for_key(key, default_value):
    value = get_cfg_value(key, warn_when_missing=False)
    if value:
        return value
    else:
        return default_value


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
        default_cfg = [f"[{CFG_FILE_SECTION_MAIN}]",
                       f"{CFG_FILE_KEY_DATA_DIR_PATH} = {DEFAULT_DATA_DIR_PATH}",
                       f"{CFG_FILE_KEY_FIX_DEFINITIONS_PATH} = {fix_definition_dir}",
                       f"{CFG_FILE_KEY_FIX_VERSION} = {DEFAULT_FIX_VERSION}",
                       f"{CFG_FILE_KEY_STORE_PATH} = {DEFAULT_STORE_PATH}"
                       f"{CFG_FILE_KEY_LOOKUP_URL_TEMPLATE} = {DEFAULT_LOOKUP_URL_TEMPLATE}",
                       f"{CFG_ADDITIONAL_FIX_DEFINITIONS_CACHE_PATH} = {DEFAULT_ADDITIONAL_FIX_DEFINITIONS_CACHE_PATH}"
                       ]
        with open(DEFAULT_CFG_FILE_PATH, "w") as cfg_fd:
            cfg_fd.writelines(line + "\n" for line in default_cfg)


def extract_additional_fixtags_from_text(text: str) -> Dict[str, FixTag]:
    lines = text.split('\n')
    additional_tags_dict = dict()
    for line in lines:
        # Assume the add'l fix tags are one per line with the format: tagid = some_value
        key_value_match = re.search(r'^\s*(\d+)\s*=\s*(\S+)', line)
        if key_value_match:
            key, value = key_value_match.groups()
            additional_tags_dict[key] = FixTag(key, value, 'String', f"N/A for tag:{key} / value:{value}", {})

    return additional_tags_dict


def extract_additional_fixtags_text_from_url(additional_fix_definitions_url: str) -> Dict[str, FixTag]:
    global Additional_tag_cache_expiry_time
    now = time.time()
    if additional_fix_definitions_url in Additional_tag_cache and now < Additional_tag_cache_expiry_time:
        return Additional_tag_cache[additional_fix_definitions_url]
    else:
        text = ''
        if additional_fix_definitions_url.startswith('file://'):
            local_path = additional_fix_definitions_url[len('file://'):]
            try:
                with open(local_path, 'r') as fd:
                    text = fd.read()
            except Exception as e:
                print(f"ERROR: can't read-open file:{local_path}. Error:{e}")
        else:
            try:
                response = requests.get(additional_fix_definitions_url)
                if response.ok:
                    text = response.text
            except Exception as e:
                print(f"ERROR: can't get data from url:{additional_fix_definitions_url}. Error:{e}")

        additional_fixtags = extract_additional_fixtags_from_text(text)
        Additional_tag_cache[additional_fix_definitions_url] = additional_fixtags
        Additional_tag_cache_expiry_time = now + DEFAULT_CACHE_EXPIRY_TIME_OFFSET

        return additional_fixtags


def check_for_additional_fix_definitions(additional_fix_definitions_url: str = None) -> Dict[str, FixTag]:
    if additional_fix_definitions_url is None:
        additional_fix_definitions_url = get_cfg_for_key(CFG_ADDITIONAL_FIX_DEFINITIONS_URL, None)
    if additional_fix_definitions_url:
        return extract_additional_fixtags_text_from_url(additional_fix_definitions_url)
    else:
        return {}


def get_xml_text(nodelist):
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data)
    return ''.join(rc)


def extract_tag_data_from_xml_field(field):
    return extract_tag_data_from_xml(field, ['Tag', 'Name', 'Type', 'Description'])


def extract_tag_data_from_xml_enum(enum):
    return extract_tag_data_from_xml(enum, ['Tag', 'SymbolicName', 'Value', 'Description'])


def extract_tag_data_from_xml_msg_content(msg_content):
    return extract_tag_data_from_xml(msg_content, ['ComponentID', 'TagText', 'Indent', 'Position'])


def extract_tag_data_from_xml(item: str, tag_names: List) -> List[str]:
    data = []
    for tag_name in tag_names:
        value = get_xml_text(item.getElementsByTagName(tag_name)[0].childNodes)
        data.append(value)

    return data


def path_for_fix_version(version=None, file=None):
    root_dir = get_cfg_value(CFG_FILE_KEY_FIX_DEFINITIONS_PATH)
    if version:
        # FIX.4.2 | FIXT.1.1
        path = f"{root_dir}/FIX.{version}/Base"
        if os.path.exists(path) is not True:
            path = f"{root_dir}/FIXT.{version}/Base"
        if file:
            path = path + "/" + file
    else:
        path = root_dir

    return path


def get_list_of_available_fix_versions():
    root_path = path_for_fix_version()
    root_dir = pathlib.Path(root_path)
    versions = []
    for entry in root_dir.glob("FIX*"):
        if os.path.isdir(entry):
            dir_name = os.path.basename(entry)
            version_match = re.search(r"FIXT*\.(.*)", dir_name)
            versions.append(version_match.group(1))

    return versions


def extract_elements_from_file_by_tag_name(fix_version, file, tag_name) -> NodeList:
    cache_key = '|'.join([fix_version, file, tag_name])
    if cache_key in Xml_elements_cache:
        return Xml_elements_cache[cache_key]
    else:
        fields_file = path_for_fix_version(fix_version, file)
        doc = parse(fields_file)
        elements = doc.getElementsByTagName(tag_name)
        Xml_elements_cache[cache_key] = elements

        return elements


@cache
def extract_info_for_fix_version(fix_version=DEFAULT_FIX_VERSION) -> FixVersionInfo:
    versions = get_list_of_available_fix_versions()
    assert fix_version in versions, f"The specified FIX version:{fix_version} is not valid. Use one of these {versions}"
    fix_version_info = FixVersionInfo(fix_version)

    # Extract all FIX tags from Fields XML file
    fields = extract_elements_from_file_by_tag_name(fix_version, "Fields.xml", "Field")
    for field_ in fields:
        tag_id, name, tag_type, desc = extract_tag_data_from_xml_field(field_)
        fix_version_info.fix_tags_by_tag_id[tag_id] = FixTag(tag_id, name, tag_type, desc, {})

    # Extract all FIX tag values from Enums XML file and attach them to the tag dictionary
    enums = extract_elements_from_file_by_tag_name(fix_version, "Enums.xml", "Enum")
    for enum in enums:
        tag_id, name, value, desc = extract_tag_data_from_xml_enum(enum)
        fix_tag_value = FixTagValue(value, name, desc)
        if tag_id in fix_version_info.fix_tags_by_tag_id:
            fix_version_info.fix_tags_by_tag_id[tag_id].values[value] = fix_tag_value
        else:
            # Somehow the quality of the data is not that great and some enum values reference tags that don't exist
            #            print(f"ERROR: id:{id} for name:{name}, value:{value}, desc:{desc} doesn't exist")
            pass

    additional_tag_dict = check_for_additional_fix_definitions()
    if len(additional_tag_dict):
        add_additional_tag_dict(additional_tag_dict, fix_version_info.fix_tags_by_tag_id)

    extract_fix_blocks_for_fix_version(fix_version_info)

    return fix_version_info


# Explanation of the
# Also see https://www.onixs.biz/fix-dictionary/4.4/compBlock_Parties.html
# MsgContents.xml contains a description of all blocks and their comprising items
#   * all items are grouped under the same ComponentID (say 1012)
#           <MsgContent added="FIX.4.3">
#                 <ComponentID>1012</ComponentID>
#                 <TagText>453</TagText>
#                 <Indent>0</Indent>
#                 <Position>1</Position>
#                 <Reqd>0</Reqd>
#                 <Description>Repeating group below should contain unique combinations of PartyID, PartyIDSource,
#                              and PartyRole</Description>
#         </MsgContent>
#   * the TagText if the FIX tag (such as 453)
#      Note that in the case of a subgroup it will not be a tag but a group name such as PtysSubGrp
#      One can convert it to an actual FIX tag by finding the FixBlock with name = TagText and getting its count_tag
#   * the Indent seems to be for display purposes
#   * the position (starting with 1) is also important
#
#  Component.xml contains a mapping of ComponentID (say 1012) and Name
#   * it's useful for group name such as 2077 (ComponentID) -> PtysSubGrp (Name)
#         <Component added="FIX.4.3">
#            <ComponentID>1012</ComponentID>
#            <ComponentType>BlockRepeating</ComponentType>
#            <CategoryID>Common</CategoryID>
#            <Name>Parties</Name>
#            <AbbrName>Pty</AbbrName>
#            <NotReqXML>0</NotReqXML>
#            <Description>The Parties component block is used to identify and convey information on the entities
#               both central and peripheral to the financial transaction represented by the FIX message containing
#               the Parties Block. The Parties block allows many different types of entites to be expressed through
#               use of the PartyRole field and identifies the source of the PartyID through the the PartyIDSource.
#            </Description>
#         </Component>
# Example:
# 453=6    <- number of items in the group (ComponentID=1012)
#   448=TDEM <- always starts with 448
#   447=D
#   452=1
#   802=2  <- number of sub-groups (ComponentID=2077, group PtysSubGrp)
#     523=4203
#     803=4014
#
#     523=PT3QB789TSUIDF371261
#     803=4025
#
#   (5 more repeated group starting with 448)
def extract_fix_blocks_for_fix_version(fix_version_info: FixVersionInfo) -> None:
    # Parse the Components and MsgContents XML file to get all groups/blocks and their components
    blocks = extract_elements_from_file_by_tag_name(fix_version_info.version, "Components.xml", "Component")
    for block in blocks:
        block_id, block_type, name = extract_tag_data_from_xml(block, ['ComponentID', 'ComponentType', 'Name'])
        if block_type == 'BlockRepeating' or block_type == 'ImplicitBlockRepeating':
            fix_block = FixBlock(block_id, name, '', '', {})
            fix_version_info.fix_blocks_by_id[block_id] = fix_block
            fix_version_info.fix_blocks_by_name[name] = fix_block

    components = extract_elements_from_file_by_tag_name(fix_version_info.version, "MsgContents.xml", "MsgContent")
    for component in components:
        block_id, tag, indent, position = extract_tag_data_from_xml(component,
                                                                    ['ComponentID', 'TagText', 'Indent', 'Position'])
        if block_id in fix_version_info.fix_blocks_by_id:
            fix_block = fix_version_info.fix_blocks_by_id[block_id]
            fix_component = FixComponent(block_id, tag, indent, position)
            fix_block.components_by_position[position] = fix_component
            fix_block.tag_ids.add(tag)

            if position == '1':
                fix_block.count_tag = tag
                fix_version_info.fix_blocks_by_count_tag[tag] = fix_block
            elif position == '2':
                fix_block.start_tag = tag

    convert_tag_ids_as_name_to_fix_tags(fix_version_info)


def convert_tag_ids_as_name_to_fix_tags(fix_version_info: FixVersionInfo) -> None:
    for block in fix_version_info.fix_blocks_by_id.values():
        new_tag_ids = set()
        for tag_id in block.tag_ids:
            tag_block = fix_version_info.fix_blocks_by_name.get(tag_id, None)
            if tag_block:
                new_tag_ids.add(tag_block.count_tag)
            else:
                new_tag_ids.add(tag_id)
        block.tag_ids = new_tag_ids


def add_additional_tag_dict(additional_tag_dict: Dict[str, FixTag], tag_dict: Dict[str, FixTag]) -> None:
    for tag, fix_tag in additional_tag_dict.items():
        if tag not in tag_dict:
            tag_dict[tag] = fix_tag


def tag_dict_to_json(tag_dict_):
    dict_of_objects = {k: (v.to_json() if isinstance(v, FixTag) else v) for k, v in tag_dict_.items()}
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
        # FIX.4.2 | FIXT.1.1
        match = re.search(VERSION_RE, line)
        if match:
            version = match.group(1)
            return version

    return None


def get_fix_version_info_dict_for_lines(str_fix_lines) -> FixVersionInfo:
    version = determine_fix_version(str_fix_lines)
    assert version, "ERROR: can't extract FIX version from lines starting with line:{str_fix_lines[0]}"
    fix_version_info = extract_info_for_fix_version(version)

    return fix_version_info


def get_kv_parts_from_line(line: str) -> Tuple[str, List[str], str, str]:
    match = re.search(VERSION_RE, line)
    if not match:
        comment_match = re.search(r'#\s*(.*)', line)
        comment = comment_match.group(1) if comment_match else ''
        return '', [], '', comment

    fix_start, fix_end = match.span()
    body_length_start = line.find('9=')
    separator = line[fix_end:body_length_start]

    line_prefix = line[:fix_start]
    fix_line = line[fix_start:]
    kv_parts = fix_line.split(separator)

    return line_prefix, kv_parts, separator, ''


# The resulting key is to be used for both sorting and encoding of block/sub-block information
# to be used later for formatting
def encode_key_for_fix_tags(tag_id: str, block_start: FixBlock = None, block_count: int = 0,
                            inner_block_start: FixBlock = None, inner_block_count: int = 0) -> str:
    key = None
    if block_start:
        key = f'{int(block_start.count_tag):06} {block_count:02}'
        if inner_block_start:
            key += f' {int(inner_block_start.count_tag):06} {inner_block_count:02}'
    if key:
        key += ' ' + simple_tag_id_encoding(tag_id)
    else:
        key = simple_tag_id_encoding(tag_id)

    return key


def simple_tag_id_encoding(tag_id: str) -> str:
    return f'{int(tag_id):06}'


def decode_key_for_fix_tags(key: str) -> Tuple[str, str]:
    if ' ' in key:
        # key with block information
        elements = key.split(' ')
        block_count = int(elements[1])
        tag_id = elements[2].lstrip('0')
        if block_count == 0:
            formatted_tag_id = START_OF_BLOCK_CHARACTER + tag_id
        else:
            formatted_tag_id = f"├─[{block_count}] {tag_id}"
        if len(elements) == 5:
            # key with inner-block information
            inner_block_count = int(elements[3])
            tag_id = elements[4].lstrip('0')
            if inner_block_count == 0:
                formatted_tag_id = f"├─[{block_count}] {START_OF_BLOCK_CHARACTER}{tag_id}"
            else:
                padding_char = '\u00A0'
                formatted_tag_id = f"{padding_char * 6}├─[{inner_block_count}] {tag_id}"

    else:
        tag_id = key.lstrip('0')
        formatted_tag_id = tag_id

    return tag_id, formatted_tag_id


def parse_fix_line_into_kvs(line: str, fix_version_info: FixVersionInfo) -> Tuple[Dict[str, str], str]:
    _, kv_parts, separator, comment = get_kv_parts_from_line(line)

    kvs = {}
    fix_tags_by_tag_id = fix_version_info.fix_tags_by_tag_id
    fix_blocks_by_count_tag = fix_version_info.fix_blocks_by_count_tag
    current_block, current_inner_block = None, None
    current_block_count, current_inner_block_count = 0, 0
    for kv_part in kv_parts:
        if kv_part:
            kv = re.search(r"^(\d+)=(.*)", kv_part)
            if kv:
                tag_id, value = kv.group(1, 2)
                if tag_id in fix_tags_by_tag_id and value in fix_tags_by_tag_id[tag_id].values:
                    value = f"{value} ({fix_tags_by_tag_id[tag_id].values[value].name})"

                # it's hard to determine when a block (or inner block) is done until we reach the next unrelated tag
                if current_inner_block and tag_id not in current_inner_block.tag_ids:
                    current_inner_block = None
                if not current_inner_block and current_block and tag_id not in current_block.tag_ids:
                    current_block = None

                if tag_id in fix_blocks_by_count_tag:
                    # starts of a block or inner block
                    if current_block:
                        if tag_id in current_block.tag_ids:
                            current_inner_block = fix_blocks_by_count_tag[tag_id]
                            current_inner_block_count = 0
                        else:
                            current_block = fix_blocks_by_count_tag[tag_id]
                            current_block_count = 0
                    else:
                        current_block = fix_blocks_by_count_tag[tag_id]
                        current_block_count = 0

                if current_block:
                    if tag_id == current_block.start_tag:
                        current_block_count += 1

                    if current_inner_block and tag_id == current_inner_block.start_tag:
                        current_inner_block_count += 1

                    key = encode_key_for_fix_tags(tag_id, current_block, current_block_count,
                                                  current_inner_block, current_inner_block_count)

                else:
                    key = encode_key_for_fix_tags(tag_id)

                kvs[key] = value
            else:
                print(f"ERROR: can't tokenize:'{kv_part}' into a key=value pair using separator:'{separator}'")
    #    print(f"{fix_line}:\n\t{kvs}")

    return kvs, comment


def extract_version_from_first_fix_line(str_fix_lines):
    for line in str_fix_lines:
        if len(line.strip()) > 0:
            version = determine_fix_version(str_fix_lines)
            return version

    return None


def get_fix_tag_value_from_fix_tags(tag_id: str, fix_tags: dict[str, str]) -> Union[str, None]:
    if fix_tags:
        if tag_id in fix_tags:
            return fix_tags[tag_id]

        encoded_tag_id = simple_tag_id_encoding(tag_id)
        if encoded_tag_id in fix_tags:
            return fix_tags[encoded_tag_id]

    return None


def extract_timestamp(line, fix_tags=None):
    # assume that the there's a timestamp before the beginning of the FIX k/v tags
    match = re.search(r"(\d*\d:\d\d:\d\d[,.0-9]*).*8=FIXT*\.\d+", line)
    if match:
        return match.group(1), None
    else:
        timestamp = get_fix_tag_value_from_fix_tags(FIX_TAG_ID_SENDING_TIME, fix_tags)
        if timestamp:
            return timestamp, None
        else:
            error = f"ERROR: FIX line w/o timestamp and SENDING_TIME tag{FIX_TAG_ID_SENDING_TIME}: {line}"
            return None, error


def extract_fix_lines_from_str_lines(str_fix_lines: List[str]):
    if len(str_fix_lines):
        version = extract_version_from_first_fix_line(str_fix_lines)
        if version:
            fix_version_info = extract_info_for_fix_version(version)
            used_fix_tags = {}
            fix_lines = []
            previous_line_comment = ''
            for line in str_fix_lines:
                if line is not None and len(line) > 0 and not line.isspace():
                    fix_tags, comment = parse_fix_line_into_kvs(line.strip(), fix_version_info)
                    if fix_tags:
                        timestamp, error = extract_timestamp(line, fix_tags)
                        if timestamp:
                            for fix_tag_key in fix_tags.keys():
                                used_fix_tags[fix_tag_key] = 1
                            fix_lines.append((timestamp, fix_tags, previous_line_comment))
                        else:
                            print(error)
                    previous_line_comment = comment

            return fix_version_info.fix_tags_by_tag_id, fix_lines, used_fix_tags, version

    return {}, [], {}, None


def create_obfuscate_tag_set(obfuscate_tags_str: str) -> Set[int]:
    if obfuscate_tags_str and len(obfuscate_tags_str):
        obfuscate_tag_set = set(obfuscate_tags_str.split())
    else:
        obfuscate_tag_set = set()

    return obfuscate_tag_set


def obfuscate_lines(lines: List[str], obfuscate_tags: set[str]) -> List[str]:
    obfuscate_lines = list()
    for line in lines:
        obfuscate_lines.append(obfuscate_tag_values_in_line(line, obfuscate_tags))

    return obfuscate_lines


def obfuscate_tag_values_in_line(line: str, obfuscate_tags: set[str]) -> None:
    line_prefix, kv_parts, separator, comment = get_kv_parts_from_line(line)

    obfuscated_kvs: List = list()
    for kv_part in kv_parts:
        if kv_part:
            kv = re.search(r"^(\d+)=(.*)", kv_part)
            if kv:
                tag_id, value = kv.group(1, 2)
                if tag_id in obfuscate_tags:
                    obfuscated_value = '*' * len(value)
                    kv_part = '='.join((tag_id, obfuscated_value))
        obfuscated_kvs.append(kv_part)

    if comment:
        comment = '# ' + comment

    obfuscated_line = line_prefix + separator.join(obfuscated_kvs) + comment

    return obfuscated_line


def create_header_for_fix_lines(fix_lines: str, show_date: bool) -> List[str]:
    headers = ['TAG_ID', 'TAG_NAME']
    previous_timestamp = None
    for (timestamp, fix_tags, _) in fix_lines:
        if show_date is False:
            timestamp = remove_date_from_datetime(timestamp)
        timestamp_with_delta = get_timestamp_with_delta(timestamp, previous_timestamp)
        previous_timestamp = timestamp
        headers.append(timestamp_with_delta)

    return headers


# def tag_id_sorting(tag_id: str) -> str:
#     if ' ' in tag_id:
#

def create_comment_row(fix_lines) -> Union[None | List[str]]:
    cols = ['#', 'COMMENT']
    comments_are_present = False
    for (_, _, comment) in fix_lines:
        if comment:
            comments_are_present = True
            cols.append(comment)
        else:
            cols.append('')

    return cols if comments_are_present else None


def create_fix_lines_grid(fix_tag_dict, fix_lines, used_fix_tags,
                          with_session_level_tags=True, top_header_tags=[],
                          show_date=False, transpose=False):
    top_header_tags = [simple_tag_id_encoding(fix_tag) for fix_tag in top_header_tags]
    comment_rows = create_comment_row(fix_lines)
    rows = []
    for key in (*top_header_tags, *sorted(used_fix_tags)):
        fix_tag, formatted_fix_tag = decode_key_for_fix_tags(key)
        if fix_tag in SESSION_LEVEL_TAGS and with_session_level_tags is False:
            continue
        if fix_tag in fix_tag_dict:
            fix_tag_name = fix_tag_dict[fix_tag].name
        else:
            fix_tag_name = '???'
        cols = [formatted_fix_tag, fix_tag_name]
        for (_, fix_tags, comment) in fix_lines:
            value = fix_tags[key] if key in fix_tags else ''
            if 'time' in fix_tag_name.lower() and show_date is False:
                value = remove_date_from_datetime(value)
            cols.append(value)
        rows.append(cols)

    headers = create_header_for_fix_lines(fix_lines, show_date)

    if transpose:
        headers, rows = transpose_data_grid(headers, rows)

    return headers, rows, comment_rows


def transpose_data_grid(headers, rows):
    transposed = []
    for c in range(len(headers)):
        row = [headers[c]]
        for r in range(len(rows)):
            row.append(rows[r][c])
        transposed.append(row)

    transposed_headers = transposed.pop(0)

    return transposed_headers, transposed


def remove_date_from_datetime(dt_str):
    # assume that the format is ISO 8601-ish and strip anything before the hh:mm:ss
    found_timestamp = re.search(r'(\d+:\d+:\d+.*)', dt_str)
    if found_timestamp:
        return found_timestamp.group(1)
    else:
        return dt_str


def get_timestamp_with_delta(timestamp: str, previous_timestamp: Union[str, None]) -> str:
    if previous_timestamp:
        stripped_timestamp = remove_date_from_datetime(timestamp)
        stripped_previous_timestamp = remove_date_from_datetime(previous_timestamp)

        try:
            dt = datetime.strptime(stripped_timestamp, '%H:%M:%S.%f' if '.' in stripped_timestamp else "%H:%M:%S")
            previous_dt = datetime.strptime(stripped_previous_timestamp,
                                            '%H:%M:%S.%f' if '.' in stripped_previous_timestamp else "%H:%M:%S")
            delta = dt - previous_dt
            delta_in_hhmmssus = convert_delta_into_hhmmssus(delta)

            return f"{timestamp}\n({delta_in_hhmmssus})"

        except Exception as e:
            return f"{timestamp}\n(??? {e} ???)"
    else:
        return timestamp


def convert_delta_into_hhmmssus(delta: timedelta) -> str:
    sign = '-' if delta.total_seconds() < 0 else '+'
    delta_df = datetime(2000, 1, 1) + abs(delta)
    delta_in_hhmmssus = delta_df.strftime('%H:%M:%S.%f')
    delta_in_hhmmssus = re.sub(r"[0.]+$", "", delta_in_hhmmssus)  # strip trailing 0's
    delta_in_hhmmssus = re.sub(r"^[0:]+", "", delta_in_hhmmssus)  # replace leading 0:'s

    return sign + delta_in_hhmmssus


def display_fix_blocks():
    for id, fix_block in FixBlock.fix_blocks_by_id.items():
        print(f"id:{id}")
        for position, fix_component in fix_block.components_by_position.items():
            print(f"\t{position} -> {fix_component}")


def create_table_from_fix_lines(fix_lines: List[str], grid_style: str = 'psql') -> str:
    fix_tag_dict, fix_lines, used_fix_tags, _ = extract_fix_lines_from_str_lines(fix_lines)
    if len(used_fix_tags) == 0:
        print("Could not find FIX lines.")
        exit(1)

    top_header_tags = [FIX_TAG_ID_SENDER_COMP_ID, FIX_TAG_ID_TARGET_COMP_ID]
    headers, rows, comment_row = create_fix_lines_grid(fix_tag_dict, fix_lines, used_fix_tags, top_header_tags=top_header_tags)
    if comment_row:
        rows.insert(0, comment_row)
        rows.insert(1, tabulate.SEPARATING_LINE)
        if top_header_tags:
            rows.insert(len(top_header_tags) + 2, tabulate.SEPARATING_LINE)
    else:
        if top_header_tags:
            rows.insert(len(top_header_tags), tabulate.SEPARATING_LINE)

    table = tabulate.tabulate(rows, headers=headers, stralign='left', tablefmt=grid_style)

    return table


# -- Configuration --------
Cfg = configparser.ConfigParser()
cfg_init()

if __name__ == '__main__':
    extract_fix_blocks_for_fix_version(FixVersionInfo("4.4"))
    display_fix_blocks()
    exit()

    all_versions = get_list_of_available_fix_versions()
    print("\n".join(all_versions))
    tag_dict = extract_tag_dict_for_fix_version("4.2")
    json_file_path = "/tmp/fix_tags.json"
    save_tag_dict_to_json_file(tag_dict, json_file_path)
    tag_dict = load_tag_dict_from_json_file(json_file_path)
    print(tag_dict_to_json(tag_dict))
