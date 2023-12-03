#!/usr/bin/env python3
import urllib.parse

from flask import Flask, render_template
from flask import request

from fixations.fix_store import Store
from fixations.fix_utils import extract_fix_lines_from_str_lines, create_fix_lines_grid, get_store_path, \
    get_lookup_url_template_for_js, create_obfuscate_tag_set, obfuscate_lines, create_table_from_fix_lines
from fixations.short_str_id import get_short_str_id

app = Flask(__name__)

TEXT_AREA_MAX_COUNT = 8092  # this is mandated by gunicorn

FORM_ID = 'id'
FORM_FIX_LINES = 'fix_lines'
FORM_UPLOAD = 'upload'

store = Store(get_store_path())


@app.route('/stdin', methods=['POST'])
def receive_data():
    data = request.get_data().decode()
    data = urllib.parse.unquote_plus(data)
    fix_lines = data.splitlines()

    table = create_table_from_fix_lines(fix_lines)
    if not table:
        return "Could not find FIX lines!"

    str_id = store_fix_lines(data)
    url = get_url_for_str_id(str_id)

    return f"{table}\n{url}\n"


@app.route("/")
def home():
    fix_lines_list, id_str, char_count = get_fix_lines_list(request)
    if request.args.get(FORM_UPLOAD, False):
        uploaded_url = get_url_for_str_id(id_str)
        return uploaded_url

    show_date = True if request.args.get('show_date', False) else False
    transpose = True if request.args.get('transpose', False) else False

    fix_tag_dict, fix_lines, used_fix_tags, fix_version = extract_fix_lines_from_str_lines(fix_lines_list)
    headers, rows, comment_row = create_fix_lines_grid(fix_tag_dict, fix_lines, used_fix_tags,
                                                       with_session_level_tags=False,
                                                       show_date=show_date, transpose=transpose)
    lookup_url_template_for_js = get_lookup_url_template_for_js(fix_version)

    context = {'headers': headers,
               'rows': rows,
               'comment_row': comment_row,
               'show_date': show_date,
               'transpose': transpose,
               'max_count': TEXT_AREA_MAX_COUNT,
               'fix_lines_list': [line.replace('"', '\\"') for line in fix_lines_list],  # Escape "
               'str_id': id_str,
               'lookup_url_template': lookup_url_template_for_js,
               'size': f"{len(fix_lines)} lines / {char_count} chars"
               }
    return render_template("index.html", **context)


def get_fix_lines_list(req):
    obfuscate_tags_str = req.args.get('obfuscate_tags', None)
    obfuscate_tags = create_obfuscate_tag_set(obfuscate_tags_str)

    str_id = req.args.get(FORM_ID)
    if str_id and not obfuscate_tags:
        fix_lines_str, _ = store.get(str_id)
        if fix_lines_str is None:
            fix_lines_str = f"There's no record for id:{str_id}!"
        fix_lines_list = fix_lines_str.splitlines()
        char_count = len(fix_lines_str)
    else:
        fix_lines_param = req.args.get(FORM_FIX_LINES, '')
        fix_lines_list = fix_lines_param.splitlines()
        if len(fix_lines_list) > 0:
            if len(obfuscate_tags):
                fix_lines_list = obfuscate_lines(fix_lines_list, obfuscate_tags)
            fix_lines_str = '\n'.join(fix_lines_list)
            char_count = len(fix_lines_str)
            str_id = store_fix_lines(fix_lines_str)
        else:
            char_count = 0

    return fix_lines_list, str_id, char_count


def store_fix_lines(fix_lines_str: str) -> str:
    str_id = get_short_str_id(fix_lines_str, length=8)
    store.save(str_id, fix_lines_str)

    return str_id


def get_url_for_str_id(id_str: str) -> str:
    url = f"{request.host_url}?{FORM_ID}={id_str}"

    return url


def main():
    app.run(debug=True, port=8001)


if __name__ == "__main__":
    main()
