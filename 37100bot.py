import asyncio
import contextlib
import datetime
import json
import os
import aiohttp
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

CONFIG_FILE = "config.json"

def carica_config():
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError("❌ File config.json non trovato! Crealo con TOKEN, ADMIN_ID, API_BASE_URL, API_TOKEN e CHAT_ID.")
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

config = carica_config()
TOKEN = config["TOKEN"]
ADMIN_ID = config["ADMIN_ID"]
API_BASE_URL = config.get("API_BASE_URL", "http://localhost:3000")
API_TOKEN = config.get("API_TOKEN", "YOUR_TOKEN")

CHAT_ID = config.get("CHAT_ID", None)
THREAD_ID = config.get("THREAD_ID", None)

ORDINI_FILE = "ordini.json"
ORDINI_APERTI = True
EVENTO_ATTUALE = None
MAX_CLEAN_MESSAGES = 200

async def sleep_until(hour: int, minute: int):
    """Sleep until the next occurrence of the given hour/minute."""
    while True:
        now = datetime.datetime.now()
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if now >= target:
            target += datetime.timedelta(days=1)
        delta = (target - now).total_seconds()
        if delta <= 0:
            await asyncio.sleep(1)
            continue
        await asyncio.sleep(delta)
        return


async def invia_messaggio_gruppo(bot, text: str, context_desc: str = "messaggio"):
    """Invia un messaggio nel gruppo configurato gestendo topic e log degli errori."""
    if CHAT_ID is None:
        print(f"⚠️ CHAT_ID non configurato, {context_desc} non inviato.")
        return

    kwargs = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    if THREAD_ID is not None:
        kwargs["message_thread_id"] = THREAD_ID

    try:
        await bot.send_message(**kwargs)
    except Exception as e:
        print(f"⚠️ Errore invio {context_desc}: {e}")

def carica_ordini():
    if os.path.exists(ORDINI_FILE):
        with open(ORDINI_FILE, "r") as f:
            return json.load(f)
    return []


def salva_ordini(ordini):
    with open(ORDINI_FILE, "w") as f:
        json.dump(ordini, f, indent=4)

async def fetch_evento_giorno(app, send_auto_message: bool = True):
    global EVENTO_ATTUALE, ORDINI_APERTI
    session = app.bot_data.get("http_session")
    if not isinstance(session, aiohttp.ClientSession):
        print("⚠️ Sessione HTTP non disponibile per fetch_evento_giorno.")
        return

    url = f"{API_BASE_URL}/api/events/today?token={API_TOKEN}"
    timeout = aiohttp.ClientTimeout(total=5)
    try:
        async with session.get(url, timeout=timeout) as response:
            response.raise_for_status()
            data = await response.json()
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        print(f"⚠️ Errore durante il fetch evento: {e}")
        EVENTO_ATTUALE = None
        ORDINI_APERTI = False
        return
    except Exception as e:
        print(f"⚠️ Errore imprevisto durante il fetch evento: {e}")
        EVENTO_ATTUALE = None
        ORDINI_APERTI = False
        return

    event = data.get("event", {}).get("title")
    if not event:
        EVENTO_ATTUALE = None
        ORDINI_APERTI = False
        print("ℹ️ Nessun evento per oggi.")
        if send_auto_message:
            msg = (
                f"👋 Buongiorno 37100!\n"
                f"🗓 *Data:* {datetime.datetime.now().strftime('%Y-%m-%d')}\n"
                f"ℹ️ *Nessun evento oggi*\n\n"
                "❌ Gli ordini sono chiusi."
            )
            await invia_messaggio_gruppo(app.bot, msg, "messaggio automatico")
        return

    EVENTO_ATTUALE = data
    ORDINI_APERTI = True
    print(f"✅ Evento di oggi: {event}")

    if send_auto_message:
        data_str = data.get("date", "Data non disponibile")
        msg = (
            f"👋 Buongiorno 37100!\n"
            f"🗓 *Data:* {data_str}\n"
            f"🎉 *Evento del giorno:* {event}\n\n"
            "Usa /ordina per fare un ordine 🍕\nUsa /cancella per cancellarlo"
        )
        await invia_messaggio_gruppo(app.bot, msg, "messaggio automatico")

