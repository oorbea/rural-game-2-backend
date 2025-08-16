import os
from flask_smorest import Blueprint
from flask.views import MethodView

blp = Blueprint('main-page', __name__, description='Main API page.')

@blp.route('')
class ChallengeCRUD(MethodView):
    """Main page for the API documentation."""
    def get(self):
        """Returns the main page of the API documentation."""
        with open(os.path.join(os.path.dirname(__file__), '..', 'helpers', 'main_page.html'), 'r') as file:
            content = file.read()
        return content, 200, {'Content-Type': 'text/html'}