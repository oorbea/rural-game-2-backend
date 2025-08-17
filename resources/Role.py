import datetime
import os
import traceback
from helpers.allow_filename import allowfilename
from helpers.auth.decorators import admin_required, login_required
from flask_smorest import Blueprint, abort
from flask.views import MethodView
from flask import Response, current_app, jsonify, request, send_from_directory
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from db import db 
from werkzeug.exceptions import NotFound
from werkzeug.utils import secure_filename
from globals import ALLOWED_PICTURE_EXTENSIONS, ROLE_PICTURES_DIR
from models.Role import Role
from schemas import GetRoleSchema, RoleSchema, TitleRoleSchema

blp = Blueprint('role', __name__, description='Role related CRUD operations.')

@blp.route('')
class RoleCRUD(MethodView):
    """CRUD operations for roles."""
    @login_required
    @blp.arguments(GetRoleSchema, location='query')
    @blp.response(200, RoleSchema(many=True))
    @blp.response(400, description='Bad request')
    @blp.response(401, description='Invalid token')
    @blp.response(403, description='You do not have permission for this operation')
    @blp.response(500, description='Internal server error.')
    def get(self, data):
        try: 
            data = GetRoleSchema().load(data)
            filters = []
            getTitle = request.args.get('title')
            if getTitle is not None :
                filters.append(Role.title == getTitle)

            getDescription = request.args.get('description')
            if getDescription is not None :
                filters.append(Role.description == getDescription)

            getQuantityPerGame = request.args.get('quantity_per_game')
            if getQuantityPerGame is not None :
                filters.append(Role.quantity_per_game == getQuantityPerGame)

            getPriority = request.args.get('priority')
            if getPriority is not None :
                filters.append(Role.priority == getPriority)

            roles:list[Role] = []
            if len(filters) > 0:
                roles = Role.query.filter(or_(*filters)).all()
            else:
                roles = Role.query.all()
            return jsonify([role.to_dict() for role in roles])
        
        except ValidationError as error:
            traceback.print_exc()
            abort(400, message=str(error))

        except Exception as error:
            traceback.print_exc()
            abort(500, message='Internal server error.')

    @admin_required
    @blp.arguments(RoleSchema)
    @blp.response(201, description='Role created.')
    @blp.response(400, description='Bad request')
    @blp.response(401, description='Invalid token')
    @blp.response(403, description='You do not have permission for this operation')
    @blp.response(409, description='Conflict.')
    @blp.response(500, description='Internal server error.')
    def post(self, data): 
        try:
            data = RoleSchema().load(data) 
            role = Role(**data)
            db.session.add(role) 
            db.session.commit()
            return Response(status=201)

        except ValidationError as error:
            traceback.print_exc()
            abort(400, message=str(error))

        except IntegrityError as error:
            db.session.rollback()
            abort(409, message='Role with the same title already exists.')

        except Exception as error:
            traceback.print_exc()
            db.session.rollback()
            abort(500, message='Internal server error.')

    @admin_required
    @blp.arguments(RoleSchema)
    @blp.arguments(TitleRoleSchema, location='query')
    @blp.response(204, description='Role updated.')
    @blp.response(400, description='Bad request')
    @blp.response(401, description='Invalid token')
    @blp.response(403, description='You do not have permission for this operation')
    @blp.response(404, description='Title not found.')
    @blp.response(500, description='Internal server error.')
    def put(self, bodydata, querydata):
        try:
            querydata = TitleRoleSchema().load(querydata) 
            role = Role.query.get(querydata.get("title"))
            if role is not None:
                bodydata = RoleSchema().load(bodydata) 
                for key, value in bodydata.items():
                    if hasattr(role, key):
                        setattr(role, key, value)
                db.session.commit()
                return Response(status=204)
            else:
                abort(404, message='Role not found.')

        except ValidationError as error:
            traceback.print_exc()
            abort(400, message=str(error))

        except NotFound as error:
            abort(404, message='Role not found.')

        except Exception as error:
            traceback.print_exc()
            db.session.rollback()
            abort(500, message='Internal server error.')

    @admin_required
    @blp.arguments(GetRoleSchema)
    @blp.arguments(TitleRoleSchema, location='query')
    @blp.response(200, RoleSchema, description='Role updated.')
    @blp.response(400, description='Bad request')
    @blp.response(401, description='Invalid token')
    @blp.response(403, description='You do not have permission for this operation')
    @blp.response(404, description='Title not found.')
    @blp.response(500, description='Internal server error.')
    def patch(self, bodydata, querydata):
        try:
            querydata = TitleRoleSchema().load(querydata) 
            role:Role = Role.query.get(querydata.get("title"))
            if role is not None:
                bodydata = GetRoleSchema().load(bodydata) 
                for key, value in bodydata.items():
                    if hasattr(role, key):
                        setattr(role, key, value)
                db.session.commit()
                return jsonify(role.to_dict()) 
            else:
                abort(404, message='Role not found.')
        
        except ValidationError as error:
            traceback.print_exc()
            abort(400, message=str(error))

        except NotFound as error:
            abort(404, message='Role not found.')

        except Exception as error:
            traceback.print_exc()
            db.session.rollback()
            abort(500, message='Internal server error.')

    @admin_required
    @blp.arguments(TitleRoleSchema, location='query')
    @blp.response(204, description='Role deleted.')
    @blp.response(400, description='Bad request')
    @blp.response(401, description='Invalid token')
    @blp.response(403, description='You do not have permission for this operation')
    @blp.response(404, description='Title not found.')
    @blp.response(500, description='Internal server error.')
    def delete(self, data):
        try:
            data = TitleRoleSchema().load(data) 
            role = db.session.get(Role, data.get("title"))
            if role is not None:
                db.session.delete(role)
                db.session.commit()
                return Response(status=204)
            else:
                abort(404, message='Role not found.')

        except ValidationError as error:
            traceback.print_exc()
            abort(400, message=str(error))

        except NotFound as error:
            abort(404, message='Role not found.')

        except Exception as error:
            traceback.print_exc()
            db.session.rollback()
            abort(500, message='Internal server error.')

