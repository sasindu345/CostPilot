from costpilot.shared.exceptions import AppError


class ConversationNotFoundError(AppError):
    status_code = 404
    code = "conversation_not_found"

    def __init__(self) -> None:
        super().__init__("We could not find that conversation.")


class QuestionRejectedError(AppError):
    status_code = 422
    code = "question_rejected"


class DailyLimitReachedError(AppError):
    status_code = 429
    code = "daily_limit_reached"

    def __init__(self) -> None:
        super().__init__("You have reached today's question limit. Please try again tomorrow.")


class ModelUnavailableError(Exception):
    """Gemini cannot be reached right now."""
