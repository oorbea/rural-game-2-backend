from marshmallow import INCLUDE, RAISE, Schema, ValidationError, fields, validate, validates, validates_schema
from enums.GenderEnum import GenderEnum
from enums.TurnType import TurnTypeEnum

class ChallengeSchema(Schema):
    """Schema for validating challenge data."""
    title = fields.String(required=True, validate=validate.Length(min=1, max=100))
    description = fields.String(
        required=True,
        validate=validate.Length(min=1, max=500),
        metadata={
            "description": (
                "Template text with restriction placeholders. "
                "Use space-delimited tokens in braces: {slot[:token[:token...]]}. "
                "Tokens: gender=male|gender=female, target, Tn/tn (team index). "
                "males/females are auto-derived from gender tokens. "
                "IMPORTANT: placeholders must be standalone words (no punctuation attached to '}'). "
                "Example: 'Kiss {P1:gender=female} and {P2:gender=male}'. "
                "If you want the performer’s name in the text, include a slot with ':target'."
            )
        }
    )
    drinking = fields.Boolean(required=False, load_default=False)
    sex = fields.Boolean(required=False, load_default=False)
    smoking = fields.Boolean(required=False, load_default=False)
    partner_friendly = fields.Boolean(required=False, load_default=True)
    probability = fields.Float(required=False, load_default=1.0)
    icon = fields.String(required=False, allow_none=True, load_default=None)
    skipping = fields.Float(required=False, allow_none=True, load_default=None, validate=validate.Range(min=0.0, max=100.0))
    voting = fields.Boolean(required=False, load_default=False)
    prize = fields.Integer(required=True)
    males = fields.Integer(
        required=False,
        allow_none=True,
        metadata={
            "description": (
                "Auto-computed from description: number of slots tagged with gender=male. "
                "Do not set manually."
            )
        }
    )
    females = fields.Integer(
        required=False,
        allow_none=True,
        metadata={
            "description": (
                "Auto-computed from description: number of slots tagged with gender=female. "
                "Do not set manually."
            )
        }
    )

class GetChallengeSchema(Schema):
    """Schema for validating challenge data."""
    class Meta:
        unknown = RAISE
    title = fields.String(required=False, validate=validate.Length(min=1, max=100))
    description = fields.String(
        required=False,
        validate=validate.Length(min=1, max=500),
        metadata={
            "description": (
                "Same restriction language as ChallengeSchema.description "
                "(see there for full rules and examples)."
            )
        }
    )
    drinking = fields.Boolean(required=False)
    sex = fields.Boolean(required=False)
    smoking = fields.Boolean(required=False)
    partner_friendly = fields.Boolean(required=False)
    probability = fields.Float(required=False)
    icon = fields.String(required=False, allow_none=True)
    skipping = fields.Float(required=False, allow_none=True, validate=validate.Range(min=0.0, max=100.0))
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
    description = fields.String(
        required=True,
        validate=validate.Length(min=1, max=500),
        metadata={
            "description": (
                "Group challenge template with restriction placeholders. "
                "Use {slot[:token...]}; tokens include gender=male|gender=female and Tn/tn to assign teams. "
                "player_quantity is auto-derived as the number of placeholders; males/females are auto-counted "
                "from gender tokens. Team membership is derived from Tn tokens (emitted as Team0, Team1, ...). "
                "IMPORTANT: placeholders must be standalone words (no punctuation attached). "
                "Example: 'Relay race: {A:gender=male:T0} vs {B:gender=female:T1}'."
            )
        }
    )
    teams = fields.Integer(
        required=True,
        metadata={
            "description": (
                "Number of teams for this challenge. Should match the number of distinct team indices present "
                "in the description (e.g., T0/T1 -> 2). When >1 and teams are emitted, the server can trigger "
                "team voting. Team membership itself is derived from the Tn tokens in the description."
            )
        }
    )
    player_quantity = fields.Integer(
        required=False,
        metadata={
            "description": (
                "Auto-computed from description as the count of placeholders (slots). Do not set manually."
            )
        }
    )
    drinking = fields.Boolean(required=False, load_default=False)
    sex = fields.Boolean(required=False, load_default=False)
    smoking = fields.Boolean(required=False, load_default=False)
    partner_friendly = fields.Boolean(required=False, load_default=True)
    probability = fields.Float(required=False, load_default=1.0)
    icon = fields.String(required=False, allow_none=True, load_default=None)
    skipping = fields.Float(required=False, allow_none=True, load_default=None, validate=validate.Range(min=0.0, max=100.0))
    voting = fields.Boolean(required=False, load_default=False)
    prize = fields.Integer(required=True)
    males = fields.Integer(
        required=False,
        allow_none=True,
        metadata={"description": "Auto-computed from gender=male slots in description. Do not set manually."}
    )
    females = fields.Integer(
        required=False,
        allow_none=True,
        metadata={"description": "Auto-computed from gender=female slots in description. Do not set manually."}
    )


