import asyncio
from telegram import Bot

BOT_TOKEN = '8339195903:AAG574Lcbk7WRpSFJuP1WPWLJiHE0LCZPqo'  # Replace with your actual token
CHANNEL_USERNAME = 'Get_Your_Fun1'  # Without '@'

async def get_channel_chat_id():
    try:
        bot = Bot(token=BOT_TOKEN)
        updates = await bot.get_updates(timeout=30)

        for update in updates:
            if update.channel_post and hasattr(update.channel_post.chat, 'username'):
                if update.channel_post.chat.username == CHANNEL_USERNAME:
                    print(f"✅ Channel Chat ID: {update.channel_post.chat.id}")
                    return update.channel_post.chat.id

        print(f"⚠️ No updates found for @{CHANNEL_USERNAME}.")
        print("Make sure the bot is an admin and you posted after adding it.")
        return None

    except Exception as e:
        print(f"❌ Error fetching chat ID: {e}")
        return None

if __name__ == '__main__':
    chat_id = asyncio.run(get_channel_chat_id())
    if chat_id:
        print(f"✅ Successfully retrieved Chat ID: {chat_id}")
    else:
        print("❌ Failed to retrieve chat ID.")
