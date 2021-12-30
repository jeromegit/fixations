from xml.dom.minidom import parse


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


# Parse XML from a filename
document = parse("./fix_repository_2010_edition_20200402/FIX.4.2/Base/Fields.xml")
fields = document.getElementsByTagName('Field')
tag_dict_by_id = {}
tag_dict_by_name = {}

for field in fields:
    id, name, type, desc = extract_tag_data_from_xml_field(field)
    tag_dict_by_name[name] = tag_dict_by_id[id] = {'id': id, 'name': name, 'type': type, 'desc': desc, 'values': {}}
#    print(id, name, type, desc)

document = parse("./fix_repository_2010_edition_20200402/FIX.4.2/Base/Enums.xml")
enums = document.getElementsByTagName('Enum')
tag_values_by_id = {}
for enum in enums:
    id, name, value, desc = extract_tag_data_from_xml_enum(enum)
    tag_dict_by_id[id]['values'][value] = {'name': name, 'desc': desc}

for id, record in tag_dict_by_id.items():
    print(f"{record}")
