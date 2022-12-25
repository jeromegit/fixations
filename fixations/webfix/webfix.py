from flask import Flask, render_template
from flask import request

from fixations.fix_utils import extract_fix_lines_from_str_lines, create_fix_lines_grid

app = Flask(__name__)


@app.route("/")
def home():
    fix_lines_param = request.args.get("fix_lines", "")
    fix_lines_str = fix_lines_param.splitlines()
    fix_tag_dict, fix_lines, used_fix_tags = extract_fix_lines_from_str_lines(fix_lines_str)
    headers, rows = create_fix_lines_grid(fix_tag_dict, fix_lines, used_fix_tags,
                                          with_session_level_tags=False, with_top_header=False)
    context = {'headers': headers,
               'rows': rows}
    return render_template("index.html", **context)


if __name__ == "__main__":
    app.run(debug=True, port=8001)
