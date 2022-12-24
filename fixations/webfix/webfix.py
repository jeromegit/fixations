from flask import Flask, render_template
from flask import request

app = Flask(__name__)


@app.route("/")
def home():
    fix_lines_str = request.args.get("fix_lines", "")
    fix_lines = fix_lines_str.splitlines()
    context = {'fix_lines': fix_lines}
    return render_template("index.html", **context)


if __name__ == "__main__":
    app.run(debug=True, port=8001)
