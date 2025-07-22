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
    skipping = fields.Integer(required=False, allow_none=True, default=None)
    voting = fields.Boolean(required=False, default=False)
    prize = fields.Integer(required=False, default=0)