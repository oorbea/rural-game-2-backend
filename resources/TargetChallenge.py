import datetime
from sqlalchemy import or_
import os
import traceback
from globals import ALLOWED_PICTURE_EXTENSIONS, TARGET_PICTURES_DIR
from helpers.RestrictionAdapter import RestrictionAdapter
from flask import Response, current_app, jsonify, request, send_from_directory
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import NotFound
from werkzeug.utils import secure_filename
from db import db 
from helpers.allow_filename import allowfilename
from helpers.auth.decorators import admin_required, login_required
from models.TargetChallenge import TargetChallenge
from schemas import TargetChallengeSchema, GetTargetChallengeSchema, TitleTargetChallengeSchema

blp = Blueprint("target_challenge", __name__, description="CRUD operations on target challenges")

@blp.route("")
class SecretMissionCRUD(MethodView):
    """CRUD operations for Target Challenges."""

    @login_required
    @blp.arguments(GetTargetChallengeSchema, location="query")
    @blp.response(200, TargetChallengeSchema(many=True))  
    @blp.response(400, description="Bad request")       
    @blp.response(401, description="Invalid token")
    @blp.response(403, description="You do not have permission for this operation")
    @blp.response(500, description="Internal server error.")
    def get(self, data):
        try:
            data = GetTargetChallengeSchema().load(data)
            filters = []
            getTitle = data.get("title")
            if getTitle is not None:
                filters.append(TargetChallenge.title == getTitle)
            
            getDescription = data.get("description")
            if getDescription is not None:
                filters.append(TargetChallenge.description == getDescription)

            getDrinking = data.get("drinking")
            if getDrinking is not None:
                filters.append(TargetChallenge.drinking == getDrinking)
            
            getSex = data.get("sex")
            if getSex is not None:
                filters.append(TargetChallenge.sex == getSex)

            getSmoking = data.get("smoking")
            if getSmoking is not None :
                filters.append(TargetChallenge.smoking == getSmoking)
            
            getPartnerFriendly = data.get('partner_friendly')
            if getPartnerFriendly is not None :
                filters.append(TargetChallenge.partner_friendly == getPartnerFriendly)
            
            getProbability = data.get('probability')
            if getProbability is not None :
                filters.append(TargetChallenge.probability == getProbability)

            getSkipping = data.get("skipping")
            if getSkipping is not None:
                filters.append(TargetChallenge.skipping == getSkipping)
    
            getVoting = data.get("voting")
            if getVoting is not None:
                filters.append(TargetChallenge.voting == getVoting)

            getPrize = data.get('prize')
            if getPrize is not None :
                filters.append(TargetChallenge.prize == getPrize)

            getMales = data.get('males')
            if getMales is not None :
                filters.append(TargetChallenge.males == getMales) 

            getFemales = data.get('females')
            if getFemales is not None :
                filters.append(TargetChallenge.females == getFemales)

            getTeams = data.get("group_challenge")
            if getTeams is not None:
                filters.append(TargetChallenge.group_challenge == getTeams)

            getPlayerQty = data.get("player_quantity")
            if getPlayerQty is not None:
                filters.append(TargetChallenge.player_quantity == getPlayerQty)

            if len(filters) > 0:
                target_challenges = TargetChallenge.query.filter(or_(*filters)).all()
            else:
                target_challenges = TargetChallenge.query.all()
            return jsonify([target_challenge.to_dict() for target_challenge in target_challenges])
        

        except ValidationError as error:
            traceback.print_exc()
            abort(400, message=str(error))

        except Exception:
            traceback.print_exc()
            abort(500, message="Internal server error.")

    @admin_required
    @blp.arguments(TargetChallengeSchema)
    @blp.response(201, description='Target challenge created.')
    @blp.response(400, description='Bad request')
    @blp.response(401, description='Invalid token')
    @blp.response(403, description='You do not have permission for this operation')
    @blp.response(409, description='Conflict.')
    @blp.response(500, description='Internal server error.')
    def post(self, data:dict): 
        try:
            data = TargetChallengeSchema().load(data) 
            description = data.get("description")
            data['males'] = RestrictionAdapter.get_num_males(description)
            data['females'] = RestrictionAdapter.get_num_females(description)
            data['player_quantity'] = RestrictionAdapter.get_num_participants(description)
            target_challenge = TargetChallenge(**data)
            db.session.add(target_challenge) 
            db.session.commit()
            return Response(status=201)

        except ValidationError as error:
            traceback.print_exc()
            abort(400, message=str(error))

        except IntegrityError as error:
            db.session.rollback()
            abort(409, message='A target challenge with the same title already exists.')

        except Exception as error:
            traceback.print_exc()
            db.session.rollback()
            abort(500, message='Internal server error.')

    @admin_required
    @blp.arguments(TargetChallengeSchema)
    @blp.arguments(TitleTargetChallengeSchema, location='query')
    @blp.response(204, description='Target challenge updated.')
    @blp.response(400, description='Bad request')
    @blp.response(401, description='Invalid token')
    @blp.response(403, description='You do not have permission for this operation')
    @blp.response(404, description='Title not found.')
    @blp.response(500, description='Internal server error.')
    def put(self, bodydata, querydata):
        try:
            querydata = TitleTargetChallengeSchema().load(querydata) 
            target_challenge = TargetChallenge.query.get(querydata.get("title"))
            if target_challenge is not None:
                bodydata = TargetChallengeSchema().load(bodydata) 
                for key, value in bodydata.items():
                    if key == 'player_quantity' or key == 'males' or key == 'females':
                        continue
                    if hasattr(target_challenge, key):
                        setattr(target_challenge, key, value)
                        if key == 'description':
                            setattr(target_challenge, 'males', RestrictionAdapter.get_num_males(value))
                            setattr(target_challenge, 'females', RestrictionAdapter.get_num_females(value))
                            setattr(target_challenge, 'player_quantity', RestrictionAdapter.get_num_participants(value))
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
    @blp.arguments(GetTargetChallengeSchema)
    @blp.arguments(TitleTargetChallengeSchema, location='query')
    @blp.response(200, TargetChallengeSchema, description='Target challenge updated.')
    @blp.response(400, description='Bad request')
    @blp.response(401, description='Invalid token')
    @blp.response(403, description='You do not have permission for this operation')
    @blp.response(404, description='Title not found.')
    @blp.response(500, description='Internal server error.')
    def patch(self, bodydata, querydata):
        try:
            querydata = TitleTargetChallengeSchema().load(querydata) 
            target_challenge = TargetChallenge.query.get(querydata.get("title"))
            if target_challenge is not None:
                bodydata = GetTargetChallengeSchema().load(bodydata) 
                for key, value in bodydata.items():
                    if key == 'player_quantity' or key == 'males' or key == 'females':
                        continue
                    if hasattr(target_challenge, key):
                        setattr(target_challenge, key, value)
                        if key == 'description':
                            setattr(target_challenge, 'males', RestrictionAdapter.get_num_males(value))
                            setattr(target_challenge, 'females', RestrictionAdapter.get_num_females(value))
                            setattr(target_challenge, 'player_quantity', RestrictionAdapter.get_num_participants(value))
                db.session.commit()
                return jsonify(target_challenge.to_dict()) 
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
    @blp.arguments(TitleTargetChallengeSchema, location='query')
    @blp.response(204, description='Target challenge deleted.')
    @blp.response(400, description='Bad request')
    @blp.response(401, description='Invalid token')
    @blp.response(403, description='You do not have permission for this operation')
    @blp.response(404, description='Title not found.')
    @blp.response(500, description='Internal server error.')
    def delete(self, data):
        try:
            data = TitleTargetChallengeSchema().load(data) 
            target_challenge = db.session.get(TargetChallenge, data.get("title"))
            if target_challenge is not None:
                db.session.delete(target_challenge)
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
class TargetChallengeImg(MethodView):
    """Handles target challenge icon upload and retrieval."""
    @blp.doc(
        summary="Upload or update your target challenge pic",
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
                                "description": f"Target challenge pic file {str(ALLOWED_PICTURE_EXTENSIONS)}. If not provided, deletes the current icon."
                            }
                        },
                        "required": ["icon"]
                    }
                }
            }
        }
    )
    @admin_required
    @blp.arguments(TitleTargetChallengeSchema, location='query')
    @blp.response(200, TargetChallengeSchema, description='Target challenge updated.')
    @blp.response(400, description='Bad request')
    @blp.response(401, description='Invalid token')
    @blp.response(403, description='You do not have permission for this operation')
    @blp.response(404, description='Title not found.')
    @blp.response(500, description='Internal server error.')
    def patch(self, querydata):
        try:
            querydata = TitleTargetChallengeSchema().load(querydata)
            target_challenge:TargetChallenge = TargetChallenge.query.get(querydata.get("title"))
            picture = request.files["icon"]
            if not picture:
                old_picture = target_challenge.icon
                if old_picture is None:
                    abort(204, message='No icon to delete.')
                else:
                    upload_dir = current_app.config.get('TARGET_PICTURES_DIR', TARGET_PICTURES_DIR)
                    old_path = os.path.join(upload_dir, old_picture)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                    target_challenge.icon = None
                    db.session.commit()
                    return Response(status=204)
            else:
                originalfilename = picture.filename.replace(" ", "_")
                newfilename = secure_filename(f"{str(datetime.datetime.now()).replace(" ", "_")}_{originalfilename}") 
                if not allowfilename(newfilename):
                    abort(400, message='Picture filename not allowed.')
                if target_challenge is not None:
                    upload_dir = current_app.config.get('TARGET_PICTURES_DIR', TARGET_PICTURES_DIR)
                    os.makedirs(upload_dir, exist_ok=True)
                    save_path = os.path.join(upload_dir, newfilename)
                    picture.save(save_path)
                    if target_challenge.icon is not None:
                        old_path = os.path.join(upload_dir, target_challenge.icon)
                        if os.path.exists(old_path):
                            os.remove(old_path)
                    target_challenge.icon = newfilename
                    db.session.commit()
                    return jsonify(target_challenge.to_dict()) 
                else:
                    abort(404, message='Target challenge not found.')
        
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
    @blp.arguments(TitleTargetChallengeSchema, location='query')
    @blp.response(200, description='Icon found.')
    @blp.response(204, description='Icon not found.')
    @blp.response(400, description='Bad request')
    @blp.response(401, description='Invalid token')
    @blp.response(403, description='You do not have permission for this operation')
    @blp.response(404, description='Target challenge not found.')
    @blp.response(500, description='Internal server error.')
    def get(self, data):
        try: 
            data = GetTargetChallengeSchema().load(data)
            getTitle = data.get('title')
            if getTitle is None :
                abort(400, message='Title is required.')
            target_challenge = TargetChallenge.query.get(getTitle)
            if target_challenge is None:
                abort(404, message='Target challenge not found.')
            if target_challenge.icon is None:
                return Response(status=204)  # No content if no icon is set
            else:
                upload_dir = current_app.config.get('TARGET_PICTURES_DIR', TARGET_PICTURES_DIR)
                icon_path = os.path.join(upload_dir, target_challenge.icon)
                if not os.path.exists(icon_path):
                    abort(404, message='Icon file not found.')
                return send_from_directory(upload_dir, target_challenge.icon, as_attachment=False)
                
        except ValidationError as error:
            traceback.print_exc()
            abort(400, message=str(error))

        except NotFound as error:
            abort(404, message='Target challenge not found.')
        
        except Exception as error:
            traceback.print_exc()
            db.session.rollback()
            abort(500, message='Internal server error.')