#!/usr/bin/env python3
import urllib.parse
from typing import List, Tuple, Dict
from urllib.parse import unquote

from flask import Flask, render_template
from flask import request

from fixations.fix_store import Store
from fixations.fix_utils import extract_fix_lines_from_str_lines, create_fix_lines_grid, get_store_path, \
    get_lookup_url_template_for_js, obfuscate_lines, create_table_from_fix_lines, get_version, \
    create_tag_set, create_tag_list
from fixations.short_str_id import get_short_str_id

app = Flask(__name__)

FORM_ID = 'id'
FORM_FIX_LINES = 'fix_lines'
FORM_UPLOAD = 'upload'

store = Store(get_store_path())

DEFAULT_TOP_TAGS_STR = "49 56 35 39 150 11"
DEFAULT_TOP_TAGS = DEFAULT_TOP_TAGS_STR.split()


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


@app.route("/", methods=['POST', 'GET'])
def home():
    params = get_request_params(request)

    show_date = True if params.get('show_date', False) else False
    transpose = True if params.get('transpose', False) else False

    headers = comment_row = fix_lines_list = fix_lines = []
    id_str = lookup_url_template_for_js = error = None
    char_count = 0
    try:
        fix_lines_list, id_str, char_count, error = get_fix_lines_list(params)
        if params.get(FORM_UPLOAD, False):
            uploaded_url = get_url_for_str_id(id_str)
            return uploaded_url

        fix_tag_dict, fix_lines, used_fix_tags, fix_version = extract_fix_lines_from_str_lines(fix_lines_list)
        headers, rows, comment_row = create_fix_lines_grid(fix_tag_dict, fix_lines, used_fix_tags,
                                                           with_session_level_tags=False,
                                                           show_date=show_date, transpose=transpose)
        lookup_url_template_for_js = get_lookup_url_template_for_js(fix_version)
    except Exception as e:
        error = e
        rows = []

    top_tags, rows = set_top_rows(request, transpose, rows)

    context = {'headers': headers,
               'rows': rows,
               'comment_row': comment_row,
               'show_date': show_date,
               'transpose': transpose,

               'tags_to_highlight': top_tags if top_tags else DEFAULT_TOP_TAGS,
               'DEFAULT_TOP_TAGS_STR': DEFAULT_TOP_TAGS_STR,

               'fix_lines_list': [line.replace('"', '\\"') for line in fix_lines_list],  # Escape "
               'str_id': id_str,
               'lookup_url_template': lookup_url_template_for_js,
               'size': f"{len(fix_lines)} lines / {char_count} chars",
               'version': get_version(),
               'error': error
               }
    return render_template("index.html", **context)


def get_request_params(req) -> Dict[str, str]:
    params = {}

    # Get parameters from GET request
    if req.args:
        params.update(req.args.to_dict())

    # Get parameters from form data in POST request
    if req.form:
        params.update(req.form.to_dict())

    # Get parameters from JSON data in POST request
    if req.is_json:
        params.update(req.json)

    return params


def set_top_rows(req, transpose, rows: List[List[str]]) -> Tuple[List[str], List[List[str]]]:
    top_tags_str = request.cookies.get('top_tags')
    if top_tags_str and not transpose:
        top_tags = create_tag_list(unquote(top_tags_str))
        top_tags_row = []
        non_top_tags_row = []
        for row in rows:
            tag_col = row[0]
            if tag_col in top_tags:
                top_tags_row.append(row)
            else:
                non_top_tags_row.append(row)
        all_rows = top_tags_row + non_top_tags_row

        return top_tags, all_rows
    else:
        return [], rows


def get_fix_lines_list(params: Dict[str, str]):
    obfuscate_tags_str = params.get('obfuscate_tags', None)
    obfuscate_tags = create_tag_set(obfuscate_tags_str)

    str_id = params.get(FORM_ID)
    error = ''
    if str_id and not obfuscate_tags:
        fix_lines_str, _ = store.get(str_id)
        if fix_lines_str is None:
            if str_id and str_id != "None":
                error = f"There's no record for id:{str_id}!"
            fix_lines_str = ''
        fix_lines_list = fix_lines_str.splitlines()
        char_count = len(fix_lines_str)
    else:
        fix_lines_param = params.get(FORM_FIX_LINES, '')
        fix_lines_list = fix_lines_param.splitlines()
        if len(fix_lines_list) > 0:
            if len(obfuscate_tags):
                fix_lines_list = obfuscate_lines(fix_lines_list, obfuscate_tags)
            fix_lines_str = '\n'.join(fix_lines_list)
            char_count = len(fix_lines_str)
            str_id = store_fix_lines(fix_lines_str)
        else:
            char_count = 0

    return fix_lines_list, str_id, char_count, error


def store_fix_lines(fix_lines_str: str) -> str:
    str_id = get_short_str_id(fix_lines_str, length=8)
    store.save(str_id, fix_lines_str)

    return str_id


def get_url_for_str_id(id_str: str) -> str:
    url = f"{request.host_url}?{FORM_ID}={id_str}"

    return url


def main():
    app.run(debug=True, port=7979)


if __name__ == "__main__":
    main()
