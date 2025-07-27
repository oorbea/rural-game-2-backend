import datetime
import os
import traceback
from flask_smorest import Blueprint
from flask.views import MethodView
from flask import Response, current_app, jsonify, request, abort
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from db import db 
from werkzeug.exceptions import NotFound
from werkzeug.utils import secure_filename
from globals import ALLOWED_PICTURE_EXTENSIONS, PROFILE_PICTURES_DIR
from models.Challenge import Challenge
from schemas import ChallengeSchema, GetChallengeSchema, TitleChallengeSchema

blp = Blueprint('challenge', __name__, description='Challenge related CRUD operations.')

@blp.route('')
class ChallengeCRUD(MethodView):
    """Handles CRUD operations for challenges."""
    @blp.arguments(GetChallengeSchema, location='query')
    @blp.response(200, ChallengeSchema(many=True))
    @blp.response(400, description='Bad request')
    @blp.response(500, description='Internal server error.')
    def get(self, data):
        try: 
            data = GetChallengeSchema().load(data)
            filters = []
            getTitle = request.args.get('title')
            if getTitle is not None :
                filters.append(Challenge.title == getTitle)

            getDescription = request.args.get('description')
            if getDescription is not None :
                filters.append(Challenge.description == getDescription)

            getSex = request.args.get('sex')
            if getSex is not None :
                filters.append(Challenge.sex == getSex)

            getDrink = request.args.get('drinking')
            if getDrink is not None :
                filters.append(Challenge.drinking == getDrink)

            getSmoking = request.args.get('smoking')
            if getSmoking is not None :
                filters.append(Challenge.smoking == getSmoking)
            
            getPartnerFriendly = request.args.get('partner_friendly')
            if getPartnerFriendly is not None :
                filters.append(Challenge.partner_friendly == getPartnerFriendly)
            
            getProbability = request.args.get('probability')
            if getProbability is not None :
                filters.append(Challenge.probability == getProbability)
            
            getSkipping = request.args.get('skipping')
            if getSkipping is not None :
                if getSkipping.lower() == 'null':
                    filters.append(Challenge.skipping is None)
                else:
                    filters.append(Challenge.skipping == getSkipping)

            getVoting = request.args.get('voting')
            if getVoting is not None :
                filters.append(Challenge.voting == getVoting)

            getPrize = request.args.get('prize')
            if getPrize is not None :
                filters.append(Challenge.prize == getPrize)

            if len(filters) > 0:
                challenges = Challenge.query.filter(or_(*filters)).all()
            else:
                challenges = Challenge.query.all()
            return jsonify([challenge.to_dict() for challenge in challenges])
        
        except ValidationError as error:
            traceback.print_exc()
            abort(400, description=str(error))

        except Exception as error:
            traceback.print_exc()
            abort(500, description='Internal server error.')

    @blp.arguments(ChallengeSchema)
    @blp.response(201, description='Challenge created.')
    @blp.response(400, description='Bad request')
    @blp.response(409, description='Conflict.')
    @blp.response(500, description='Internal server error.')
    def post(self, data): 
        try:
            data = ChallengeSchema().load(data) 
            challenge = Challenge(**data)
            db.session.add(challenge) 
            db.session.commit()
            return Response(status=201)

        except ValidationError as error:
            traceback.print_exc()
            abort(400, description=str(error))

        except IntegrityError as error:
            db.session.rollback()
            abort(409, description='Challenge with the same title already exists.')

        except Exception as error:
            traceback.print_exc()
            db.session.rollback()
            abort(500, description='Internal server error.')

    @blp.arguments(ChallengeSchema)
    @blp.arguments(TitleChallengeSchema, location='query')
    @blp.response(204, description='Challenge updated.')
    @blp.response(400, description='Bad request')
    @blp.response(404, description='Title not found.')
    @blp.response(500, description='Internal server error.')
    def put(self, bodydata, querydata):
        try:
            querydata = TitleChallengeSchema().load(querydata) 
            challenge = Challenge.query.get(querydata.get("title"))
            if challenge is not None:
                bodydata = ChallengeSchema().load(bodydata) 
                for key, value in bodydata.items():
                    if hasattr(challenge, key):
                        setattr(challenge, key, value)
                db.session.commit()
                return Response(status=204)
            else:
                abort(404, description='Title not found.')

        except ValidationError as error:
            traceback.print_exc()
            abort(400, description=str(error))

        except NotFound as error:
            abort(404, description='Title not found.')

        except Exception as error:
            traceback.print_exc()
            db.session.rollback()
            abort(500, description='Internal server error.')

    @blp.arguments(GetChallengeSchema)
    @blp.arguments(TitleChallengeSchema, location='query')
    @blp.response(200, ChallengeSchema, description='Challenge updated.')
    @blp.response(400, description='Bad request')
    @blp.response(404, description='Title not found.')
    @blp.response(500, description='Internal server error.')
    def patch(self, bodydata, querydata):
        try:
            querydata = TitleChallengeSchema().load(querydata) 
            challenge = Challenge.query.get(querydata.get("title"))
            if challenge is not None:
                bodydata = GetChallengeSchema().load(bodydata) 
                for key, value in bodydata.items():
                    if hasattr(challenge, key):
                        setattr(challenge, key, value)
                db.session.commit()
                return jsonify(challenge.to_dict()) 
            else:
                abort(404, description='Title not found.')
        
        except ValidationError as error:
            traceback.print_exc()
            abort(400, description=str(error))

        except NotFound as error:
            abort(404, description='Title not found.')

        except Exception as error:
            traceback.print_exc()
            db.session.rollback()
            abort(500, description='Internal server error.')


    @blp.arguments(TitleChallengeSchema, location='query')
    @blp.response(204, description='Challenge deleted.')
    @blp.response(400, description='Bad request')
    @blp.response(404, description='Title not found.')
    @blp.response(500, description='Internal server error.')
    def delete(self, data):
        try:
            data = TitleChallengeSchema().load(data) 
            challenge = db.session.get(Challenge, data.get("title"))
            if challenge is not None:
                db.session.delete(challenge)
                db.session.commit()
                return Response(status=204)
            else:
                abort(404, description='Title not found.')

        except ValidationError as error:
            traceback.print_exc()
            abort(400, description=str(error))

        except NotFound as error:
            abort(404, description='Title not found.')

        except Exception as error:
            traceback.print_exc()
            db.session.rollback()
            abort(500, description='Internal server error.')


