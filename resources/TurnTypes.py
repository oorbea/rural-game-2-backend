from flask_smorest import Blueprint
from flask.views import MethodView
from enums.TurnType import TurnTypeEnum
from helpers.auth.decorators import login_required

blp = Blueprint('turn-types', __name__, description='Defines the types of turns in the game.')

@blp.route('')
class TurnTypes(MethodView):
    """TurnTypes class to define the types of turns in the game."""
    @login_required
    @blp.response(200, description="List of available turn types.")
    @blp.response(401, description="Invalid token.")
    @blp.response(403, description="You do not have permission for this operation.")
    @blp.response(500, description="Internal server error.")
    def get(self):
        """Returns the available turn types."""
        try:
            return [e.value for e in TurnTypeEnum], 200
        except Exception as e:
            return {"error": str(e)}, 500