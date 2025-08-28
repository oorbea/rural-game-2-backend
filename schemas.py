from marshmallow import INCLUDE, RAISE, Schema, ValidationError, fields, validate, validates, validates_schema
from enums.GenderEnum import GenderEnum
from enums.TurnType import TurnTypeEnum
class ChallengeSchema(Schema):
    """Schema for validating challenge data."""
    title = fields.String(required=True, validate=validate.Length(min=1, max=100))
    description = fields.String(required=True, validate=validate.Length(min=1, max=500))
    drinking = fields.Boolean(required=False, load_default=False)
    sex = fields.Boolean(required=False, load_default=False)
    smoking = fields.Boolean(required=False, load_default=False)
    partner_friendly = fields.Boolean(required=False, load_default=True)
    probability = fields.Float(required=False, load_default=1.0)
    icon = fields.String(required=False, allow_none=True, load_default=None)
    skipping = fields.Float(required=False, allow_none=True, load_default=None)
    voting = fields.Boolean(required=False, load_default=False)
    prize = fields.Integer(required=True)
    males = fields.Integer(required=False, allow_none=True, metadata={"description": "Number of male players required. Do not stablish this, it will be calculated automatically from the description."})
    females = fields.Integer(required=False, allow_none=True, metadata={"description": "Number of female players required. Do not stablish this, it will be calculated automatically from the description."})

class GetChallengeSchema(Schema):
    """Schema for validating challenge data."""
    class Meta:
        unknown = RAISE
    title = fields.String(required=False, validate=validate.Length(min=1, max=100))
    description = fields.String(required=False, validate=validate.Length(min=1, max=500))
    drinking = fields.Boolean(required=False)
    sex = fields.Boolean(required=False)
    smoking = fields.Boolean(required=False)
    partner_friendly = fields.Boolean(required=False)
    probability = fields.Float(required=False)
    icon = fields.String(required=False, allow_none=True)
    skipping = fields.Float(required=False, allow_none=True)
    voting = fields.Boolean(required=False)
    prize = fields.Integer(required=False)
    males = fields.Integer(required=False, allow_none=True)
    females = fields.Integer(required=False, allow_none=True)

class TitleChallengeSchema(Schema):
    """Schema for validating challenge data."""
    title = fields.String(required=True, validate=validate.Length(min=1, max=100))
    
class GroupChallengeSchema(ChallengeSchema):
    """Schema for validating group challenge data."""
    title = fields.String(required=True, validate=validate.Length(min=1, max=100))
    description = fields.String(required=True, validate=validate.Length(min=1, max=500))
    teams = fields.Integer(required=True)
    player_quantity = fields.Integer(required=False, metadata={"description": "Number of players per group. Do not stablish this, it will be calculated automatically from the description."})
    drinking = fields.Boolean(required=False, load_default=False)
    sex = fields.Boolean(required=False, load_default=False)
    smoking = fields.Boolean(required=False, load_default=False)
    partner_friendly = fields.Boolean(required=False, load_default=True)
    probability = fields.Float(required=False, load_default=1.0)
    icon = fields.String(required=False, allow_none=True, load_default=None)
    skipping = fields.Float(required=False, allow_none=True, load_default=None)
    voting = fields.Boolean(required=False, load_default=False)
    prize = fields.Integer(required=True)
    males = fields.Integer(required=False, allow_none=True, metadata={"description": "Number of male players required. Do not stablish this, it will be calculated automatically from the description."})
    females = fields.Integer(required=False, allow_none=True, metadata={"description": "Number of female players required. Do not stablish this, it will be calculated automatically from the description."})


