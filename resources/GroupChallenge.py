import datetime
from sqlalchemy import or_
import os
import traceback
from globals import ALLOWED_PICTURE_EXTENSIONS, GROUPCHALLENGE_PICTURES_DIR
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
from models.GroupChallenge import GroupChallenge
from schemas import GroupChallengeSchema, GetGroupChallengeSchema, TitleGroupChallengeSchema


blp = Blueprint("group_challenge", __name__, description="CRUD operations on group challenges")

@blp.route("")
class GroupChallengeCRUD(MethodView):
    """CRUD operations for Group Challenges."""

    @login_required
    @blp.arguments(GetGroupChallengeSchema, location='query')
    @blp.response(200, GroupChallengeSchema(many=True))
    @blp.response(400, description="Bad request")       
    @blp.response(401, description="Invalid token")
    @blp.response(403, description="You do not have permission for this operation")
    @blp.response(500, description="Internal server error.")
    def get(self, data):
        try:
            data = GetGroupChallengeSchema().load(data)
            filters = []
            getTitle = data.get('title')
            if getTitle is not None:
                filters.append(GroupChallenge.title == getTitle)

            getDescription = data.get("description")
            if getDescription is not None:
                filters.append(GroupChallenge.description == getDescription)
            
            getTeams = data.get("teams")
            if getTeams is not None:
                filters.append(GroupChallenge.teams == getTeams)

            getPlayerQty = data.get("player_quantity")
            if getPlayerQty is not None:
                filters.append(GroupChallenge.player_quantity == getPlayerQty)

            getDrinking = data.get("drinking")
            if getDrinking is not None:
                filters.append(GroupChallenge.drinking == getDrinking)

            getSex = data.get("sex")
            if getSex is not None:
                filters.append(GroupChallenge.sex == getSex)

            getSmoking = data.get("smoking")
            if getSmoking is not None :
                filters.append(GroupChallenge.smoking == getSmoking)
            
            getPartnerFriendly = data.get('partner_friendly')
            if getPartnerFriendly is not None :
                filters.append(GroupChallenge.partner_friendly == getPartnerFriendly)
            
            getProbability = data.get('probability')
            if getProbability is not None :
                filters.append(GroupChallenge.probability == getProbability)

            getPrize = data.get('prize')
            if getPrize is not None :
                filters.append(GroupChallenge.prize == getPrize)

            getSkipping = data.get("skipping")
            if getSkipping is not None:
                filters.append(GroupChallenge.skipping == getSkipping)
    
            getVoting = data.get("voting")
            if getVoting is not None:
                filters.append(GroupChallenge.voting == getVoting)

            getMales = data.get('males')
            if getMales is not None :
                filters.append(GroupChallenge.males == getMales)

            getFemales = data.get('females')
            if getFemales is not None :
                filters.append(GroupChallenge.females == getFemales)

            if len(filters) > 0:
                group_challenges = GroupChallenge.query.filter(or_(*filters)).all()
            else:
                group_challenges = GroupChallenge.query.all()

            return jsonify([group_challenge.to_dict() for group_challenge in group_challenges])

        except Exception as e:
            traceback.print_exc()
            abort(500, message=str(e))

    @admin_required
    @blp.arguments(GroupChallengeSchema)
    @blp.response(201, description='Group challenge created.')
    @blp.response(400, description='Bad request')
    @blp.response(401, description='Invalid token')
    @blp.response(403, description='You do not have permission for this operation')
    @blp.response(409, description='Conflict.')
    @blp.response(500, description='Internal server error.')
    def post(self, data: dict):
        try:
            data = GroupChallengeSchema().load(data) 
            description = data.get("description")
            data['males'] = RestrictionAdapter.get_num_males(description)
            data['females'] = RestrictionAdapter.get_num_females(description)
            data['player_quantity'] = RestrictionAdapter.get_num_participants(description)
            group_challenge = GroupChallenge(**data)
            db.session.add(group_challenge) 
            db.session.commit()
            return Response(status=201)
        
        except ValidationError as error:
            traceback.print_exc()
            abort(400, message=str(error))

        except IntegrityError as error:
            db.session.rollback()
            abort(409, message='Challenge with the same title already exists.')

        except Exception as error:
            traceback.print_exc()
            db.session.rollback()
            abort(500, message='Internal server error.')

    @admin_required
    @blp.arguments(GroupChallengeSchema)
    @blp.arguments(TitleGroupChallengeSchema, location='query')
    @blp.response(204, description='Challenge updated.')
    @blp.response(400, description='Bad request')
    @blp.response(401, description='Invalid token')
    @blp.response(403, description='You do not have permission for this operation')
    @blp.response(404, description='Title not found.')
    @blp.response(500, description='Internal server error.')
    def put(self, bodydata, querydata):
        try:
            querydata = TitleGroupChallengeSchema().load(querydata) 
            group_challenge = GroupChallenge.query.get(querydata.get("title"))
            if group_challenge is not None:
                bodydata = GroupChallengeSchema().load(bodydata) 
                for key, value in bodydata.items():
                    if key == 'player_quantity' or key == 'males' or key == 'females':
                        continue
                    if hasattr(group_challenge, key):
                        setattr(group_challenge, key, value)
                        if key == 'description':
                            setattr(group_challenge, 'males', RestrictionAdapter.get_num_males(value))
                            setattr(group_challenge, 'females', RestrictionAdapter.get_num_females(value))
                            setattr(group_challenge, 'player_quantity', RestrictionAdapter.get_num_participants(value))
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
    @blp.arguments(GetGroupChallengeSchema)
    @blp.arguments(TitleGroupChallengeSchema, location='query')
    @blp.response(200, GroupChallengeSchema, description='Challenge updated.')
    @blp.response(400, description='Bad request')
    @blp.response(401, description='Invalid token')
    @blp.response(403, description='You do not have permission for this operation')
    @blp.response(404, description='Title not found.')
    @blp.response(500, description='Internal server error.')
    def patch(self, bodydata, querydata):
        try:
            querydata = TitleGroupChallengeSchema().load(querydata) 
            group_challenge = GroupChallenge.query.get(querydata.get("title"))
            if group_challenge is not None:
                bodydata = GetGroupChallengeSchema().load(bodydata) 
                for key, value in bodydata.items():
                    if key == 'player_quantity' or key == 'males' or key == 'females':
                        continue
                    if hasattr(group_challenge, key):
                        setattr(group_challenge, key, value)
                        if key == 'description':
                            setattr(group_challenge, 'males', RestrictionAdapter.get_num_males(value))
                            setattr(group_challenge, 'females', RestrictionAdapter.get_num_females(value))
                db.session.commit()
                return jsonify(group_challenge.to_dict()) 
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
    @blp.arguments(TitleGroupChallengeSchema, location='query')
    @blp.response(204, description='Challenge deleted.')
    @blp.response(400, description='Bad request')
    @blp.response(401, description='Invalid token')
    @blp.response(403, description='You do not have permission for this operation')
    @blp.response(404, description='Title not found.')
    @blp.response(500, description='Internal server error.')
    def delete(self, data):
        try:
            data = TitleGroupChallengeSchema().load(data) 
            group_challenge = db.session.get(GroupChallenge, data.get("title"))
            if group_challenge is not None:
                db.session.delete(group_challenge)
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
class GroupChallengeImg(MethodView):
    """Handles challenge icon upload and retrieval."""
    @blp.doc(
        summary="Upload or update your group challenge pic",
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
                                "description": f"Group challenge pic file {str(ALLOWED_PICTURE_EXTENSIONS)}. If not provided, deletes the current icon."
                            }
                        },
                        "required": ["icon"]
                    }
                }
            }
        }
    )
    @admin_required
    @blp.arguments(TitleGroupChallengeSchema, location='query')
    @blp.response(200, GroupChallengeSchema, description='GroupChallenge updated.')
    @blp.response(400, description='Bad request')
    @blp.response(401, description='Invalid token')
    @blp.response(403, description='You do not have permission for this operation')
    @blp.response(404, description='Title not found.')
    @blp.response(500, description='Internal server error.')
    def patch(self, querydata):
        try:
            querydata = TitleGroupChallengeSchema().load(querydata)
            group_challenge:GroupChallenge = GroupChallenge.query.get(querydata.get("title"))
            picture = request.files["icon"]
            if not picture:
                old_picture = group_challenge.icon
                if old_picture is None:
                    abort(204, message='No icon to delete.')
                else:
                    upload_dir = current_app.config.get('GROUPCHALLENGE_PICTURES_DIR', GROUPCHALLENGE_PICTURES_DIR)
                    old_path = os.path.join(upload_dir, old_picture)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                    group_challenge.icon = None
                    db.session.commit()
                    return Response(status=204)
            else:
                originalfilename = picture.filename.replace(" ", "_")
                newfilename = secure_filename(f"{str(datetime.datetime.now()).replace(" ", "_")}_{originalfilename}") 
                if not allowfilename(newfilename):
                    abort(400, message='Picture filename not allowed.')
                if group_challenge is not None:
                    upload_dir = current_app.config.get('GROUPCHALLENGE_PICTURES_DIR', GROUPCHALLENGE_PICTURES_DIR)
                    os.makedirs(upload_dir, exist_ok=True)
                    save_path = os.path.join(upload_dir, newfilename)
                    picture.save(save_path)
                    if group_challenge.icon is not None:
                        old_path = os.path.join(upload_dir, group_challenge.icon)
                        if os.path.exists(old_path):
                            os.remove(old_path)
                    group_challenge.icon = newfilename
                    db.session.commit()
                    return jsonify(group_challenge.to_dict()) 
                else:
                    abort(404, message='Group challenge not found.')
        
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
    @blp.arguments(TitleGroupChallengeSchema, location='query')
    @blp.response(200, description='Icon found.')
    @blp.response(204, description='Icon not found.')
    @blp.response(400, description='Bad request')
    @blp.response(401, description='Invalid token')
    @blp.response(403, description='You do not have permission for this operation')
    @blp.response(404, description='Challenge not found.')
    @blp.response(500, description='Internal server error.')
    def get(self, data):
        try: 
            data = GetGroupChallengeSchema().load(data)
            getTitle = data.get('title')
            if getTitle is None :
                abort(400, message='Title is required.')
            group_challenge = GroupChallenge.query.get(getTitle)
            if group_challenge is None:
                abort(404, message='Challenge not found.')
            if group_challenge.icon is None:
                return Response(status=204)  # No content if no icon is set
            else:
                upload_dir = current_app.config.get('GROUPCHALLENGE_PICTURES_DIR', GROUPCHALLENGE_PICTURES_DIR)
                icon_path = os.path.join(upload_dir, group_challenge.icon)
                if not os.path.exists(icon_path):
                    abort(404, message='Icon file not found.')
                return send_from_directory(upload_dir, group_challenge.icon, as_attachment=False)
                
        except ValidationError as error:
            traceback.print_exc()
            abort(400, message=str(error))

        except NotFound as error:
            abort(404, message='Group challenge not found.')
        
        except Exception as error:
            traceback.print_exc()
            db.session.rollback()
            abort(500, message='Internal server error.')