@blp.route('icon')
class RoleImg(MethodView):
    """Handles role icon upload and retrieval."""
    @blp.doc(
        summary="Upload or update your role pic",
        consumes=["multipart/form-data"],
        requestBody={
            "required": True,
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "icon": {
                                "type": "string",
                                "format": "binary",
                                "description": f"Role pic file {str(ALLOWED_PICTURE_EXTENSIONS)}"
                            }
                        },
                        "required": ["icon"]
                    }
                }
            }
        }
    )
    @admin_required
    @blp.arguments(TitleRoleSchema, location='query')
    @blp.response(200, RoleSchema, description='Role updated.')
    @blp.response(400, description='Bad request')
    @blp.response(401, description='Invalid token')
    @blp.response(403, description='You do not have permission for this operation')
    @blp.response(404, description='Title not found.')
    @blp.response(500, description='Internal server error.')
    def patch(self, querydata):
        try:

            picture = request.files["icon"]
            originalfilename = picture.filename.replace(" ", "_")
            newfilename = secure_filename(f"{str(datetime.datetime.now()).replace(" ", "_")}_{originalfilename}") 
            if not allowfilename(newfilename):
                abort(400, message='Picture.')

            querydata = TitleRoleSchema().load(querydata) 
            role:Role = Role.query.get(querydata.get("title"))
            if role is not None:
                upload_dir = current_app.config.get('ROLE_PICTURES_DIR', ROLE_PICTURES_DIR)
                os.makedirs(upload_dir, exist_ok=True)
                save_path = os.path.join(upload_dir, newfilename)
                picture.save(save_path)
                role.icon = newfilename
                db.session.commit()
                return jsonify(role.to_dict()) 
            else:
                abort(404, message='Role not found.')
        
        except ValidationError as error:
            traceback.print_exc()
            abort(400, message=str(error))

        except KeyError as error:
            traceback.print_exc()
            abort(400, message='Picture needed.')

        except NotFound as error:
            abort(404, message='Role not found.')

        except Exception as error:
            traceback.print_exc()
            db.session.rollback()
            abort(500, message='Internal server error.')

    @login_required
    @blp.arguments(TitleRoleSchema, location='query')
    @blp.response(200, description='Icon found.')
    @blp.response(204, description='Icon not found.')
    @blp.response(400, description='Bad request')
    @blp.response(401, description='Invalid token')
    @blp.response(403, description='You do not have permission for this operation')
    @blp.response(404, description='Role not found.')
    @blp.response(500, description='Internal server error.')
    def get(self, data):
        try: 
            data = GetRoleSchema().load(data)
            getTitle = data.get('title')
            if getTitle is None :
                abort(400, message='Title is required.')
            role:Role = Role.query.get(getTitle)
            if role is None:
                abort(404, message='Role not found.')
            if role.icon is None:
                return Response(status=204)
            else:
                upload_dir = current_app.config.get('ROLE_PICTURES_DIR', ROLE_PICTURES_DIR)
                icon_path = os.path.join(upload_dir, role.icon)
                if not os.path.exists(icon_path):
                    abort(404, message='Icon file not found.')
                return send_from_directory(upload_dir, role.icon, as_attachment=False)
                
        except ValidationError as error:
            traceback.print_exc()
            abort(400, message=str(error))

        except NotFound as error:
            abort(404, message='Role not found.')
        
        except Exception as error:
            traceback.print_exc()
            db.session.rollback()
            abort(500, message='Internal server error.')