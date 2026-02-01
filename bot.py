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
ADMIN_ID = 8504263842
CHANNEL_USERNAMES = ["@darkunknownmodder", "@DarkEpicModderBD0x1"]  # ✅ Multiple channels
CHANNEL_URLS = {
    "@darkunknownmodder": "https://t.me/darkunknownmodder",
    "@DarkEpicModderBD0x1": "https://t.me/DarkEpicModderBD0x1"
}
WHL_FILE = "hbctool-0.1.5-96-py3-none-any.whl"
IMG_URL = "https://raw.githubusercontent.com/darkunknownmodder/Drive-DuM/refs/heads/main/Img/Gemini_Generated_Image_rbwl3prbwl3prbwl-picsay.png"

# --- CONCURRENT USER LIMIT ---
MAX_CONCURRENT_USERS = 5
active_users = set()  # Tracks currently processing non-admin users

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
    btn4 = types.InlineKeyboardButton("📢 Official Channel", url=CHANNEL_URLS["@darkunknownmodder"])
    btn5 = types.InlineKeyboardButton("👤 Developer", url=CHANNEL_URLS["@DarkEpicModderBD0x1"])
    markup.add(btn1, btn2)
    markup.add(btn3, btn4)
    markup.add(btn5)
    if user_id == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("🛠 Admin Panel", callback_data="admin_panel"))
    return markup

def back_btn():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Back to Menu", callback_data="back_home"))
    return markup

def generate_join_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    for ch in CHANNEL_USERNAMES:
        markup.add(types.InlineKeyboardButton(f"📢 Join {ch}", url=CHANNEL_URLS[ch]))
    markup.add(types.InlineKeyboardButton("🔄 Verify Membership", callback_data="verify"))
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
        users_col.update_one(
            {"user_id": user.id},
            {"$set": {"name": user.first_name, "username": f"@{user.username}" if user.username else "N/A"}}
        )
    return user_data

def is_banned(user_id):
    u = users_col.find_one({"user_id": user_id})
    return u.get("status") == "banned" if u else False

def check_all_joined(user_id):
    if user_id == ADMIN_ID:
        return True
    try:
        for ch in CHANNEL_USERNAMES:
            status = bot.get_chat_member(ch, user_id).status
            if status not in ['member', 'administrator', 'creator']:
                return False
        return True
    except Exception as e:
        logging.error(f"Join check error: {e}")
        return False

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
    except Exception as e:
        logging.error(f"Engine bootstrap failed: {e}")

# --- START COMMAND ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    if is_banned(user_id):
        return bot.reply_to(message, "🚫 <b>You are restricted from using this bot!</b>")

    sync_user(message.from_user)

    welcome_text = (
        "<b>🚀 HERMES ENGINE ULTRA v96 ACTIVE</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Welcome:</b> {message.from_user.first_name}\n"
        "🛠 <b>Engine:</b> <code>Hermes Decompiler/Assembler</code>\n"
        "💎 <b>Status:</b> <code>Premium Access</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "<i>Please select an option below:</i>"
    )

    if check_all_joined(user_id):
        bot.send_photo(message.chat.id, IMG_URL, caption=welcome_text, reply_markup=get_main_keyboard(user_id))
    else:
        bot.send_photo(
            message.chat.id,
            IMG_URL,
            caption="<b>⚠️ ACCESS LOCKED!</b>\nYou must join <b>ALL</b> official channels to unlock the engine.",
            reply_markup=generate_join_markup()
        )

