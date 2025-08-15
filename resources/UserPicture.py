import os
from flask import current_app, send_file, Response
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from controllers.GameController import GameController
from helpers.auth.decorators import login_required
from schemas import CodeAndUsernameSchema

blp = Blueprint('user-picture', __name__, description='Serve user profile pictures')

@blp.route('/lobby/<string:code>/user/<string:player_name>/profile-picture')
class UserPicture(MethodView):
    """Serves a user's profile picture for a given lobby."""

    @login_required
    @blp.arguments(CodeAndUsernameSchema, location='view_args')
    @blp.response(200, description='Profile picture file')
    @blp.response(204, description='No profile picture set')
    @blp.response(400, description='Invalid request parameters')
    @blp.response(401, description='Invalid token')
    @blp.response(403, description='You do not have permission for this operation')
    @blp.response(404, description='Lobby or user not found')
    @blp.response(500, description='Internal server error')
    def get(self, args):
        """
        Retrieve and stream the profile picture file if the user belongs
        to the given lobby. Returns 204 if no picture is set.
        """
        code = str(args["code"])
        username = args["player_name"]

        gc:GameController = current_app.extensions['game_controller']
        r = gc.redis

        if not r.sismember(gc.ACTIVE_LOBBIES_SET, code):
            abort(404, message='Lobby not found or inactive.')

        players_list_key = gc.PLAYERS_LIST_TEMPLATE.format(code=code)
        players = r.lrange(players_list_key, 0, -1)
        if username not in players:
            abort(404, message='Player not in this lobby.')

        user_key = gc.USER_INFO_TEMPLATE.format(username=username)
        if not r.exists(user_key):
            abort(404, message='User not found.')

        rel_path = r.hget(user_key, 'profile_pic')
        if not rel_path:
            return Response(status=204)

        base_dir = current_app.root_path
        abs_path = rel_path if os.path.isabs(rel_path) else os.path.join(base_dir, rel_path.lstrip('/'))
        if not os.path.exists(abs_path):
            abort(404, message='Profile picture file not found.')

        resp = send_file(abs_path, as_attachment=False, conditional=True)
        resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        resp.headers['Pragma'] = 'no-cache'
        resp.headers['Expires'] = '0'
        return resp
