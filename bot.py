import os
import sys
import shutil
import subprocess
import zipfile
import time
import logging
import threading
import urllib.parse
import gc
from datetime import datetime
from telebot import TeleBot, types
from pymongo import MongoClient

# --- CONFIGURATION ---
TOKEN = "8536451561:AAFIuJAuATjo0WnzhgQAtV73mFx_0adS-kg"
ADMIN_ID = 8504263842
CHANNELS = [
    "@darkunknownmodder",
    # Add more channels here if needed
]
CHANNEL_URLS = {
    "@darkunknownmodder": "https://t.me/darkunknownmodder"
}
WHL_FILE = "hbctool-0.1.5-96-py3-none-any.whl"
IMG_URL = "https://raw.githubusercontent.com/darkunknownmodder/Drive-DuM/refs/heads/main/Img/Gemini_Generated_Image_rbwl3prbwl3prbwl-picsay.png"

# --- MONGODB CONNECTION ---
raw_uri = "mongodb+srv://darkunknownmodder:" + urllib.parse.quote_plus("%#DuM404%App@#%") + "@cluster0.w2fubew.mongodb.net/?appName=Cluster0"
client = MongoClient(raw_uri)
db = client['hermes_ultra_db']
users_col = db['users']
config_col = db['config']

# Initialize config if not exists
if not config_col.find_one({"key": "active_tasks"}):
    config_col.insert_one({"key": "active_tasks", "value": 0})
if not config_col.find_one({"key": "max_concurrent"}):
    config_col.insert_one({"key": "max_concurrent", "value": 5})

bot = TeleBot(TOKEN, parse_mode="HTML", threaded=True, num_threads=40)
logging.basicConfig(level=logging.INFO)

# --- HELPERS ---
def get_progress_bar(percent):
    done = int(percent / 10)
    bar = "█" * done + "░" * (10 - done)
    return f"<b>{bar} {percent}%</b>"

