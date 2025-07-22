import traceback
from flask_smorest import Blueprint, abort
from flask.views import MethodView
from flask import jsonify, request
from marshmallow import ValidationError
from sqlalchemy import or_
from models.Challenge import Challenge
from schemas import ChallengeSchema, GetChallengeSchema

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
            abort(400, message=str(error))

        except Exception as error:
            traceback.print_exc()
            abort(500, message='Internal server error.')


            