# --- CALLBACK HANDLERS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    user_id = call.from_user.id
    sync_user(call.from_user)

    if call.data == "back_home":
        welcome_text = (
            "<b>🚀 HERMES ENGINE ULTRA v96 ACTIVE</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Welcome:</b> {call.from_user.first_name}\n"
            "🛠 <b>Engine:</b> <code>Decompiler/Assembler</code>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        bot.edit_message_caption(welcome_text, call.message.chat.id, call.message.message_id, reply_markup=get_main_keyboard(user_id))

    elif call.data == "my_profile":
        u = users_col.find_one({"user_id": user_id})
        profile = (
            "<b>👤 USER PROFILE DATA</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
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
        active_count = len(active_users)
        stats_text = (
            "<b>📊 ENGINE GLOBAL STATS</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 Total Users: <code>{total_u}</code>\n"
            f"⚙️ Tasks Completed: <code>{total_t}</code>\n"
            f"🟢 Active Users: <code>{active_count}/{MAX_CONCURRENT_USERS}</code>\n"
            "🛰 Server Status: <code>Running Smoothly</code>"
        )
        bot.edit_message_caption(stats_text, call.message.chat.id, call.message.message_id, reply_markup=back_btn())

    elif call.data == "verify":
        if check_all_joined(user_id):
            bot.answer_callback_query(call.id, "✅ Verified! Welcome back.", show_alert=True)
            bot.delete_message(call.message.chat.id, call.message.message_id)
            start_cmd(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ Not joined all channels yet!", show_alert=True)

    elif call.data == "admin_panel" and user_id == ADMIN_ID:
        adm_text = (
            "<b>🛠 ADMIN CONTROL PANEL</b>\n\n"
            "• <code>/broadcast [text]</code> - Message all users\n"
            "• <code>/ban [ID]</code> - Ban a user\n"
            "• <code>/unban [ID]</code> - Unban user\n"
            "• <code>/stats</code> - Detailed database stats\n"
            "• <code>/listbans</code> - List banned users\n"
            "• <code>/reload</code> - Reload engine (dev only)"
        )
        bot.edit_message_caption(adm_text, call.message.chat.id, call.message.message_id, reply_markup=back_btn())

# --- CONCURRENCY CHECKER ---
def can_process(user_id):
    if user_id == ADMIN_ID:
        return True
    if len(active_users) >= MAX_CONCURRENT_USERS:
        return False
    return True

def add_active_user(user_id):
    if user_id != ADMIN_ID:
        active_users.add(user_id)

def remove_active_user(user_id):
    if user_id != ADMIN_ID:
        active_users.discard(user_id)

# --- CORE ENGINE PROCESSING ---
def process_engine(mode, message, status_msg):
    user_id = message.from_user.id
    if not can_process(user_id):
        bot.edit_message_text(
            f"⚠️ <b>Server Busy!</b>\nMaximum {MAX_CONCURRENT_USERS} users allowed simultaneously.\n"
            "Please wait or try again later.",
            message.chat.id, status_msg.message_id
        )
        return

    add_active_user(user_id)
    work_id = f"{user_id}_{int(time.time())}"
    work_dir = f"workspace_{work_id}"
    os.makedirs(work_dir, exist_ok=True)

    try:
        import hbctool
        users_col.update_one({"user_id": user_id}, {"$inc": {"total_tasks": 1}})

        # File info
        doc = message.reply_to_message.document
        file_size_mb = round(doc.file_size / (1024 * 1024), 2)
        file_name = doc.file_name or "Unknown"

        # Phase 1: Download
        bot.send_chat_action(message.chat.id, 'typing')
        bot.edit_message_text(
            f"📥 <b>Downloading...</b>\n📁 <code>{file_name}</code>\n💾 <code>{file_size_mb} MB</code>\n{get_progress_bar(20)}",
            message.chat.id, status_msg.message_id
        )

        file_info = bot.get_file(doc.file_id)
        downloaded = bot.download_file(file_info.file_path)
        input_file = os.path.join(work_dir, "input_data")
        with open(input_file, 'wb') as f:
            f.write(downloaded)

        if mode == "disasm":
            # Phase 2: Decompile
            bot.send_chat_action(message.chat.id, 'typing')
            bot.edit_message_text(
                f"⚙️ <b>Decompiling (v96)...</b>\n{get_progress_bar(50)}\n⏳ Processing Hermes bytecode...",
                message.chat.id, status_msg.message_id
            )
            out_path = os.path.join(work_dir, "out")
            hbctool.disasm(input_file, out_path)

            # Phase 3: Zip
            bot.send_chat_action(message.chat.id, 'upload_document')
            bot.edit_message_text(
                f"📦 <b>Packing result...</b>\n{get_progress_bar(80)}",
                message.chat.id, status_msg.message_id
            )
            zip_name = f"Decompiled_{user_id}.zip"
            with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as z:
                for root, _, files in os.walk(out_path):
                    for f in files:
                        z.write(os.path.join(root, f), os.path.relpath(os.path.join(root, f), out_path))

            # Phase 4: Send
            with open(zip_name, 'rb') as f:
                bot.send_document(message.chat.id, f, caption="✅ <b>Decompiled successfully by Hermes Engine.</b>")
            os.remove(zip_name)

        else:  # Assemble
            bot.send_chat_action(message.chat.id, 'typing')
            bot.edit_message_text(
                f"⚙️ <b>Assembling (v96)...</b>\n{get_progress_bar(50)}\n⏳ Rebuilding bundle...",
                message.chat.id, status_msg.message_id
            )
            extract_dir = os.path.join(work_dir, "extract")
            with zipfile.ZipFile(input_file, 'r') as z:
                z.extractall(extract_dir)

            bundle_out = os.path.join(work_dir, "index.android.bundle")
            hbctool.asm(extract_dir, bundle_out)

            bot.send_chat_action(message.chat.id, 'upload_document')
            bot.edit_message_text(
                f"📤 <b>Sending compiled bundle...</b>\n{get_progress_bar(90)}",
                message.chat.id, status_msg.message_id
            )
            with open(bundle_out, 'rb') as f:
                bot.send_document(message.chat.id, f, caption="✅ <b>Compiled successfully by Hermes Engine.</b>")

        bot.delete_message(message.chat.id, status_msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"❌ <b>ENGINE ERROR:</b>\n<code>{str(e)[:300]}</code>", message.chat.id, status_msg.message_id)
    finally:
        remove_active_user(user_id)
        shutil.rmtree(work_dir, ignore_errors=True)

# --- USER COMMANDS ---
@bot.message_handler(commands=['disasmdem', 'asmdem'])
def handle_engine_commands(message):
    if is_banned(message.from_user.id) or not check_all_joined(message.from_user.id):
        return

    if not message.reply_to_message or not message.reply_to_message.document:
        return bot.reply_to(message, "❌ <b>Invalid Input!</b> Please reply to a bundle or zip file.")

    mode = "disasm" if message.text == "/disasmdem" else "asm"
    status = bot.send_message(message.chat.id, "🚀 <b>Initializing Hermes Engine...</b>")
    threading.Thread(target=process_engine, args=(mode, message, status), daemon=True).start()

# --- EXTRA COMMANDS ---
@bot.message_handler(commands=['stats'])
def stats_cmd(message):
    total_u = users_col.count_documents({})
    agg = list(users_col.aggregate([{"$group": {"_id": None, "total": {"$sum": "$total_tasks"}}}]))
    total_t = agg[0]['total'] if agg else 0
    active_count = len(active_users)
    bot.reply_to(
        message,
        f"📊 <b>ENGINE STATISTICS</b>\n\n"
        f"👥 Total Users: <code>{total_u}</code>\n"
        f"⚙️ Tasks Completed: <code>{total_t}</code>\n"
        f"🟢 Active Now: <code>{active_count}/{MAX_CONCURRENT_USERS}</code>"
    )

# --- ADMIN COMMANDS ---
@bot.message_handler(commands=['broadcast'])
def broadcast_handler(message):
    if message.from_user.id != ADMIN_ID:
        return
    text = message.text.replace("/broadcast ", "").strip()
    if not text:
        return bot.reply_to(message, "Usage: /broadcast [message]")
    users = users_col.find({"status": {"$ne": "banned"}})
    count = 0
    for u in users:
        try:
            bot.send_message(u['user_id'], f"📢 <b>ANNOUNCEMENT:</b>\n\n{text}")
            count += 1
        except:
            pass
    bot.send_message(ADMIN_ID, f"✅ Broadcast sent to {count} users.")

@bot.message_handler(commands=['ban'])
def ban_user(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        tid = int(message.text.split()[1])
        users_col.update_one({"user_id": tid}, {"$set": {"status": "banned"}})
        bot.reply_to(message, f"🚫 User {tid} has been banned.")
    except:
        bot.reply_to(message, "Usage: /ban [USER_ID]")

@bot.message_handler(commands=['unban'])
def unban_user(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        tid = int(message.text.split()[1])
        users_col.update_one({"user_id": tid}, {"$set": {"status": "active"}})
        bot.reply_to(message, f"✅ User {tid} has been unbanned.")
    except:
        bot.reply_to(message, "Usage: /unban [USER_ID]")

@bot.message_handler(commands=['listbans'])
def list_bans(message):
    if message.from_user.id != ADMIN_ID:
        return
    banned = users_col.find({"status": "banned"})
    ids = [str(u['user_id']) for u in banned]
    if not ids:
        bot.reply_to(message, "No banned users.")
    else:
        bot.reply_to(message, f"Banned IDs:\n<code>{', '.join(ids)}</code>")

@bot.message_handler(commands=['reload'])
def reload_engine(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.reply_to(message, "🔄 Reloading engine...")
    bootstrap_engine()
    bot.send_message(ADMIN_ID, "✅ Engine reloaded!")

# --- START BOT ---
if __name__ == "__main__":
    bootstrap_engine()
    print("✨ Hermes Engine Ultra v96 Started Successfully!")
    bot.infinity_polling(timeout=60, long_polling_timeout=30)"live_tasks":
        bot.answer_callback_query(call.id, f"Current Load: {current_running_tasks}/{MAX_CONCURRENT_TASKS} Users")

    elif call.data == "admin_panel" and user_id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Broadcast", callback_data="adm_bc"), types.InlineKeyboardButton("🚫 Ban User", callback_data="adm_ban"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_home"))
        bot.edit_message_caption("<b>🛠 ADMIN CONTROL UNIT</b>\nManage users and system load here.", call.message.chat.id, call.message.message_id, reply_markup=markup)

# --- ENGINE COMMANDS ---
@bot.message_handler(commands=['disasmdem', 'asmdem'])
def handle_tasks(message):
    not_joined = check_join(message.from_user.id)
    if not_joined: return bot.reply_to(message, "❌ Please /start and join our channels first!")
    
    if not message.reply_to_message or not message.reply_to_message.document:
        return bot.reply_to(message, "❌ <b>Reply to a file!</b>\nFor Decompile: reply to .bundle\nFor Compile: reply to .zip")
    
    mode = "disasm" if message.text == "/disasmdem" else "asm"
    status = bot.send_message(message.chat.id, "🚀 <b>Initializing Engine...</b>")
    threading.Thread(target=process_engine, args=(mode, message, status)).start()

# --- ADMIN ACTIONS ---
@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.from_user.id != ADMIN_ID: return
    text = message.text.replace("/broadcast ", "")
    users = users_col.find({})
    success = 0
    for u in users:
        try:
            bot.send_message(u['user_id'], f"📢 <b>GLOBAL ANNOUNCEMENT</b>\n\n{text}")
            success += 1
        except: pass
    bot.reply_to(message, f"✅ Sent to {success} users.")

# --- STARTUP ---
if __name__ == "__main__":
    bootstrap_engine()
    print("✨ Hermes Premium Bot is Live!")
    bot.infinity_polling(timeout=60, long_polling_timeout=30)"live_tasks":
        bot.answer_callback_query(call.id, f"Current Load: {current_running_tasks}/{MAX_CONCURRENT_TASKS} Users")

    elif call.data == "admin_panel" and user_id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Broadcast", callback_data="adm_bc"), types.InlineKeyboardButton("🚫 Ban User", callback_data="adm_ban"))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_home"))
        bot.edit_message_caption("<b>🛠 ADMIN CONTROL UNIT</b>\nManage users and system load here.", call.message.chat.id, call.message.message_id, reply_markup=markup)

# --- ENGINE COMMANDS ---
@bot.message_handler(commands=['disasmdem', 'asmdem'])
def handle_tasks(message):
    not_joined = check_join(message.from_user.id)
    if not_joined: return bot.reply_to(message, "❌ Please /start and join our channels first!")
    
    if not message.reply_to_message or not message.reply_to_message.document:
        return bot.reply_to(message, "❌ <b>Reply to a file!</b>\nFor Decompile: reply to .bundle\nFor Compile: reply to .zip")
    
    mode = "disasm" if message.text == "/disasmdem" else "asm"
    status = bot.send_message(message.chat.id, "🚀 <b>Initializing Engine...</b>")
    threading.Thread(target=process_engine, args=(mode, message, status)).start()

# --- ADMIN ACTIONS ---
@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.from_user.id != ADMIN_ID: return
    text = message.text.replace("/broadcast ", "")
    users = users_col.find({})
    success = 0
    for u in users:
        try:
            bot.send_message(u['user_id'], f"📢 <b>GLOBAL ANNOUNCEMENT</b>\n\n{text}")
            success += 1
        except: pass
    bot.reply_to(message, f"✅ Sent to {success} users.")

# --- STARTUP ---
if __name__ == "__main__":
    bootstrap_engine()
    print("✨ Hermes Premium Bot is Live!")
    bot.infinity_polling(timeout=60, long_polling_timeout=30)f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"

def process_engine(mode, message, status_msg):
    user_id = message.from_user.id
    max_c = get_max_concurrent()
    active = get_active_tasks()

    if user_id != ADMIN_ID and active >= max_c:
        bot.edit_message_text(
            f"⚠️ <b>Server Busy!</b>\nMaximum {max_c} users allowed simultaneously.\nPlease try again later.",
            message.chat.id, status_msg.message_id
        )
        return

    increment_active()
    work_id = f"{user_id}_{int(time.time())}"
    work_dir = f"workspace_{work_id}"
    os.makedirs(work_dir, exist_ok=True)
    
    try:
        import hbctool
        users_col.update_one({"user_id": user_id}, {"$inc": {"total_tasks": 1}})
        
        # Download
        bot.send_chat_action(message.chat.id, 'typing')
        file_info = bot.get_file(message.reply_to_message.document.file_id)
        file_size = file_info.file_size
        readable_size = format_bytes(file_size)
        bot.edit_message_text(
            f"📥 <b>Downloading File...</b>\n📂 Size: {readable_size}\n{get_progress_bar(20)}",
            message.chat.id, status_msg.message_id
        )
        downloaded = bot.download_file(file_info.file_path)
        input_file = os.path.join(work_dir, "input_data")
        with open(input_file, 'wb') as f:
            f.write(downloaded)

        if mode == "disasm":
            bot.send_chat_action(message.chat.id, 'typing')
            bot.edit_message_text(
                f"⚙️ <b>Decompiling (v96)...</b>\n📂 File: {message.reply_to_message.document.file_name}\n📏 Size: {readable_size}\n{get_progress_bar(50)}",
                message.chat.id, status_msg.message_id
            )
            out_path = os.path.join(work_dir, "out")
            hbctool.disasm(input_file, out_path)
            
            bot.send_chat_action(message.chat.id, 'typing')
            bot.edit_message_text(
                f"📦 <b>Packing Result...</b>\n{get_progress_bar(80)}",
                message.chat.id, status_msg.message_id
            )
            zip_name = f"Decompiled_{user_id}.zip"
            with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as z:
                for r, _, fs in os.walk(out_path):
                    for f in fs:
                        z.write(os.path.join(r, f), os.path.relpath(os.path.join(r, f), out_path))
            
            bot.send_chat_action(message.chat.id, 'upload_document')
            with open(zip_name, 'rb') as f:
                bot.send_document(message.chat.id, f, caption="✅ <b>Decompiled successfully by Hermes Engine v96.</b>")
            os.remove(zip_name)

        else:  # asm
            bot.send_chat_action(message.chat.id, 'typing')
            bot.edit_message_text(
                f"⚙️ <b>Assembling (v96)...</b>\n📂 File: {message.reply_to_message.document.file_name}\n📏 Size: {readable_size}\n{get_progress_bar(50)}",
                message.chat.id, status_msg.message_id
            )
            extract_dir = os.path.join(work_dir, "extract")
            with zipfile.ZipFile(input_file, 'r') as z:
                z.extractall(extract_dir)
            
            bundle_out = os.path.join(work_dir, "index.android.bundle")
            hbctool.asm(extract_dir, bundle_out)
            
            bot.send_chat_action(message.chat.id, 'upload_document')
            bot.edit_message_text(
                f"📤 <b>Sending Bundle...</b>\n{get_progress_bar(90)}",
                message.chat.id, status_msg.message_id
            )
            with open(bundle_out, 'rb') as f:
                bot.send_document(message.chat.id, f, caption="✅ <b>Compiled successfully by Hermes Engine v96.</b>")

        bot.delete_message(message.chat.id, status_msg.message_id)

    except Exception as e:
        bot.send_chat_action(message.chat.id, 'typing')
        bot.edit_message_text(
            f"❌ <b>ENGINE ERROR:</b>\n<code>{str(e)[:300]}</code>",
            message.chat.id, status_msg.message_id
        )
    finally:
        decrement_active()
        shutil.rmtree(work_dir, ignore_errors=True)
        gc.collect()

# --- USER COMMANDS ---
@bot.message_handler(commands=['disasmdem', 'asmdem'])
def handle_engine_commands(message):
    if is_banned(message.from_user.id):
        return
    if not check_all_joined(message.from_user.id):
        return bot.reply_to(message, "🔐 Please join all channels first via /start")

    if not message.reply_to_message or not message.reply_to_message.document:
        return bot.reply_to(message, "❌ <b>Invalid Input!</b> Reply to a valid file.")

    mode = "disasm" if message.text == "/disasmdem" else "asm"
    status = bot.send_message(message.chat.id, "🚀 <b>Initializing Hermes Engine...</b>")
    threading.Thread(target=process_engine, args=(mode, message, status), daemon=True).start()

@bot.message_handler(commands=['stats'])
def stats_cmd(message):
    total_u = users_col.count_documents({})
    agg = list(users_col.aggregate([{"$group": {"_id": None, "total": {"$sum": "$total_tasks"}}}]))
    total_t = agg[0]['total'] if agg else 0
    active = get_active_tasks()
    max_c = get_max_concurrent()
    bot.reply_to(
        message,
        f"📊 <b>ENGINE STATISTICS</b>\n\n"
        f"👥 Total Users: <code>{total_u}</code>\n"
        f"⚙️ Total Tasks: <code>{total_t}</code>\n"
        f"🟢 Live: <code>{active}/{max_c}</code>"
    )

@bot.message_handler(commands=['live'])
def live_cmd(message):
    if message.from_user.id != ADMIN_ID:
        return
    active = get_active_tasks()
    max_c = get_max_concurrent()
    bot.reply_to(message, f"🟢 <b>Live Monitoring</b>\nActive Tasks: <code>{active}/{max_c}</code>")

# --- ADMIN COMMANDS ---
@bot.message_handler(commands=['broadcast'])
def broadcast_handler(message):
    if message.from_user.id != ADMIN_ID:
        return
    text = message.text.replace("/broadcast ", "")
    if not text.strip():
        return bot.reply_to(message, "Usage: /broadcast Your message here")
    users = users_col.find({})
    count = 0
    for u in users:
        try:
            bot.send_message(u['user_id'], f"📢 <b>ANNOUNCEMENT:</b>\n\n{text}")
            count += 1
        except:
            pass
    bot.send_message(ADMIN_ID, f"✅ Broadcast sent to {count} users.")

@bot.message_handler(commands=['ban'])
def ban_user(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        tid = int(message.text.split()[1])
        users_col.update_one({"user_id": tid}, {"$set": {"status": "banned"}})
        bot.reply_to(message, f"🚫 User {tid} has been banned.")
    except:
        bot.reply_to(message, "Usage: /ban [USER_ID]")

@bot.message_handler(commands=['unban'])
def unban_user(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        tid = int(message.text.split()[1])
        users_col.update_one({"user_id": tid}, {"$set": {"status": "active"}})
        bot.reply_to(message, f"✅ User {tid} has been unbanned.")
    except:
        bot.reply_to(message, "Usage: /unban [USER_ID]")

@bot.message_handler(commands=['set_limit'])
def set_limit(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        n = int(message.text.split()[1])
        config_col.update_one({"key": "max_concurrent"}, {"$set": {"value": n}})
        bot.reply_to(message, f"✅ Max concurrent users set to {n}.")
    except:
        bot.reply_to(message, "Usage: /set_limit [NUMBER]")

@bot.message_handler(commands=['clear_tasks'])
def clear_tasks(message):
    if message.from_user.id != ADMIN_ID:
        return
    set_active_tasks(0)
    bot.reply_to(message, "✅ Active task counter reset.")

# --- START BOT ---
if __name__ == "__main__":
    bootstrap_engine()
    print("✨ Hermes Engine Ultra v96 Started Successfully!")
    bot.infinity_polling(timeout=60, long_polling_timeout=30)        with open(zip_name, 'rb') as f:
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
