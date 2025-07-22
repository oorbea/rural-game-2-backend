from marshmallow import INCLUDE, Schema, ValidationError, fields, validate, validates, validates_schema

class ChallengeSchema(Schema):
    """Schema for validating challenge data."""
    title = fields.String(required=True, validate=validate.Length(min=1, max=100))
    description = fields.String(required=True, validate=validate.Length(min=1, max=500))
    drinking = fields.Boolean(required=False, default=False)
    sex = fields.Boolean(required=False, default=False)
    smoking = fields.Boolean(required=False, default=False)
    partner_friendly = fields.Boolean(required=False, default=True)
    probability = fields.Float(required=False, default=1.0)
    icon = fields.String(required=False, allow_none=True, default=None)
    skipping = fields.Float(required=False, allow_none=True, default=None)
    voting = fields.Boolean(required=False, default=False)
    prize = fields.Integer(required=True)

class GroupChallengeSchema(ChallengeSchema):
    """Schema for validating group challenge data."""
    pass

class SecretMissionSchema(Schema):
    """Schema for validating secret mission data."""
    title = fields.String(required=True, validate=validate.Length(min=1, max=100))
    description = fields.String(required=True, validate=validate.Length(min=1, max=500))
    drinking = fields.Boolean(required=False, default=False)
    sex = fields.Boolean(required=False, default=False)
    smoking = fields.Boolean(required=False, default=False)
    partner_friendly = fields.Boolean(required=False, default=True)
    probability = fields.Float(required=False, default=1.0)
    icon = fields.String(required=False, allow_none=True, default=None)
    prize = fields.Integer(required=True)
    punishment = fields.Float(required=True)

class RoleSchema(Schema):
    """Schema for validating role data."""
    title = fields.String(required=True, validate=validate.Length(min=1, max=100))
    description = fields.String(required=True, validate=validate.Length(min=1, max=500))
    quantity_per_game = fields.Integer(required=False, allow_none=True, default=None)