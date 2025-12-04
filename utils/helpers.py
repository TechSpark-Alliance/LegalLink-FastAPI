from datetime import datetime
from bson import ObjectId


def convert_objectid(document: dict) -> dict:
    """Recursively convert ObjectId and datetime values to JSON-serializable."""
    def convert(value):
        if isinstance(value, ObjectId):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, list):
            return [convert(v) for v in value]
        if isinstance(value, dict):
            return {k: convert(v) for k, v in value.items()}
        return value

    return convert(document)
