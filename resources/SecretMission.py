import datetime
from operator import or_
import os
import traceback
from globals import ALLOWED_PICTURE_EXTENSIONS, CHALLENGE_PICTURES_DIR
from helpers.RestrictionAdapter import RestrictionAdapter
from flask import Response, current_app, jsonify, request, send_from_directory
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from marshmallow import ValidationError
from pymysql import IntegrityError
from werkzeug.exceptions import NotFound
from werkzeug.utils import secure_filename
from db import db 
from helpers.allow_filename import allowfilename
from helpers.auth.decorators import admin_required, login_required
from models import SecretMission
from schemas import SecretMissionSchema, GetSecretMissionSchema, TitleSecretMissionSchema

blp = Blueprint("secret_mission", __name__, description="CRUD operations on secret missions")

@blp.route("")
class SecretMissionCRUD(MethodView):
    """CRUD operations for Secret Missions."""

    @login_required
    @blp.arguments(GetSecretMissionSchema, location="query")
    @blp.response(200, SecretMissionSchema(many=True))  
    @blp.response(400, description="Bad request")       
    @blp.response(401, description="Invalid token")
    @blp.response(403, description="You do not have permission for this operation")
    @blp.response(500, description="Internal server error.")
    def get(self, data):
        try:
            data = GetSecretMissionSchema().load(data)
            filters = []
            getTitle = data.get("title")
            if getTitle is not None:
                filters.append(SecretMission.title == getTitle)
            
            getDescription = data.get("description")
            if getDescription is not None:
                filters.append(SecretMission.description == getDescription)

            getDrinking = data.get("drinking")
            if getDrinking is not None:
                filters.append(SecretMission.drinking == getDrinking)
            
            getSex = data.get("sex")
            if getSex is not None:
                filters.append(SecretMission.sex == getSex)

            getSmoking = data.get("smoking")
            if getSmoking is not None :
                filters.append(SecretMission.smoking == getSmoking)
            
            getPartnerFriendly = data.get('partner_friendly')
            if getPartnerFriendly is not None :
                filters.append(SecretMission.partner_friendly == getPartnerFriendly)
            
            getProbability = data.get('probability')
            if getProbability is not None :
                filters.append(SecretMission.probability == getProbability)

            getPrize = data.get('prize')
            if getPrize is not None :
                filters.append(SecretMission.prize == getPrize)

            getMales = data.get('males')
            if getMales is not None :
                filters.append(SecretMission.males == getMales)

            getFemales = data.get('females')
            if getFemales is not None :
                filters.append(SecretMission.females == getFemales)

            if len(filters) > 0:
                secret_missions = SecretMission.query.filter(or_(*filters)).all()
            else:
                secret_missions = SecretMission.query.all()
            return jsonify([secret_mission.to_dict() for secret_mission in secret_missions])
        

        except ValidationError as error:
            traceback.print_exc()
            abort(400, message=str(error))

        except Exception:
            traceback.print_exc()
            abort(500, message="Internal server error.")

    @admin_required
    @blp.arguments(SecretMissionSchema)
    @blp.response(201, description='Secret mission created.')
    @blp.response(400, description='Bad request')
    @blp.response(401, description='Invalid token')
    @blp.response(403, description='You do not have permission for this operation')
    @blp.response(409, description='Conflict.')
    @blp.response(500, description='Internal server error.')
    def post(self, data:dict): 
        try:
            data = SecretMissionSchema().load(data) 
            description = data.get("description")
            data['males'] = RestrictionAdapter.get_num_males(description)
            data['females'] = RestrictionAdapter.get_num_females(description)
            secret_mission = SecretMission(**data)
            db.session.add(secret_mission) 
            db.session.commit()
            return Response(status=201)

        except ValidationError as error:
            traceback.print_exc()
            abort(400, message=str(error))

        except IntegrityError as error:
            db.session.rollback()
            abort(409, message='A secret mission with the same title already exists.')

        except Exception as error:
            traceback.print_exc()
            db.session.rollback()
            abort(500, message='Internal server error.')

    @admin_required
    @blp.arguments(SecretMissionSchema)
    @blp.arguments(TitleSecretMissionSchema, location='query')
    @blp.response(204, description='Secret mission updated.')
    @blp.response(400, description='Bad request')
    @blp.response(401, description='Invalid token')
    @blp.response(403, description='You do not have permission for this operation')
    @blp.response(404, description='Title not found.')
    @blp.response(500, description='Internal server error.')
    def put(self, bodydata, querydata):
        try:
            querydata = TitleSecretMissionSchema().load(querydata) 
            secret_mission = SecretMission.query.get(querydata.get("title"))
            if secret_mission is not None:
                bodydata = SecretMissionSchema().load(bodydata) 
                for key, value in bodydata.items():
                    if key == 'males' or key == 'females':
                        continue
                    if hasattr(secret_mission, key):
                        setattr(secret_mission, key, value)
                        if key == 'description':
                            setattr(secret_mission, 'males', RestrictionAdapter.get_num_males(value))
                            setattr(secret_mission, 'females', RestrictionAdapter.get_num_females(value))
                db.session.commit()
                return Response(status=204)
            else:
                abort(404, message='Title not found.')

        except ValidationError as error:
            traceback.print_exc()
            abort(400, message=str(error))

        except NotFound as error:
            abort(404, message='Title not found.')

        except Exception as error:
            traceback.print_exc()
            db.session.rollback()
            abort(500, message='Internal server error.')

    @admin_required
    @blp.arguments(GetSecretMissionSchema)
    @blp.arguments(TitleSecretMissionSchema, location='query')
    @blp.response(200, SecretMissionSchema, description='Secret Mission updated.')
    @blp.response(400, description='Bad request')
    @blp.response(401, description='Invalid token')
    @blp.response(403, description='You do not have permission for this operation')
    @blp.response(404, description='Title not found.')
    @blp.response(500, description='Internal server error.')
    def patch(self, bodydata, querydata):
        try:
            querydata = TitleSecretMissionSchema().load(querydata) 
            secret_mission = SecretMission.query.get(querydata.get("title"))
            if secret_mission is not None:
                bodydata = GetSecretMissionSchema().load(bodydata) 
                for key, value in bodydata.items():
                    if key == 'males' or key == 'females':
                        continue
                    if hasattr(secret_mission, key):
                        setattr(secret_mission, key, value)
                        if key == 'description':
                            setattr(secret_mission, 'males', RestrictionAdapter.get_num_males(value))
                            setattr(secret_mission, 'females', RestrictionAdapter.get_num_females(value))
                db.session.commit()
                return jsonify(secret_mission.to_dict()) 
            else:
                abort(404, message='Title not found.')
        
        except ValidationError as error:
            traceback.print_exc()
            abort(400, message=str(error))

        except NotFound as error:
            abort(404, message='Title not found.')

        except Exception as error:
            traceback.print_exc()
            db.session.rollback()
            abort(500, message='Internal server error.')


    @admin_required
    @blp.arguments(TitleSecretMissionSchema, location='query')
    @blp.response(204, description='Secret Mission deleted.')
    @blp.response(400, description='Bad request')
    @blp.response(401, description='Invalid token')
    @blp.response(403, description='You do not have permission for this operation')
    @blp.response(404, description='Title not found.')
    @blp.response(500, description='Internal server error.')
    def delete(self, data):
        try:
            data = TitleSecretMissionSchema().load(data) 
            secret_mission = db.session.get(SecretMission, data.get("title"))
            if secret_mission is not None:
                db.session.delete(secret_mission)
                db.session.commit()
                return Response(status=204)
            else:
                abort(404, message='Title not found.')

        except ValidationError as error:
            traceback.print_exc()
            abort(400, message=str(error))

        except NotFound as error:
            abort(404, message='Title not found.')

        except Exception as error:
            traceback.print_exc()
            db.session.rollback()
            abort(500, message='Internal server error.')

