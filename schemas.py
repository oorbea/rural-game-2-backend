from marshmallow import INCLUDE, RAISE, Schema, ValidationError, fields, validate, validates, validates_schema

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

class GroupChallengeSchema(ChallengeSchema):
    """Schema for validating group challenge data."""
    pass

class SecretMissionSchema(Schema):
    """Schema for validating secret mission data."""
    title = fields.String(required=True, validate=validate.Length(min=1, max=100))
    description = fields.String(required=True, validate=validate.Length(min=1, max=500))
    drinking = fields.Boolean(required=False, load_default=False)
    sex = fields.Boolean(required=False, load_default=False)
    smoking = fields.Boolean(required=False, load_default=False)
    partner_friendly = fields.Boolean(required=False, load_default=True)
    probability = fields.Float(required=False, load_default=1.0)
    icon = fields.String(required=False, allow_none=True, load_default=None)
    prize = fields.Integer(required=True)
    punishment = fields.Float(required=True)

class RoleSchema(Schema):
    """Schema for validating role data."""
    title = fields.String(required=True, validate=validate.Length(min=1, max=100))
    description = fields.String(required=True, validate=validate.Length(min=1, max=500))
    quantity_per_game = fields.Integer(required=False, allow_none=True, load_default=None)