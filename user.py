from database import users_collection

async def save_user(user_id):
    await users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id}},
        upsert=True
    )