class GetGroupChallengeSchema(ChallengeSchema):
    """Schema for validating group challenge data."""
    class Meta:
        unknown = RAISE
    title = fields.String(required=False, validate=validate.Length(min=1, max=100))
    description = fields.String(
        required=False,
        validate=validate.Length(min=1, max=500),
        metadata={"description": "Same restriction language as GroupChallengeSchema.description."}
    )
    teams = fields.Integer(required=False)
    player_quantity = fields.Integer(required=False)
    drinking = fields.Boolean(required=False)
    sex = fields.Boolean(required=False)
    smoking = fields.Boolean(required=False)
    partner_friendly = fields.Boolean(required=False)
    probability = fields.Float(required=False)
    icon = fields.String(required=False, allow_none=True)
    skipping = fields.Float(required=False, allow_none=True, validate=validate.Range(min=0.0, max=100.0))
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
    description = fields.String(
        required=True,
        validate=validate.Length(min=1, max=500),
        metadata={
            "description": (
                "Secret mission template with optional restriction placeholders {slot[:token...]}. "
                "Supported tokens: gender=male|gender=female (for any additional participants). "
                "males/females are auto-derived from gender tokens. "
                "IMPORTANT: placeholders must be standalone words (no punctuation attached)."
            )
        }
    )
    drinking = fields.Boolean(required=False, load_default=False)
    smoking = fields.Boolean(required=False, load_default=False)
    partner_friendly = fields.Boolean(required=False, load_default=True)
    probability = fields.Float(required=False, load_default=1.0)
    icon = fields.String(required=False, allow_none=True, load_default=None)
    prize = fields.Integer(required=True)
    punishment = fields.Float(required=True)
    males = fields.Integer(
        required=False,
        allow_none=True,
        metadata={"description": "Auto-computed from gender=male slots in description. Do not set manually."}
    )
    females = fields.Integer(
        required=False,
        allow_none=True,
        metadata={"description": "Auto-computed from gender=female slots in description. Do not set manually."}
    )


class GetSecretMissionSchema(Schema):
    """Schema for validating secret mission data."""
    class Meta:
        unknown = RAISE
    title = fields.String(required=False, validate=validate.Length(min=1, max=100))
    description = fields.String(
        required=False,
        validate=validate.Length(min=1, max=500),
        metadata={"description": "Same restriction language as SecretMissionSchema.description."}
    )
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
    description = fields.String(
        required=True,
        metadata={
            "description": (
                "Final text used when choosing targets (client-driven). The server extracts the chosen usernames "
                "by reading the content inside braces in order (e.g., '{Alice} ... {Bob}'). "
                "Make sure the number/order of brace blocks matches the original candidate slots; "
                "each chosen username must remain wrapped in braces."
            )
        }
    )

class SkipOrCompleteTurnSchema(Schema):
    """Schema for validating skip turn or complete turn data."""
    code = fields.String(required=True, validate=validate.Length(equal=4))
    player_name = fields.String(required=True)
    turn_type = fields.String(required=True, validate=validate.OneOf([member.value for member in TurnTypeEnum]))
    title = fields.String(required=True, validate=validate.Length(min=1, max=100))

class VoteSchema(Schema):
    """Schema for validating vote data."""
    code = fields.String(required=True, validate=validate.Length(equal=4))
    player_name = fields.String(required=True)
    vote = fields.Integer(required=True, validate=validate.Range(min=0, max=10))

