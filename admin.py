from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMINS
from database import users_collection, settings_collection
from bot import app, logger

@app.on_message(filters.command("broadcast") & filters.user(ADMINS))
async def broadcast(client, message):
    target = message.text.split(" ", 1)[1] if len(message.text.split()) > 1 else "all"
    users = []
    if target in ["users", "all"]:
        users.extend([u["user_id"] async for u in users_collection.find()])
    if target in ["db_owners", "all"]:
        users.extend([s["user_id"] async for s in settings_collection.find({"db_channels": {"$exists": True}})])
    users = list(set(users))
    msg = await message.reply("Enter the broadcast message:")
    broadcast_msg = (await client.wait_for_message(msg.chat.id, msg.id + 1)).text
    sent = 0
    for user_id in users:
        try:
            await client.send_message(user_id, broadcast_msg)
            sent += 1
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Failed to send broadcast to {user_id}: {e}")
    await msg.reply(f"Broadcast sent to {sent}/{len(users)} users.")

@app.on_message(filters.command("stats") & filters.user(ADMINS))
async def stats(client, message):
    total_users = await users_collection.count_documents({})
    db_owners = await settings_collection.count_documents({"db_channels": {"$exists": True}})
    await message.reply(f"Total Users: {total_users}\nDatabase Owners: {db_owners}")
