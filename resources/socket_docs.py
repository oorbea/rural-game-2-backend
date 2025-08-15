import os
from flask import current_app, Response, render_template_string
from flask_smorest import Blueprint

blp = Blueprint('docs', __name__, description='SocketIO and API documentation')

@blp.route("/asyncapi.yml")
def asyncapi_yaml():
    ASYNCAPI_PATH = os.path.join(os.path.dirname(__file__), "..", "asyncapi.yml")
    y = open(ASYNCAPI_PATH, "r", encoding="utf-8").read()
    y = y.replace("{{API_VERSION}}", current_app.config.get("API_VERSION", "1.0.0"))
    y = y.replace("{PREFIX}", current_app.config.get("SOCKETIO_PREFIX"))
    resp = Response(y, mimetype="text/yaml")
    resp.headers['Cache-Control'] = 'no-store'
    return resp

@blp.route("")
def asyncapi_docs():
    API_PREFIX = current_app.config.get('API_PREFIX')
    DOCS_HTML = f"""<!doctype html>
    <html>
    <head><meta charset="utf-8"><title>AsyncAPI Docs</title></head>
    <body>
      <asyncapi-component
        id="ac"
        cssImportPath="https://cdn.jsdelivr.net/npm/@asyncapi/react-component/styles/default.min.css">
      </asyncapi-component>

      <script src="https://cdn.jsdelivr.net/npm/@asyncapi/web-component/lib/asyncapi-web-component.js"></script>
      <script>
        document.getElementById('ac').schemaUrl = '{API_PREFIX}/docs/asyncapi.yml';
      </script>
    </body>
    </html>"""
    return render_template_string(DOCS_HTML)
