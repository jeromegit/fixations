import json
import os.path
import pathlib
import re
from dataclasses import dataclass, field
from typing import Dict
from xml.dom.minidom import parse

DEFAULT_FIX_VERSION = '4.2'
FIX_TAG_ID_SENDING_TIME = '52'

@dataclass
class FixTagValue:
    value: str
    name: str
    desc: str

@dataclass
class FixTag:
    id: str
    name: str
    type: str
    desc: str
    values: Dict[str, FixTagValue] = field(default_factory=dict)

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
    root_dir = pathlib.Path("./fix_repository_2010_edition_20200402")
    if version:
        path = f"{root_dir}/FIX.{version}/Base"
        if file:
            path = path + "/" + file
    else:
        path = root_dir

    return path


def get_list_of_available_fix_versions():
    root_dir = path_for_fix_path()
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
        tag_dict_by_id[id].values[value] = fix_tag_value

    return tag_dict_by_id


def tag_dict_to_json(tag_dict):
    json_object = json.dumps(tag_dict, indent=3)
    return json_object


def load_tag_dict_from_json_file(json_file):
    with open(json_file) as json_file_fd:
        tag_dict = json.load(json_file_fd)
    return tag_dict


def save_tag_dict_to_json_file(tag_dict, json_file):
    json_object = tag_dict_to_json(tag_dict)
    with open(json_file, 'w') as json_file_fd:
        json_file_fd.write(json_object)


if __name__ == '__main__':
    versions = get_list_of_available_fix_versions()
    print("\n".join(versions))
    tag_dict = extract_data_for_fix_version("4.2")
    json_file_path = "/tmp/fix_tags.json"
    save_tag_dict_to_json_file(tag_dict, json_file_path)
    tag_dict = load_tag_dict_from_json_file(json_file_path)
    print(tag_dict_to_json(tag_dict))
