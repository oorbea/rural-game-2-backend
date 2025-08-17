import os
from flask import current_app, send_file, Response
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from helpers.auth.decorators import login_required
from controllers.GameController import GameController
from schemas import CodeAndUsernameSchema

blp = Blueprint("user-picture", __name__, description="Serve user profile pictures")

@blp.route("/lobby/<string:code>/user/<string:player_name>/profile-picture")
class UserPicture(MethodView):
    """
    Serves a user's profile picture for a given lobby.
    Path params validated via CodeAndUsernameSchema in view_args.
    """

    @blp.arguments(CodeAndUsernameSchema, location="view_args")
    @login_required
    def get(self, args, **kwargs):
        code = str(args["code"])
        username = args["player_name"]

        gc: GameController = current_app.extensions["game_controller"]
        r = gc.redis

        if not r.sismember(gc.ACTIVE_LOBBIES_SET, code):
            abort(404, message="Lobby not found or inactive.")

        players_key = gc.PLAYERS_LIST_TEMPLATE.format(code=code)
        if username not in r.lrange(players_key, 0, -1):
            abort(404, message="Player not in this lobby.")

        user_key = gc.USER_INFO_TEMPLATE.format(username=username)
        if not r.exists(user_key):
            abort(404, message="User not found.")

        rel_path = r.hget(user_key, "profile_pic")
        if not rel_path:
            return Response(status=204)

        app_root = current_app.root_path
        abs_from_rel = os.path.join(app_root, rel_path.lstrip("/"))
        abs_path = rel_path if os.path.isabs(rel_path) else abs_from_rel

        pictures_root = os.path.abspath(os.path.join(app_root, "public", "ProfilePictures"))
        abs_path = os.path.abspath(abs_path)
        if not (abs_path == pictures_root or abs_path.startswith(pictures_root + os.sep)):
            abort(404, message="Profile picture file not found.")

        if not os.path.exists(abs_path):
            abort(404, message="Profile picture file not found.")

        resp = send_file(abs_path, as_attachment=False, conditional=True)
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp
