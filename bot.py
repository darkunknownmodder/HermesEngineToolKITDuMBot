import os
import sys
import shutil
import subprocess
import zipfile
import time
import logging
import threading
import urllib.parse
from datetime import datetime
from telebot import TeleBot, types
from pymongo import MongoClient

# --- CONFIGURATION ---
TOKEN = "8536451561:AAFIuJAuATjo0WnzhgQAtV73mFx_0adS-kg"
ADMIN_ID = 7498487211
CHANNEL_USERNAME = "@darkunknownmodder"
CHANNEL_URL = "https://t.me/darkunknownmodder"
WHL_FILE = "hbctool-0.1.5-96-py3-none-any.whl"
IMG_URL = "https://raw.githubusercontent.com/darkepicmoddder/Drive-DeM/refs/heads/main/Img/toolkit.jpg"

# --- MONGODB CONNECTION ---
raw_uri = "mongodb+srv://darkunknownmodder:" + urllib.parse.quote_plus("%#DuM404%App@#%") + "@cluster0.w2fubew.mongodb.net/?appName=Cluster0"
client = MongoClient(raw_uri)
db = client['hermes_ultra_db']
users_col = db['users']

bot = TeleBot(TOKEN, parse_mode="HTML", threaded=True, num_threads=40)
logging.basicConfig(level=logging.INFO)

# --- UI HELPERS ---
def get_progress_bar(percent):
    done = int(percent / 10)
    bar = "█" * done + "░" * (10 - done)
    return f"<b>{bar} {percent}%</b>"

def get_main_keyboard(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("👤 My Profile", callback_data="my_profile")
    btn2 = types.InlineKeyboardButton("📜 All Commands", callback_data="help_cmd")
    btn3 = types.InlineKeyboardButton("📊 Bot Stats", callback_data="bot_stats")
    btn4 = types.InlineKeyboardButton("📢 Channel", url=CHANNEL_URL)
    btn5 = types.InlineKeyboardButton("👤 Developer", url="https://t.me/DarkEpicModderBD0x1")
    markup.add(btn1, btn2)
    markup.add(btn3, btn4)
    markup.add(btn5)
    if user_id == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("🛠 Admin Control Panel", callback_data="admin_panel"))
    return markup

def back_btn():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Back to Menu", callback_data="back_home"))
    return markup

# --- DATABASE LOGIC ---
def sync_user(user):
    user_data = users_col.find_one({"user_id": user.id})
    if not user_data:
        user_data = {
            "user_id": user.id,
            "username": f"@{user.username}" if user.username else "N/A",
            "name": user.first_name,
            "joined_at": datetime.now().strftime("%Y-%m-%d"),
            "status": "active",
            "total_tasks": 0
        }
        users_col.insert_one(user_data)
    else:
        # Update name/username in case they changed
        users_col.update_one({"user_id": user.id}, {"$set": {"name": user.first_name, "username": f"@{user.username}" if user.username else "N/A"}})
    return user_data

def is_banned(user_id):
    u = users_col.find_one({"user_id": user_id})
    return u.get("status") == "banned" if u else False

def check_join(user_id):
    if user_id == ADMIN_ID: return True
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['member', 'administrator', 'creator']
    except: return False

# --- ENGINE SETUP ---
def bootstrap_engine():
    try:
        if os.path.exists(WHL_FILE):
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", WHL_FILE])
        else:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "hbctool"])
        import hbctool.hbc
        if 96 not in hbctool.hbc.HBC:
            latest_v = max(hbctool.hbc.HBC.keys())
            hbctool.hbc.HBC[96] = hbctool.hbc.HBC[latest_v]
    except: pass

# --- COMMAND HANDLERS ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    if is_banned(message.from_user.id):
        return bot.reply_to(message, "🚫 <b>You are restricted from using this bot!</b>")
    
    sync_user(message.from_user)
    
    welcome_text = (
        f"<b>🚀 HERMES ENGINE ULTRA v96 ACTIVE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Welcome:</b> {message.from_user.first_name}\n"
        f"🛠 <b>Engine:</b> <code>Hermes Decompiler/Assembler</code>\n"
        f"💎 <b>Status:</b> <code>Premium Access</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Please select an option below:</i>"
    )
    
    if check_join(message.from_user.id):
        bot.send_photo(message.chat.id, IMG_URL, caption=welcome_text, reply_markup=get_main_keyboard(message.from_user.id))
    else:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Join Channel", url=CHANNEL_URL))
        markup.add(types.InlineKeyboardButton("🔄 Verify Membership", callback_data="verify"))
        bot.send_photo(message.chat.id, IMG_URL, caption="<b>⚠️ ACCESS LOCKED!</b>\nYou must join our official channel to use the decompiler engine.", reply_markup=markup)

# --- CALLBACK QUERY HANDLERS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    user_id = call.from_user.id
    sync_user(call.from_user)

    if call.data == "back_home":
        welcome_text = (
            f"<b>🚀 HERMES ENGINE ULTRA v96 ACTIVE</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Welcome:</b> {call.from_user.first_name}\n"
            f"🛠 <b>Engine:</b> <code>Decompiler/Assembler</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        bot.edit_message_caption(welcome_text, call.message.chat.id, call.message.message_id, reply_markup=get_main_keyboard(user_id))

    elif call.data == "my_profile":
        u = users_col.find_one({"user_id": user_id})
        profile = (
            f"<b>👤 USER PROFILE DATA</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 <b>User ID:</b> <code>{u['user_id']}</code>\n"
            f"🏷 <b>Name:</b> <code>{u['name']}</code>\n"
            f"⚡ <b>Tasks Done:</b> <code>{u['total_tasks']}</code>\n"
            f"📅 <b>Registration:</b> <code>{u['joined_at']}</code>\n"
            f"💎 <b>Plan:</b> <code>PREMIUM</code>"
        )
        bot.edit_message_caption(profile, call.message.chat.id, call.message.message_id, reply_markup=back_btn())
    
    elif call.data == "help_cmd":
        help_text = (
            "<b>📜 ENGINE COMMAND LIST</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚡ <code>/disasmdem</code> - Reply to <i>index.android.bundle</i> to decompile.\n"
            "⚡ <code>/asmdem</code> - Reply to your <i>zipped source</i> to compile.\n"
            "⚡ <code>/start</code> - Refresh the bot interface.\n"
            "⚡ <code>/stats</code> - Show global engine statistics.\n\n"
            "<i>Note: Make sure your zip file structure is correct.</i>"
        )
        bot.edit_message_caption(help_text, call.message.chat.id, call.message.message_id, reply_markup=back_btn())

    elif call.data == "bot_stats":
        total_u = users_col.count_documents({})
        agg = list(users_col.aggregate([{"$group": {"_id": None, "total": {"$sum": "$total_tasks"}}}]))
        total_t = agg[0]['total'] if agg else 0
        stats_text = (
            f"<b>📊 ENGINE GLOBAL STATS</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 Total Users: <code>{total_u}</code>\n"
            f"⚙️ Tasks Completed: <code>{total_t}</code>\n"
            f"🛰 Server Status: <code>Running Smoothly</code>"
        )
        bot.edit_message_caption(stats_text, call.message.chat.id, call.message.message_id, reply_markup=back_btn())

    elif call.data == "verify":
        if check_join(user_id):
            bot.answer_callback_query(call.id, "✅ Verified! Welcome back.", show_alert=True)
            bot.delete_message(call.message.chat.id, call.message.message_id)
            start_cmd(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ Not joined yet! Please join the channel first.", show_alert=True)

    elif call.data == "admin_panel" and user_id == ADMIN_ID:
        adm_text = (
            f"<b>🛠 ADMIN CONTROL PANEL</b>\n\n"
            f"• <code>/broadcast</code> - Message to all\n"
            f"• <code>/ban [ID]</code> - Ban a user\n"
            f"• <code>/unban [ID]</code> - Unban user\n"
            f"• <code>/stats</code> - Detailed database stats"
        )
        bot.edit_message_caption(adm_text, call.message.chat.id, call.message.message_id, reply_markup=back_btn())

# --- CORE ENGINE PROCESSING ---
def process_engine(mode, message, status_msg):
    work_id = f"{message.from_user.id}_{int(time.time())}"
    work_dir = f"workspace_{work_id}"
    os.makedirs(work_dir, exist_ok=True)
    
    try:
        import hbctool
        users_col.update_one({"user_id": message.from_user.id}, {"$inc": {"total_tasks": 1}})
        
        # Phase 1: Download
        bot.edit_message_text(f"📥 <b>Downloading File...</b>\n{get_progress_bar(20)}", message.chat.id, status_msg.message_id)
        file_info = bot.get_file(message.reply_to_message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        input_file = os.path.join(work_dir, "input_data")
        with open(input_file, 'wb') as f: f.write(downloaded)

        if mode == "disasm":
            # Phase 2: Decompile
            bot.edit_message_text(f"⚙️ <b>Engine: Decompiling (v96)...</b>\n{get_progress_bar(50)}", message.chat.id, status_msg.message_id)
            out_path = os.path.join(work_dir, "out")
            hbctool.disasm(input_file, out_path)
            
            # Phase 3: Zipping
            bot.edit_message_text(f"📦 <b>Packing Result Zip...</b>\n{get_progress_bar(80)}", message.chat.id, status_msg.message_id)
            zip_name = f"Decompiled_{message.from_user.id}.zip"
            with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as z:
                for r, _, fs in os.walk(out_path):
                    for f in fs: z.write(os.path.join(r, f), os.path.relpath(os.path.join(r, f), out_path))
            
            # Phase 4: Uploading
            bot.send_chat_action(message.chat.id, 'upload_document')
            with open(zip_name, 'rb') as f:
                bot.send_document(message.chat.id, f, caption="✅ <b>Decompiled successfully by Hermes Engine.</b>")
            os.remove(zip_name)

        else: # Assemble
            # Phase 2: Extract & Assemble
            bot.edit_message_text(f"⚙️ <b>Engine: Assembling (v96)...</b>\n{get_progress_bar(50)}", message.chat.id, status_msg.message_id)
            extract_dir = os.path.join(work_dir, "extract")
            with zipfile.ZipFile(input_file, 'r') as z: z.extractall(extract_dir)
            
            bundle_out = os.path.join(work_dir, "index.android.bundle")
            hbctool.asm(extract_dir, bundle_out)
            
            # Phase 3: Uploading
            bot.edit_message_text(f"📤 <b>Sending Bundle...</b>\n{get_progress_bar(90)}", message.chat.id, status_msg.message_id)
            bot.send_chat_action(message.chat.id, 'upload_document')
            with open(bundle_out, 'rb') as f:
                bot.send_document(message.chat.id, f, caption="✅ <b>Compiled successfully by Hermes Engine.</b>")

        bot.delete_message(message.chat.id, status_msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ <b>ENGINE ERROR:</b>\n<code>{str(e)}</code>", message.chat.id, status_msg.message_id)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

# --- USER ENGINE COMMANDS ---
@bot.message_handler(commands=['disasmdem', 'asmdem'])
def handle_engine_commands(message):
    if not check_join(message.from_user.id) or is_banned(message.from_user.id):
        return
    
    if not message.reply_to_message or not message.reply_to_message.document:
        return bot.reply_to(message, "❌ <b>Invalid Input!</b> Please reply to a bundle or zip file.")
    
    mode = "disasm" if message.text == "/disasmdem" else "asm"
    status = bot.send_message(message.chat.id, f"🚀 <b>Initializing {mode.upper()} Process...</b>")
    threading.Thread(target=process_engine, args=(mode, message, status)).start()

# --- EXTRA COMMANDS ---
@bot.message_handler(commands=['stats'])
def stats_cmd(message):
    total_u = users_col.count_documents({})
    agg = list(users_col.aggregate([{"$group": {"_id": None, "total": {"$sum": "$total_tasks"}}}]))
    total_t = agg[0]['total'] if agg else 0
    bot.reply_to(message, f"📊 <b>ENGINE STATISTICS</b>\n\nTotal Users: <code>{total_u}</code>\nTotal Tasks: <code>{total_t}</code>")

# --- ADMIN COMMANDS ---
@bot.message_handler(commands=['broadcast'])
def broadcast_handler(message):
    if message.from_user.id != ADMIN_ID: return
    users = users_col.find({})
    count = 0
    if message.reply_to_message:
        for u in users:
            try:
                bot.copy_message(u['user_id'], message.chat.id, message.reply_to_message.message_id)
                count += 1
            except: pass
    else:
        text = message.text.replace("/broadcast ", "")
        for u in users:
            try:
                bot.send_message(u['user_id'], f"📢 <b>ANNOUNCEMENT:</b>\n\n{text}")
                count += 1
            except: pass
    bot.send_message(ADMIN_ID, f"✅ Broadcast sent to {count} users.")

@bot.message_handler(commands=['ban'])
def ban_user(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        tid = int(message.text.split()[1])
        users_col.update_one({"user_id": tid}, {"$set": {"status": "banned"}})
        bot.reply_to(message, f"🚫 User {tid} has been banned.")
    except: bot.reply_to(message, "Usage: /ban [ID]")

# --- START BOT ---
if __name__ == "__main__":
    bootstrap_engine()
    print("✨ Hermes Engine Ultra v96 Started Successfully!")
    bot.infinity_polling(timeout=60, long_polling_timeout=30)
