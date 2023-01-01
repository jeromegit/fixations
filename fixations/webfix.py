#!/usr/bin/env python3
from flask import Flask, render_template
from flask import request

from fixations.fix_utils import extract_fix_lines_from_str_lines, create_fix_lines_grid

app = Flask(__name__)

# TODO: create hyperlink to FIX specs for each tag based on FIX version
# TODO: add more info to README.md. Use rule80A and 47 as example for fix_args
# TODO: clean up examples
# TODO: add more example(s)
# TODO: simplify directory hierarchy
# TODO: logs/sample_blank.log is incorrect
# TODO: add more examples to logs
# TODO: add some pytest to detect the FIX version for example



TEXT_AREA_MAX_COUNT = 8092  # this is mandated by gunicorn


@app.route("/")
def home():
    fix_lines_param = request.args.get('fix_lines', '')
    show_date = True if request.args.get('show_date', False) else False
    fix_lines_str = fix_lines_param.splitlines()
    fix_tag_dict, fix_lines, used_fix_tags = extract_fix_lines_from_str_lines(fix_lines_str)
    headers, rows = create_fix_lines_grid(fix_tag_dict, fix_lines, used_fix_tags,
                                          with_session_level_tags=False, show_date=show_date)
    context = {'headers': headers,
               'rows': rows,
               'show_date': show_date,
               'max_count': TEXT_AREA_MAX_COUNT,
               'size': f"{len(fix_lines)} lines / {len(fix_lines_param)} chars"
               }
    return render_template("index.html", **context)


if __name__ == "__main__":
    app.run(debug=True, port=8001)
