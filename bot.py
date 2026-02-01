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
# একাধিক চ্যানেলের ইউজারনেম এখানে লিস্ট আকারে বসাও (সহজেই নতুন বাটন তৈরি হবে)
REQUIRED_CHANNELS = ["@darkunknownmodder", "@darkunknownmodder_chat"] 
IMG_URL = "https://raw.githubusercontent.com/darkunknownmodder/Drive-DuM/refs/heads/main/Img/Gemini_Generated_Image_rbwl3prbwl3prbwl-picsay.png"
WHL_FILE = "hbctool-0.1.5-96-py3-none-any.whl"

# --- MONGODB CONNECTION ---
raw_uri = "mongodb+srv://darkunknownmodder:" + urllib.parse.quote_plus("%#DuM404%App@#%") + "@cluster0.w2fubew.mongodb.net/?appName=Cluster0"
client = MongoClient(raw_uri)
db = client['hermes_ultra_db']
users_col = db['users']
active_tasks_col = db['active_tasks'] # লাইভ টাস্ক মনিটরিং

bot = TeleBot(TOKEN, parse_mode="HTML", threaded=True, num_threads=50)
logging.basicConfig(level=logging.INFO)

# --- GLOBAL TRACKER ---
MAX_CONCURRENT_TASKS = 5
current_running_tasks = 0
task_lock = threading.Lock()

# --- UI HELPERS ---
def get_progress_bar(percent, speed="Calculating..."):
    done = int(percent / 10)
    bar = "🟢" * done + "⚪" * (10 - done)
    return f"<b>{bar} {percent}%</b>\n🚀 <b>Speed:</b> <code>{speed}</code>"

def get_main_keyboard(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("👤 My Profile", callback_data="my_profile"),
        types.InlineKeyboardButton("📜 Commands", callback_data="help_cmd")
    )
    markup.add(
        types.InlineKeyboardButton("📊 Bot Stats", callback_data="bot_stats"),
        types.InlineKeyboardButton("🛰 Active Tasks", callback_data="live_tasks")
    )
    markup.add(types.InlineKeyboardButton("📢 Official Channel", url="https://t.me/darkunknownmodder"))
    if user_id == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("🛠 Admin Control Panel", callback_data="admin_panel"))
    return markup

def back_btn():
    return types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 Back to Menu", callback_data="back_home"))

# --- DATABASE LOGIC ---
def sync_user(user):
    user_data = users_col.find_one({"user_id": user.id})
    if not user_data:
        user_data = {
            "user_id": user.id,
            "username": f"@{user.username}" if user.username else "N/A",
            "name": user.first_name,
            "joined_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "status": "active",
            "total_tasks": 0
        }
        users_col.insert_one(user_data)
        return True, user_data # New User
    else:
        users_col.update_one({"user_id": user.id}, {"$set": {"name": user.first_name, "username": f"@{user.username}" if user.username else "N/A"}})
        return False, user_data # Old User

def check_join(user_id):
    if user_id == ADMIN_ID: return True
    not_joined = []
    for channel in REQUIRED_CHANNELS:
        try:
            status = bot.get_chat_member(channel, user_id).status
            if status not in ['member', 'administrator', 'creator']:
                not_joined.append(channel)
        except:
            not_joined.append(channel)
    return not_joined

# --- ENGINE SETUP ---
def bootstrap_engine():
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "hbctool" if not os.path.exists(WHL_FILE) else WHL_FILE])
        import hbctool.hbc
        if 96 not in hbctool.hbc.HBC:
            hbctool.hbc.HBC[96] = hbctool.hbc.HBC[max(hbctool.hbc.HBC.keys())]
    except: pass

# --- COMMAND HANDLERS ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.send_chat_action(message.chat.id, 'typing')
    is_new, u_data = sync_user(message.from_user)
    
    if u_data.get("status") == "banned":
        return bot.reply_to(message, "🚫 <b>Access Denied!</b> You are banned from this system.")

    not_joined = check_join(message.from_user.id)
    if not_joined:
        markup = types.InlineKeyboardMarkup()
        for ch in not_joined:
            markup.add(types.InlineKeyboardButton(f"📢 Join {ch}", url=f"https://t.me/{ch.replace('@','') }"))
        markup.add(types.InlineKeyboardButton("🔄 Verify Membership", callback_data="verify"))
        
        caption = "<b>⚠️ ACCESS RESTRICTED!</b>\n\nTo use this premium engine, you must join all our official channels below."
        return bot.send_photo(message.chat.id, IMG_URL, caption=caption, reply_markup=markup)

    welcome_text = (
        f"<b>🚀 HERMES ENGINE ULTRA v96</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👋 <b>Welcome back,</b> {message.from_user.first_name}!\n"
        f"💎 <b>Plan:</b> <code>Premium User</code>\n"
        f"⚙️ <b>Engine Status:</b> <code>Ready to Work</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Reply to index.android.bundle with /disasmdem to start.</i>"
    )
    bot.send_photo(message.chat.id, IMG_URL, caption=welcome_text, reply_markup=get_main_keyboard(message.from_user.id))