class GetGroupChallengeSchema(ChallengeSchema):
    """Schema for validating group challenge data."""
    class Meta:
        unknown = RAISE
    title = fields.String(required=False, validate=validate.Length(min=1, max=100))
    description = fields.String(required=False, validate=validate.Length(min=1, max=500))
    teams = fields.Integer(required=False)
    player_quantity = fields.Integer(required=False)
    drinking = fields.Boolean(required=False)
    sex = fields.Boolean(required=False)
    smoking = fields.Boolean(required=False)
    partner_friendly = fields.Boolean(required=False)
    probability = fields.Float(required=False)
    icon = fields.String(required=False, allow_none=True)
    skipping = fields.Float(required=False, allow_none=True)
    voting = fields.Boolean(required=False)
    prize = fields.Integer(required=False)
    males = fields.Integer(required=False, allow_none=True)
    females = fields.Integer(required=False, allow_none=True)

class TitleGroupChallengeSchema(Schema):
    """Schema for validating group challenge data."""
    title = fields.String(required=True, validate=validate.Length(min=1, max=100))

class SecretMissionSchema(Schema):
    """Schema for validating secret mission data."""
    title = fields.String(required=True, validate=validate.Length(min=1, max=100))
    description = fields.String(required=True, validate=validate.Length(min=1, max=500))
    drinking = fields.Boolean(required=False, load_default=False)
    smoking = fields.Boolean(required=False, load_default=False)
    partner_friendly = fields.Boolean(required=False, load_default=True)
    probability = fields.Float(required=False, load_default=1.0)
    icon = fields.String(required=False, allow_none=True, load_default=None)
    prize = fields.Integer(required=True)
    punishment = fields.Float(required=True)
    males = fields.Integer(required=False, allow_none=True, metadata={"description": "Number of male players required. Do not stablish this, it will be calculated automatically from the description."})
    females = fields.Integer(required=False, allow_none=True, metadata={"description": "Number of female players required. Do not stablish this, it will be calculated automatically from the description."})

class GetSecretMissionSchema(Schema):
    """Schema for validating secret mission data."""
    class Meta:
        unknown = RAISE
    title = fields.String(required=False, validate=validate.Length(min=1, max=100))
    description = fields.String(required=False, validate=validate.Length(min=1, max=500))
    drinking = fields.Boolean(required=False)
    smoking = fields.Boolean(required=False)
    partner_friendly = fields.Boolean(required=False)
    probability = fields.Float(required=False)
    icon = fields.String(required=False, allow_none=True)
    prize = fields.Integer(required=False)
    punishment = fields.Float(required=False)
    males = fields.Integer(required=False, allow_none=True)
    females = fields.Integer(required=False, allow_none=True)

class TitleSecretMissionSchema(Schema):
    """Schema for validating secret mission data."""
    title = fields.String(required=True, validate=validate.Length(min=1, max=100))

class PlayerInfoSchema(Schema):
    """Schema for validating player info."""
    username = fields.String(required=True)
    drinking = fields.Boolean(required=True)
    smoking = fields.Boolean(required=True)
    partnered = fields.Boolean(required=True)
    virgin = fields.Boolean(required=True)
    gender = fields.String(required=True, validate=validate.OneOf([member.value for member in GenderEnum]))
    profile_pic = fields.String(required=False, allow_none=True, load_default=None)

class CodeAndPlayerSchema(Schema):
    """Schema for validating code and player data."""
    code = fields.String(required=True, validate=validate.Length(equal=4))
    player = fields.Nested(PlayerInfoSchema, required=True)

class CodeAndUsernameSchema(Schema):
    """Schema for validating code and username data."""
    player_name = fields.String(required=True)
    code = fields.String(required=True, validate=validate.Length(equal=4))

class CodeAndTurnTypeSchema(Schema):
    """Schema for validating code and turn type data."""
    code = fields.String(required=True, validate=validate.Length(equal=4))
    turn_type = fields.String(required=True, validate=validate.OneOf([member.value for member in TurnTypeEnum]))

class CodeAndDescriptionSchema(Schema):
    """Schema for validating code and description data."""
    code = fields.String(required=True, validate=validate.Length(equal=4))
    description = fields.String(required=True)

class SkipTurnSchema(Schema):
    """Schema for validating skip turn data."""
    code = fields.String(required=True, validate=validate.Length(equal=4))
    player_name = fields.String(required=True)
    turn_type = fields.String(required=True, validate=validate.OneOf([member.value for member in TurnTypeEnum]))
    title = fields.String(required=True, validate=validate.Length(min=1, max=100))

