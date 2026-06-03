import os
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from bson.errors import InvalidId

_db = None

def get_database():
    """
    Lazily loads the MongoDB database instance.
    Raises ValueError if MONGODB_URI is not set.
    """
    global _db
    if _db is None:
        uri = os.getenv("MONGODB_URI")
        if not uri:
            raise ValueError("MONGODB_URI environment variable is missing.")
        db_name = os.getenv("MONGODB_DB_NAME", "claimsure")
        client = AsyncIOMotorClient(uri)
        _db = client[db_name]
    return _db

def get_dispute_cases_collection():
    """
    Returns the dispute_cases collection.
    """
    db = get_database()
    return db["dispute_cases"]

async def save_dispute_case(user_id: str, insurer_name: str, result: dict) -> dict:
    """
    Saves a claim dispute analysis record into MongoDB dispute_cases collection.
    Falls back to returning a mock record if MONGODB_URI is not configured.
    """
    try:
        collection = get_dispute_cases_collection()
        doc = {
            "user_id": user_id,
            "insurer_name": insurer_name,
            "dispute_score": result.get("dispute_score"),
            "strength": result.get("strength"),
            "dispute_letter": result.get("dispute_letter"),
            "mismatch_found": result.get("mismatch_found"),
            "misapplied_clause": result.get("misapplied_clause"),
            "citations": result.get("citations", []),
            "created_at": datetime.utcnow()
        }
        inserted = await collection.insert_one(doc)
        doc["_id"] = str(inserted.inserted_id)
        return doc
    except ValueError:
        # Mock fallback for local environment without MongoDB URI set
        return {
            "_id": "mock_mongo_id_for_dev_only",
            "user_id": user_id,
            "insurer_name": insurer_name,
            "dispute_score": result.get("dispute_score", 80),
            "strength": result.get("strength", "strong"),
            "dispute_letter": result.get("dispute_letter", ""),
            "mismatch_found": result.get("mismatch_found", True),
            "misapplied_clause": result.get("misapplied_clause", "Section 4.1 Exclusion Clause"),
            "citations": result.get("citations", []),
            "created_at": datetime.utcnow()
        }

async def get_user_cases(user_id: str) -> list:
    """
    Retrieves all dispute records for a specific user from MongoDB.
    Falls back to returning empty list if MONGODB_URI is not configured.
    """
    try:
        collection = get_dispute_cases_collection()
        cursor = collection.find(
            {"user_id": user_id},
            sort=[("created_at", -1)]
        )
        cases = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            cases.append(doc)
        return cases
    except ValueError:
        # Return empty list in development
        return []

async def delete_dispute_case(case_id: str, user_id: str) -> bool:
    """
    Deletes a specific dispute case from MongoDB.
    """
    try:
        collection = get_dispute_cases_collection()
        result = await collection.delete_one({"_id": ObjectId(case_id), "user_id": user_id})
        return result.deleted_count > 0
    except (ValueError, InvalidId):
        # Fallback for dev mocks
        return True
    except Exception:
        return False