# --- CORE PROCESSING ---
def process_engine(mode, message, status_msg):
    global current_running_tasks
    user_id = message.from_user.id
    
    # Check Concurrency (Admin Bypass)
    if user_id != ADMIN_ID:
        with task_lock:
            if current_running_tasks >= MAX_CONCURRENT_TASKS:
                bot.edit_message_text(f"⚠️ <b>Server Busy!</b>\n\nCurrently 5/5 users are processing. Please wait 1-2 minutes for a slot.", message.chat.id, status_msg.message_id)
                return
            current_running_tasks += 1

    work_id = f"{user_id}_{int(time.time())}"
    work_dir = f"work_{work_id}"
    os.makedirs(work_dir, exist_ok=True)
    
    try:
        import hbctool
        start_time = time.time()
        
        # UI: Phase 1
        bot.send_chat_action(message.chat.id, 'record_video_note')
        bot.edit_message_text(f"📥 <b>Downloading Resource...</b>\n{get_progress_bar(20, '12.5 MB/s')}", message.chat.id, status_msg.message_id)
        
        file_info = bot.get_file(message.reply_to_message.document.file_id)
        file_name = message.reply_to_message.document.file_name
        downloaded = bot.download_file(file_info.file_path)
        input_file = os.path.join(work_dir, "input_data")
        with open(input_file, 'wb') as f: f.write(downloaded)

        # UI: Phase 2 (Animation)
        for i in range(30, 80, 15):
            time.sleep(0.8)
            bot.edit_message_text(f"⚙️ <b>Hermes v96 Processing...</b>\n{get_progress_bar(i, 'Processing...')}\n📂 <b>File:</b> <code>{file_name}</code>", message.chat.id, status_msg.message_id)

        if mode == "disasm":
            out_path = os.path.join(work_dir, "decompiled_source")
            hbctool.disasm(input_file, out_path)
            
            zip_name = f"Decompiled_{user_id}.zip"
            with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as z:
                for r, _, fs in os.walk(out_path):
                    for f in fs: z.write(os.path.join(r, f), os.path.relpath(os.path.join(r, f), out_path))
            
            bot.send_chat_action(message.chat.id, 'upload_document')
            duration = round(time.time() - start_time, 2)
            with open(zip_name, 'rb') as f:
                bot.send_document(message.chat.id, f, caption=f"✅ <b>Decompiled Successfully!</b>\n⏱ <b>Time:</b> <code>{duration}s</code>\n💎 <b>Engine:</b> <code>Hermes v96</code>")
            os.remove(zip_name)
        else:
            extract_dir = os.path.join(work_dir, "asm_source")
            with zipfile.ZipFile(input_file, 'r') as z: z.extractall(extract_dir)
            bundle_out = os.path.join(work_dir, "index.android.bundle")
            hbctool.asm(extract_dir, bundle_out)
            
            bot.send_chat_action(message.chat.id, 'upload_document')
            duration = round(time.time() - start_time, 2)
            with open(bundle_out, 'rb') as f:
                bot.send_document(message.chat.id, f, caption=f"✅ <b>Assembled Successfully!</b>\n⏱ <b>Time:</b> <code>{duration}s</code>\n💎 <b>Engine:</b> <code>Hermes v96</code>")

        users_col.update_one({"user_id": user_id}, {"$inc": {"total_tasks": 1}})
        bot.delete_message(message.chat.id, status_msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"❌ <b>ENGINE ERROR</b>\n<code>{str(e)}</code>", message.chat.id, status_msg.message_id)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
        if user_id != ADMIN_ID:
            with task_lock:
                current_running_tasks -= 1

# --- CALLBACKS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    user_id = call.from_user.id
    if call.data == "back_home":
        start_cmd(call.message)
        bot.delete_message(call.message.chat.id, call.message.message_id)

    elif call.data == "verify":
        if not check_join(user_id):
            bot.answer_callback_query(call.id, "✅ Verified! You can use the bot now.", show_alert=True)
            start_cmd(call.message)
            bot.delete_message(call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "❌ Join all channels first!", show_alert=True)

    elif call.data == "my_profile":
        u = users_col.find_one({"user_id": user_id})
        text = (
            f"<b>👤 USER PREMIUM PROFILE</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 <b>ID:</b> <code>{u['user_id']}</code>\n"
            f"⚡ <b>Total Tasks:</b> <code>{u['total_tasks']}</code>\n"
            f"📅 <b>Joined:</b> <code>{u['joined_at']}</code>\n"
            f"🏆 <b>Rank:</b> <code>Elite Member</code>"
        )
        bot.edit_message_caption(text, call.message.chat.id, call.message.message_id, reply_markup=back_btn())

    elif call.data == "live_tasks":
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
