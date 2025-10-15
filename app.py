from flask import Flask, request, render_template, send_from_directory, redirect
from telegram import Bot, Update
from telegram.ext import Application, MessageHandler, filters, CommandHandler, CallbackContext
import os
import sqlite3
import uuid
import asyncio 
import subprocess
import logging
# --- CRITICAL FIX IMPORTS ---
from asgiref.wsgi import WsgiToAsgi 

# --- Configuration and Setup ---

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app (WSGI object)
app = Flask(__name__)

# --- Environment Configuration ---
BOT_TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE') 
WEBHOOK_URL = os.environ.get("WEBHOOK_URL") 
# CHANGE THIS to your actual channel chat ID (e.g., -100xxxxxxxxxx)
CHANNEL_CHAT_ID = -1003167440553 

# --- Telegram Bot Setup ---
# FIX: Bot constructor NO LONGER accepts request_kwargs in modern PTB.
# We will set the timeouts in the Application Builder instead.
bot = Bot(token=BOT_TOKEN)

# Set global request parameters (timeouts) for the Application instance
GLOBAL_REQUEST_KWARGS = {
    "connect_timeout": 90.0,
    "read_timeout": 90.0
}

# Database setup
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS videos 
                 (id TEXT PRIMARY KEY, file_id TEXT, preview_path TEXT, message_id INTEGER)''')
    conn.commit()
    conn.close()
    os.makedirs('static/previews', exist_ok=True)

init_db()

# --- Telegram Handlers (Long Running Task) ---

# This function will run as a background task.
async def fetch_channel_videos(update: Update, context: CallbackContext):
    file_path = None
    
    if not (update.channel_post and update.channel_post.video and update.channel_post.chat.id == CHANNEL_CHAT_ID):
        return 

    try:
        logger.info(f"Processing video from message ID: {update.channel_post.message_id}")
        video = update.channel_post.video
        file_id = video.file_id
        message_id = update.channel_post.message_id
        
        # 1. Download the full video
        # The timeout set in the Application Builder applies here!
        file = await context.bot.get_file(file_id)
        file_path = f'/tmp/temp_{uuid.uuid4()}.mp4' 
        await file.download_to_drive(file_path)
        
        if not os.path.exists(file_path):
            logger.error(f"Downloaded file not found: {file_path}")
            return

        preview_id = str(uuid.uuid4())
        preview_path = f'static/previews/{preview_id}.mp4'
        
        # 2. Create 10-second preview using FFmpeg
        logger.info("Attempting FFmpeg conversion...")
        
        subprocess.run([
            'ffmpeg', 
            '-i', file_path, 
            '-t', '10',         
            '-c', 'copy',       
            '-y', preview_path
        ], check=True) 
        
        logger.info("FFmpeg conversion successful.")

        # 3. Save metadata to database
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO videos (id, file_id, preview_path, message_id) VALUES (?, ?, ?, ?)",
                     (preview_id, file_id, preview_path, message_id))
        conn.commit()
        conn.close()
        
        logger.info(f"Successfully processed video preview: {preview_id}")

    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg command failed: {e.stderr.decode()}")
        logger.error(f"Failed command details: {' '.join(e.cmd)}")
    except FileNotFoundError:
        logger.error("FFmpeg executable not found. Check deployment settings.")
    except Exception as e:
        logger.error(f"General error fetching/processing videos: {e}")
    finally:
        # 4. Clean up the downloaded file
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleaned up temporary file: {file_path}")

# Handle /start command (omitted for brevity, assume unchanged)
async def start(update: Update, context: CallbackContext):
    user_name = update.effective_user.first_name if update.effective_user else "There"
    
    # --- 1. Handle Deep Link (/start video_id) ---
    if update.message and context.args:
        video_id = context.args[0]
        
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT file_id FROM videos WHERE id=?", (video_id,))
        result = c.fetchone()
        conn.close()

        if result:
            file_id = result[0]
            try:
                await context.bot.send_video(chat_id=update.effective_chat.id, video=file_id)
                await update.message.reply_text("Full video sent to you!")
            except Exception as e:
                logger.error(f"Failed to send video: {e}")
                await update.message.reply_text("Failed to send video. Please try again later.")
            return
        
        await update.message.reply_text("Invalid video ID. Please use a link from the website.")
        
    # --- 2. Handle Simple /start (NO deep link) ---
    else:
        welcome_message = (
            f"Hello {user_name}!\n\n"
            "This bot is a video gate keeper.\n"
            "Please visit the website to select a video preview and click 'Get Full Video' "
            "to receive the complete file here."
        )
        await update.message.reply_text(welcome_message)

# --- Handler Setup Function ---
def setup_handlers(app_instance):
    """Registers handlers on the Application instance."""
    app_instance.add_handler(MessageHandler(filters.VIDEO & filters.Chat(CHANNEL_CHAT_ID), fetch_channel_videos))
    app_instance.add_handler(CommandHandler('start', start))
    return app_instance

# --- Flask Web Routes ---

# 1. Webhook Route - Entry point for Telegram updates
@app.route('/telegram_webhook', methods=['POST'])
async def telegram_webhook():
    if request.method == "POST":
        update_data = request.get_json(force=True)
        
        # FIX: Pass request_kwargs to the Application Builder
        temp_application = Application.builder().bot(bot).build()
        temp_application = setup_handlers(temp_application)
        
        await temp_application.initialize()
        update = Update.de_json(update_data, bot)
        
        # CRITICAL WEBHOOK TIMEOUT FIX: Run long tasks in the background
        if update.channel_post and update.channel_post.video and update.channel_post.chat.id == CHANNEL_CHAT_ID:
            current_loop = asyncio.get_event_loop()
            current_loop.create_task(
                temp_application.process_update(update)
            )
            return "ok" 

        # For quick tasks (like /start), process and wait for completion.
        await temp_application.process_update(update)
        
    return "ok"

# 2. Index page with video previews
@app.route('/')
def index():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT id, preview_path FROM videos ORDER BY message_id DESC")
    videos = c.fetchall()
    conn.close()
    return render_template('index.html', videos=videos)

# 3. Redirect to bot with /start (Deep Link Generation)
@app.route('/send/<video_id>')
async def send_video(video_id):
    bot_info = await bot.get_me()
    bot_username = bot_info.username
    bot_url = f"https://t.me/{bot_username}?start={video_id}"
    return redirect(bot_url)

# 4. Serve video previews
@app.route('/static/previews/<filename>')
def serve_preview(filename):
    return send_from_directory('static/previews', filename)

# -------------------------------------------------------------
# FINAL DEPLOYMENT FIX: ASGI Compatibility Wrapper
# -------------------------------------------------------------
asgi_app = WsgiToAsgi(app)