class VoteTeamSchema(Schema):
    """Schema for validating vote data."""
    code = fields.String(required=True, validate=validate.Length(equal=4))
    player_name = fields.String(required=True)
    team = fields.String(
        required=True,
        metadata={"description": "Team name as emitted by the server (e.g., 'Team0', 'Team1')."}
    )

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
    description = fields.String(
        required=True,
        validate=validate.Length(min=1, max=500),
        metadata={
            "description": (
                "Free text. For the special role 'Tortolitos', the backend replaces {player} with the partner "
                "selected as per lobby composition."
            )
        }
    )
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
    description = fields.String(
        required=True,
        validate=validate.Length(min=1, max=500),
        metadata={
            "description": (
                "Target challenge template with restriction placeholders {slot[:token...]}. "
                "Tokens: gender=male|gender=female, target, Tn/tn. "
                "Non-group target: include exactly one ':target' slot to mark the performer; "
                "server will present candidates for that slot, and the client will later submit the chosen names "
                "via 'choose_target'. Group target: candidates are listed per slot; client selects each. "
                "Teams are derived from Tn tokens. player_quantity equals number of slots; "
                "males/females are auto-counted. IMPORTANT: placeholders must be standalone words."
            )
        }
    )
    drinking = fields.Boolean(required=False, load_default=False)
    sex = fields.Boolean(required=False, load_default=False)
    smoking = fields.Boolean(required=False, load_default=False)
    partner_friendly = fields.Boolean(required=False, load_default=True)
    probability = fields.Float(required=False, load_default=1.0)
    icon = fields.String(required=False, allow_none=True, load_default=None)
    skipping = fields.Float(required=False, allow_none=True, load_default=None, validate=validate.Range(min=0.0, max=100.0))
    voting = fields.Boolean(required=False, load_default=False)
    prize = fields.Integer(required=True)
    males = fields.Integer(
        required=False,
        allow_none=True,
        metadata={"description": "Auto-computed from gender=male slots in description. Do not set manually."}
    )
    females = fields.Integer(
        required=False,
        allow_none=True,
        metadata={"description": "Auto-computed from gender=female slots in description. Do not set manually."}
    )
    player_quantity = fields.Integer(
        required=False,
        metadata={"description": "Auto-computed as the number of placeholders (slots). Do not set manually."}
    )
    group_challenge = fields.Boolean(
        required=False,
        load_default=False,
        metadata={
            "description": (
                "If true, the challenge is a group target: the server will expose candidates per slot and teams "
                "from Tn tokens; the client chooses per slot via 'choose_target'. If false, non-group behavior "
                "applies (single ':target' slot recommended)."
            )
        }
    )


class GetTargetChallengeSchema(Schema):
    """Schema for validating target challenge data."""
    class Meta:
        unknown = RAISE
    title = fields.String(required=False, validate=validate.Length(min=1, max=100))
    description = fields.String(
        required=False,
        validate=validate.Length(min=1, max=500),
        metadata={"description": "Same restriction language as TargetChallengeSchema.description."}
    )
    drinking = fields.Boolean(required=False)
    sex = fields.Boolean(required=False)
    smoking = fields.Boolean(required=False)
    partner_friendly = fields.Boolean(required=False)
    probability = fields.Float(required=False)
    icon = fields.String(required=False, allow_none=True)
    skipping = fields.Float(required=False, allow_none=True, validate=validate.Range(min=0.0, max=100.0))
    voting = fields.Boolean(required=False)
    prize = fields.Integer(required=False)
    males = fields.Integer(required=False, allow_none=True)
    females = fields.Integer(required=False, allow_none=True)
    player_quantity = fields.Integer(required=False)
    group_challenge = fields.Boolean(required=False)

class TitleTargetChallengeSchema(Schema):
    """Schema for validating target challenge data."""
    title = fields.String(required=True, validate=validate.Length(min=1, max=100))

class GivePointsSchema(Schema):
    """Schema for validating give points data."""
    code = fields.String(required=True, validate=validate.Length(equal=4))
    player_name = fields.String(required=True)
    points = fields.Integer(required=True)

class JudgeSecretMissionSchema(Schema):
    code = fields.String(required=True, validate=validate.Length(equal=4))
    judge_name = fields.String(required=True)
    player_name = fields.String(required=True)
    mission_title = fields.String(required=True)
    success = fields.Boolean(required=True)

class DetectiveGuessSchema(Schema):
    code = fields.String(required=True, validate=validate.Length(equal=4))
    detective_name = fields.String(required=True)
    target_player = fields.String(required=True)
    guessed_role = fields.String(required=True)