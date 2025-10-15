import asyncio
from telegram import Bot

BOT_TOKEN = '8339195903:AAG574Lcbk7WRpSFJuP1WPWLJiHE0LCZPqo'  # Your bot token

async def delete_webhook():
    bot = Bot(token=BOT_TOKEN)
    result = await bot.delete_webhook()
    print(f"Webhook deleted: {result}")

if __name__ == '__main__':
    asyncio.run(delete_webhook())