class UpdatePlayerSchema(Schema):
    """Schema for validating player updates."""
    current_username = fields.String(required=True)
    code = fields.String(required=True, validate=validate.Length(equal=4))
    new_username = fields.String(required=False)
    drinking = fields.Boolean(required=False)
    smoking = fields.Boolean(required=False)
    partnered = fields.Boolean(required=False)
    virgin = fields.Boolean(required=False)
    gender = fields.String(required=False, validate=validate.OneOf([member.value for member in GenderEnum]))
    profile_pic = fields.String(required=False, allow_none=True, load_default=None)

class RoleSchema(Schema):
    """Schema for validating role data."""
    title = fields.String(required=True, validate=validate.Length(min=1, max=100))
    description = fields.String(required=True, validate=validate.Length(min=1, max=500))
    quantity_per_game = fields.Integer(required=False, allow_none=True)
    priority = fields.Integer(required=True, validate=validate.Range(min=1, max=5))

class GetRoleSchema(Schema):
    """Schema for validating role data."""
    class Meta:
        unknown = RAISE
    title = fields.String(required=False, validate=validate.Length(min=1, max=100))
    description = fields.String(required=False, validate=validate.Length(min=1, max=500))
    quantity_per_game = fields.Integer(required=False, allow_none=True, load_default=None)
    priority = fields.Integer(required=False, validate=validate.Range(min=1, max=5))

class TitleRoleSchema(Schema):
    """Schema for validating role data."""
    title = fields.String(required=True, validate=validate.Length(min=1, max=100))

class TargetChallengeSchema(Schema):
    """Schema for validating target challenge data."""
    title = fields.String(required=True, validate=validate.Length(min=1, max=100))
    description = fields.String(required=True, validate=validate.Length(min=1, max=500))
    drinking = fields.Boolean(required=False, load_default=False)
    sex = fields.Boolean(required=False, load_default=False)
    smoking = fields.Boolean(required=False, load_default=False)
    partner_friendly = fields.Boolean(required=False, load_default=True)
    probability = fields.Float(required=False, load_default=1.0)
    icon = fields.String(required=False, allow_none=True, load_default=None)
    skipping = fields.Float(required=False, allow_none=True, load_default=None)
    voting = fields.Boolean(required=False, load_default=False)
    prize = fields.Integer(required=True)
    males = fields.Integer(required=False, allow_none=True, metadata={"description": "Number of male players required. Do not stablish this, it will be calculated automatically from the description."})
    females = fields.Integer(required=False, allow_none=True, metadata={"description": "Number of female players required. Do not stablish this, it will be calculated automatically from the description."})
    player_quantity = fields.Integer(required=False, metadata={"description": "Number of players required. Do not stablish this, it will be calculated automatically from the description."})
    group_challenge = fields.Boolean(required=False, load_default=False)

class GetTargetChallengeSchema(Schema):
    """Schema for validating target challenge data."""
    class Meta:
        unknown = RAISE
    title = fields.String(required=False, validate=validate.Length(min=1, max=100))
    description = fields.String(required=False, validate=validate.Length(min=1, max=500))
    drinking = fields.Boolean(required=False)
    sex = fields.Boolean(required=False)
    smoking = fields.Boolean(required=False)
    partner_friendly = fields.Boolean(required=False)
    probability = fields.Float(required=False)
    icon = fields.String(required=False, allow_none=True)
    skipping = fields.Float(required=False, allow_none=True)
    voting = fields.Boolean(required=False)
    prize = fields.Integer(required=False)
    males = fields.Integer(required=False, allow_none=True)
    females = fields.Integer(required=False, allow_none=True)
    player_quantity = fields.Integer(required=False)
    group_challenge = fields.Boolean(required=False)

class TitleTargetChallengeSchema(Schema):
    """Schema for validating target challenge data."""
    title = fields.String(required=True, validate=validate.Length(min=1, max=100))