@blp.route('icon')
class ChallengeImg(MethodView):
    """ """
    def __allowfilename(self, filename: str) -> bool: 
        if "." not in filename:
            return False
        ext = filename.split(".")[-1]
        if ext.lower() not in ALLOWED_PICTURE_EXTENSIONS:
            return False
        return True

    @blp.doc(
        summary="Upload or update your challenge pic",
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
                                "description": "Challenge pic file (png, jpg, jpeg, gif)"
                            }
                        },
                        "required": ["icon"]
                    }
                }
            }
        }
    )
    @blp.arguments(TitleChallengeSchema, location='query')
    @blp.response(200, ChallengeSchema, description='Challenge updated.')
    @blp.response(400, description='Bad request')
    @blp.response(404, description='Title not found.')
    @blp.response(500, description='Internal server error.')
    def patch(self, querydata):
        try:
            if "icon" not in request.files:
                abort(400, description='Picture needed.')

            picture = request.files.get("icon")
            originalfilename = picture.filename.replace(" ", "_")
            newfilename = secure_filename(f"{str(datetime.datetime.now()).replace(" ", "_")}_{originalfilename}") 
            if not self.__allowfilename(newfilename):
                abort(400, description='Picture.')

            querydata = TitleChallengeSchema().load(querydata) 
            challenge = Challenge.query.get(querydata.get("title"))
            if challenge is not None:
                upload_dir = current_app.config.get('PROFILE_PICTURES_DIR', PROFILE_PICTURES_DIR)
                os.makedirs(upload_dir, exist_ok=True)
                save_path = os.path.join(upload_dir, newfilename)
                picture.save(save_path)
                challenge.icon = newfilename
                db.session.commit()
                return jsonify(challenge.to_dict()) 
            else:
                abort(404, description='Title not found.')
        
        except ValidationError as error:
            traceback.print_exc()
            abort(400, description=str(error))

        except NotFound as error:
            abort(404, description='Title not found.')

        except Exception as error:
            traceback.print_exc()
            db.session.rollback()
            abort(500, description='Internal server error.')


            