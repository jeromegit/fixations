#!/usr/bin/env python3
from flask import Flask, render_template
from flask import request

from fixations.fix_store import Store
from fixations.fix_utils import extract_fix_lines_from_str_lines, create_fix_lines_grid, get_store_path
from fixations.short_str_id import get_short_str_id

app = Flask(__name__)

TEXT_AREA_MAX_COUNT = 8092  # this is mandated by gunicorn

store = Store(get_store_path())


@app.route("/")
def home():
    fix_lines_list, id_str, char_count = get_fix_lines_list(request)
    show_date = True if request.args.get('show_date', False) else False

    fix_tag_dict, fix_lines, used_fix_tags = extract_fix_lines_from_str_lines(fix_lines_list)
    headers, rows = create_fix_lines_grid(fix_tag_dict, fix_lines, used_fix_tags,
                                          with_session_level_tags=False, show_date=show_date)
    context = {'headers': headers,
               'rows': rows,
               'show_date': show_date,
               'max_count': TEXT_AREA_MAX_COUNT,
               'fix_lines_list': fix_lines_list,
               'str_id': id_str,
               'size': f"{len(fix_lines)} lines / {char_count} chars"
               }
    return render_template("index.html", **context)


def get_fix_lines_list(req):
    str_id = req.args.get('id')
    if str_id:
        fix_lines_str, timestamp = store.get(str_id)
        if fix_lines_str is None:
            fix_lines_str = f"There's no record for id:{str_id}!"
        fix_lines_list = fix_lines_str.splitlines()
        char_count = len(fix_lines_str)
    else:
        fix_lines_param = req.args.get('fix_lines', '')
        fix_lines_list = fix_lines_param.splitlines()
        if len(fix_lines_list) > 0:
            fix_lines_str = '\n'.join(fix_lines_list)
            char_count = len(fix_lines_str)
            str_id = get_short_str_id(fix_lines_str, length=8)
            store.save(str_id, fix_lines_str)
        else:
            char_count = 0

    return fix_lines_list, str_id, char_count


def main():
    app.run(debug=True, port=8001)


if __name__ == "__main__":
    main()
