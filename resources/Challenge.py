from flask_smorest import Blueprint, abort
from flask.views import MethodView

blp = Blueprint('challenge', __name__, description='Challenge related CRUD operations.')

@blp.route('')
class ChallengeCRUD(MethodView):
    """Handles CRUD operations for challenges."""