def get_main_keyboard(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("👤 My Profile", callback_data="my_profile")
    btn2 = types.InlineKeyboardButton("📜 All Commands", callback_data="help_cmd")
    btn3 = types.InlineKeyboardButton("📊 Bot Stats", callback_data="bot_stats")
    btn4 = types.InlineKeyboardButton("📢 Channel", url=CHANNEL_URLS.get(CHANNELS[0], CHANNELS[0]))
    btn5 = types.InlineKeyboardButton("👤 Developer", url="https://t.me/DarkEpicModderBD0x1")
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

def get_active_tasks():
    doc = config_col.find_one({"key": "active_tasks"})
    return doc["value"] if doc else 0

def set_active_tasks(n):
    config_col.update_one({"key": "active_tasks"}, {"$set": {"value": n}})

def get_max_concurrent():
    doc = config_col.find_one({"key": "max_concurrent"})
    return doc["value"] if doc else 5

def increment_active():
    config_col.update_one({"key": "active_tasks"}, {"$inc": {"value": 1}})

def decrement_active():
    config_col.update_one({"key": "active_tasks"}, {"$inc": {"value": -1}})

# --- DATABASE LOGIC ---
def sync_user(user):
    user_data = users_col.find_one({"user_id": user.id})
    now = datetime.now().strftime("%Y-%m-%d")
    if not user_data:
        user_data = {
            "user_id": user.id,
            "username": f"@{user.username}" if user.username else "N/A",
            "name": user.first_name,
            "joined_at": now,
            "status": "active",
            "total_tasks": 0
        }
        users_col.insert_one(user_data)
    else:
        users_col.update_one(
            {"user_id": user.id},
            {"$set": {
                "name": user.first_name,
                "username": f"@{user.username}" if user.username else "N/A",
                "last_seen": now
            }}
        )
    return user_data

def is_banned(user_id):
    u = users_col.find_one({"user_id": user_id})
    return u and u.get("status") == "banned"

def check_all_joined(user_id):
    if user_id == ADMIN_ID:
        return True
    for ch in CHANNELS:
        try:
            status = bot.get_chat_member(ch, user_id).status
            if status not in ['member', 'administrator', 'creator']:
                return False
        except:
            return False
    return True

def get_join_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    for ch in CHANNELS:
        name = ch.replace("@", "").title()
        url = CHANNEL_URLS.get(ch, f"https://t.me/{ch.replace('@', '')}")
        markup.add(types.InlineKeyboardButton(f"📢 Join {name}", url=url))
    markup.add(types.InlineKeyboardButton("✅ Verify Now", callback_data="verify"))
    return markup

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

# --- COMMAND HANDLERS ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    if is_banned(message.from_user.id):
        return bot.reply_to(message, "🚫 <b>You are restricted from using this bot!</b>")
    
    sync_user(message.from_user)
    
    welcome_text = (
        "<b>✨ HERMES ENGINE ULTRA v96</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔥 <b>Premium Decompiler & Assembler</b>\n"
        "🔒 <b>Secure • Fast • Reliable</b>\n"
        "💎 <b>Status:</b> <code>Premium Access</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "<i>Please verify your membership to continue.</i>"
    )
    
    if check_all_joined(message.from_user.id):
        bot.send_photo(message.chat.id, IMG_URL, caption=welcome_text, reply_markup=get_main_keyboard(message.from_user.id))
    else:
        bot.send_photo(
            message.chat.id,
            IMG_URL,
            caption="<b>⚠️ ACCESS RESTRICTED!</b>\n\nYou must join all required channels to use this premium engine.",
            reply_markup=get_join_markup()
        )

# --- CALLBACK HANDLERS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    user_id = call.from_user.id
    sync_user(call.from_user)

    if call.data == "back_home":
        welcome_text = (
            "<b>✨ HERMES ENGINE ULTRA v96</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🔥 <b>Premium Decompiler & Assembler</b>\n"
            "🔒 <b>Secure • Fast • Reliable</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        bot.edit_message_caption(welcome_text, call.message.chat.id, call.message.message_id, reply_markup=get_main_keyboard(user_id))

    elif call.data == "my_profile":
        u = users_col.find_one({"user_id": user_id})
        profile = (
            "<b>👤 USER PROFILE</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 <b>ID:</b> <code>{u['user_id']}</code>\n"
            f"🏷 <b>Name:</b> <code>{u['name']}</code>\n"
            f"👤 <b>Username:</b> {u['username']}\n"
            f"⚡ <b>Tasks Done:</b> <code>{u['total_tasks']}</code>\n"
            f"📅 <b>Joined:</b> <code>{u['joined_at']}</code>\n"
            f"💎 <b>Plan:</b> <code>PREMIUM</code>"
        )
        bot.edit_message_caption(profile, call.message.chat.id, call.message.message_id, reply_markup=back_btn())

    elif call.data == "help_cmd":
        help_text = (
            "<b>📜 ENGINE COMMANDS</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "⚡ <code>/disasmdem</code> – Reply to <i>index.android.bundle</i> to decompile.\n"
            "⚡ <code>/asmdem</code> – Reply to your <i>source.zip</i> to compile.\n"
            "⚡ <code>/start</code> – Refresh interface.\n"
            "⚡ <code>/stats</code> – View global stats.\n\n"
            "<i>⚠️ Max 5 users can process at once.</i>"
        )
        bot.edit_message_caption(help_text, call.message.chat.id, call.message.message_id, reply_markup=back_btn())

    elif call.data == "bot_stats":
        total_u = users_col.count_documents({})
        agg = list(users_col.aggregate([{"$group": {"_id": None, "total": {"$sum": "$total_tasks"}}}]))
        total_t = agg[0]['total'] if agg else 0
        active = get_active_tasks()
        max_c = get_max_concurrent()
        stats_text = (
            "<b>📊 GLOBAL STATISTICS</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"👥 Total Users: <code>{total_u}</code>\n"
            f"⚙️ Total Tasks: <code>{total_t}</code>\n"
            f"🟢 Live Tasks: <code>{active}/{max_c}</code>\n"
            f"🛰 Status: <code>Running Smoothly</code>"
        )
        bot.edit_message_caption(stats_text, call.message.chat.id, call.message.message_id, reply_markup=back_btn())

    elif call.data == "verify":
        if check_all_joined(user_id):
            bot.answer_callback_query(call.id, "✅ Verified! Welcome to Hermes Engine.", show_alert=True)
            bot.delete_message(call.message.chat.id, call.message.message_id)
            start_cmd(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ Please join all channels first!", show_alert=True)

    elif call.data == "admin_panel" and user_id == ADMIN_ID:
        adm_text = (
            "<b>🛠 ADMIN CONTROL PANEL</b>\n\n"
            "• <code>/broadcast [msg]</code>\n"
            "• <code>/ban [ID]</code>\n"
            "• <code>/unban [ID]</code>\n"
            "• <code>/user [ID]</code>\n"
            "• <code>/set_limit [N]</code>\n"
            "• <code>/clear_tasks</code>\n"
            "• <code>/live</code> – Monitor live tasks"
        )
        bot.edit_message_caption(adm_text, call.message.chat.id, call.message.message_id, reply_markup=back_btn())

# --- CORE PROCESSING ---
def format_bytes(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
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