async def ciclo_eventi(app):
    while True:
        await sleep_until(8, 0)
        now = datetime.datetime.now()
        if now.weekday() == 2:
            await fetch_evento_giorno(app, send_auto_message=False)
            if EVENTO_ATTUALE:
                data_str = EVENTO_ATTUALE.get("date", "Data non disponibile")
                title = EVENTO_ATTUALE.get("event", {}).get("title", "Nessun evento oggi")
            else:
                data_str = now.strftime("%Y-%m-%d")
                title = "Nessun evento oggi"

            msg = (
                f"👋 Benvenuto nel bot 37100!\n"
                f"🗓 *Data:* {data_str}\n"
                f"🎉 *Evento del giorno:* {title}\n\n"
                "Usa /ordina per fare un ordine 🍕"
            )
            await invia_messaggio_gruppo(app.bot, msg, "messaggio di benvenuto")
        else:
            await fetch_evento_giorno(app)

        await sleep_until(20, 0)
        global ORDINI_APERTI
        ORDINI_APERTI = False
        print("🕗 Ordini chiusi per oggi.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global EVENTO_ATTUALE
    data_str = datetime.datetime.now().strftime("%Y-%m-%d")
    
    if EVENTO_ATTUALE:
        title = EVENTO_ATTUALE.get("event", {}).get("title")
        msg = (
            f"👋 Benvenuto nel bot 37100!\n"
            f"🗓 *Data:* {data_str}\n"
            f"🎉 *Evento del giorno:* {title}\n\n"
            "Usa /ordina per fare un ordine 🍕\nUsa /cancella per cancellarlo"
        )
    else:
        msg = (
            f"👋 Benvenuto nel bot 37100!\n"
            f"🗓 *Data:* {data_str}\n"
            f"ℹ️ *Nessun evento oggi*\n\n"
            "❌ Gli ordini sono chiusi."
        )
    
    await update.message.reply_text(msg, parse_mode="Markdown")

async def ordina(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ORDINI_APERTI, EVENTO_ATTUALE

    user = update.effective_user
    nome = f"{user.first_name or ''} {user.last_name or ''}".strip()
    user_id = user.id

    if not EVENTO_ATTUALE:
        await update.message.reply_text("❌ Nessun evento oggi, gli ordini sono chiusi!")
        return

    if not ORDINI_APERTI and user_id not in ADMIN_ID:
        await update.message.reply_text("🚫 Gli ordini sono chiusi per oggi!")
        return

    if not context.args:
        await update.message.reply_text("Devi scrivere cosa vuoi ordinare! Es: /ordina pizza margherita")
        return

    ordine_testo = " ".join(context.args)
    ordini = carica_ordini()

    if any(o["id"] == user_id for o in ordini):
        await update.message.reply_text("⚠️ Hai già fatto un ordine! Usa /cancella se vuoi modificarlo.")
        return

    ordini.append({"id": user_id, "nome": nome, "ordine": ordine_testo})
    salva_ordini(ordini)
    await update.message.reply_text(f"✅ Ordine registrato per {nome}: {ordine_testo}")

async def lista(update: Update, context: ContextTypes.DEFAULT_TYPE):

    ordini = carica_ordini()
    if not ordini:
        await update.message.reply_text("📭 Nessun ordine presente.")
        return
    testo = "\n".join([f"{o['nome']}: {o['ordine']}" for o in ordini])
    await update.message.reply_text("📋 Lista ordini:\n" + testo)

async def cancella(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id
    ordini = carica_ordini()
    nuovi = [o for o in ordini if o["id"] != user_id]
    if len(nuovi) == len(ordini):
        await update.message.reply_text("❌ Non hai nessun ordine da cancellare.")
        return
    salva_ordini(nuovi)
    await update.message.reply_text("🗑️ Il tuo ordine è stato cancellato.")

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id
    if user_id not in ADMIN_ID:
        await update.message.reply_text("❌ Non hai i permessi per questo comando.")
        return
    salva_ordini([])
    await update.message.reply_text("🧹 Tutti gli ordini sono stati cancellati!")

async def post_init(app):
    timeout = aiohttp.ClientTimeout(total=10)
    app.bot_data["http_session"] = aiohttp.ClientSession(timeout=timeout)
    asyncio.create_task(ciclo_eventi(app))
    await fetch_evento_giorno(app)


async def on_shutdown(app):
    session = app.bot_data.get("http_session")
    if isinstance(session, aiohttp.ClientSession) and not session.closed:
        await session.close()

async def clean(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancella tutti i messaggi nel thread corrente (solo admin)"""
    user_id = update.effective_user.id
    if user_id not in ADMIN_ID:
        await update.message.reply_text("❌ Non hai i permessi per questo comando.")
        return

    limit = MAX_CLEAN_MESSAGES
    if context.args:
        try:
            requested = int(context.args[0])
        except ValueError:
            await update.message.reply_text("⚠️ Valore non valido. Usa ad esempio /clean 50.")
            return
        limit = max(1, min(requested, MAX_CLEAN_MESSAGES))

    try:
        command_message_id = update.message.message_id
        chat_id = update.message.chat_id
        thread_id = update.message.message_thread_id

        status_msg = await update.message.reply_text(
            f"🧹 Pulizia in corso (max {limit} messaggi)..."
        )
        
        deleted = 0
        min_message_id = max(command_message_id - limit, 0)
        for message_id in range(command_message_id, min_message_id, -1):
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
                deleted += 1
            except Exception:
                continue
            await asyncio.sleep(0)

        try:
            await status_msg.edit_text(f"✅ Cancellati {deleted} messaggi (max {limit}).")
            await asyncio.sleep(1)
            await status_msg.delete()
            with contextlib.suppress(Exception):
                await update.message.delete()
        except Exception:
            pass
            
        print(f"✅ Cancellati {deleted} messaggi dal thread {thread_id}")
        
    except Exception as e:
        print(f"⚠️ Errore durante la pulizia messaggi: {e}")
        await update.message.reply_text("⚠️ Errore durante la cancellazione dei messaggi.")

app = ApplicationBuilder().token(TOKEN).post_init(post_init).post_shutdown(on_shutdown).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("ordina", ordina))
app.add_handler(CommandHandler("lista", lista))
app.add_handler(CommandHandler("cancella", cancella))
app.add_handler(CommandHandler("clear", clear))
app.add_handler(CommandHandler("clean", clean))

print("🤖 Bot 37100 avviato con invio automatico eventi alle 08:00...")
app.run_polling()