@blp.route('icon')
class SecretMissionImg(MethodView):
    """Handles secret mission icon upload and retrieval."""
    @blp.doc(
        summary="Upload or update your secret mission pic",
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
                                "description": f"Secret Mission pic file {str(ALLOWED_PICTURE_EXTENSIONS)}. If not provided, deletes the current icon."
                            }
                        },
                        "required": ["icon"]
                    }
                }
            }
        }
    )
    @admin_required
    @blp.arguments(TitleSecretMissionSchema, location='query')
    @blp.response(200, SecretMissionSchema, description='Secret mission updated.')
    @blp.response(400, description='Bad request')
    @blp.response(401, description='Invalid token')
    @blp.response(403, description='You do not have permission for this operation')
    @blp.response(404, description='Title not found.')
    @blp.response(500, description='Internal server error.')
    def patch(self, querydata):
        try:
            querydata = TitleSecretMissionSchema().load(querydata)
            secret_mission:SecretMission = SecretMission.query.get(querydata.get("title"))
            picture = request.files["icon"]
            if not picture:
                old_picture = secret_mission.icon
                if old_picture is None:
                    abort(204, message='No icon to delete.')
                else:
                    upload_dir = current_app.config.get('CHALLENGE_PICTURES_DIR', CHALLENGE_PICTURES_DIR)
                    old_path = os.path.join(upload_dir, old_picture)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                    secret_mission.icon = None
                    db.session.commit()
                    return Response(status=204)
            else:
                originalfilename = picture.filename.replace(" ", "_")
                newfilename = secure_filename(f"{str(datetime.datetime.now()).replace(" ", "_")}_{originalfilename}") 
                if not allowfilename(newfilename):
                    abort(400, message='Picture filename not allowed.')
                if secret_mission is not None:
                    upload_dir = current_app.config.get('CHALLENGE_PICTURES_DIR', CHALLENGE_PICTURES_DIR)
                    os.makedirs(upload_dir, exist_ok=True)
                    save_path = os.path.join(upload_dir, newfilename)
                    picture.save(save_path)
                    if secret_mission.icon is not None:
                        old_path = os.path.join(upload_dir, secret_mission.icon)
                        if os.path.exists(old_path):
                            os.remove(old_path)
                    secret_mission.icon = newfilename
                    db.session.commit()
                    return jsonify(secret_mission.to_dict()) 
                else:
                    abort(404, message='Secret mission not found.')
        
        except ValidationError as error:
            traceback.print_exc()
            abort(400, message=str(error))

        except KeyError as error:
            traceback.print_exc()
            abort(400, message='Picture needed.')

        except NotFound as error:
            abort(404, message='Title not found.')

        except Exception as error:
            traceback.print_exc()
            db.session.rollback()
            abort(500, message='Internal server error.')

    
    @login_required
    @blp.arguments(TitleSecretMissionSchema, location='query')
    @blp.response(200, description='Icon found.')
    @blp.response(204, description='Icon not found.')
    @blp.response(400, description='Bad request')
    @blp.response(401, description='Invalid token')
    @blp.response(403, description='You do not have permission for this operation')
    @blp.response(404, description='Secret mission not found.')
    @blp.response(500, description='Internal server error.')
    def get(self, data):
        try: 
            data = GetSecretMissionSchema().load(data)
            getTitle = data.get('title')
            if getTitle is None :
                abort(400, message='Title is required.')
            secret_mission = SecretMission.query.get(getTitle)
            if secret_mission is None:
                abort(404, message='Secret Mission not found.')
            if secret_mission.icon is None:
                return Response(status=204)  # No content if no icon is set
            else:
                upload_dir = current_app.config.get('CHALLENGE_PICTURES_DIR', CHALLENGE_PICTURES_DIR)
                icon_path = os.path.join(upload_dir, secret_mission.icon)
                if not os.path.exists(icon_path):
                    abort(404, message='Icon file not found.')
                return send_from_directory(upload_dir, secret_mission.icon, as_attachment=False)
                
        except ValidationError as error:
            traceback.print_exc()
            abort(400, message=str(error))

        except NotFound as error:
            abort(404, message='Secret mission not found.')
        
        except Exception as error:
            traceback.print_exc()
            db.session.rollback()
            abort(500, message='Internal server error.')
