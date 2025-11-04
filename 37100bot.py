from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import asyncio
import datetime
import json
import os
import requests
from telegram.ext import MessageHandler, filters

# ----------------------------------------------
# Config
# ----------------------------------------------
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
CHAT_ID = config.get("CHAT_ID", None)  # chat dove inviare il messaggio automatico

ORDINI_FILE = "ordini.json"
ORDINI_APERTI = True
EVENTO_ATTUALE = None

# ----------------------------------------------
# Utils
# ----------------------------------------------
def carica_ordini():
    if os.path.exists(ORDINI_FILE):
        with open(ORDINI_FILE, "r") as f:
            return json.load(f)
    return []

def salva_ordini(ordini):
    with open(ORDINI_FILE, "w") as f:
        json.dump(ordini, f, indent=4)

# ----------------------------------------------
# Funzione per fetch evento del giorno
# ----------------------------------------------
async def fetch_evento_giorno(app):
    global EVENTO_ATTUALE, ORDINI_APERTI
    try:
        url = f"{API_BASE_URL}/api/events/today?token={API_TOKEN}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        event = data.get("event", {}).get("title", None)
        if event:
            EVENTO_ATTUALE = data
            ORDINI_APERTI = True
            print(f"✅ Evento di oggi: {event}")

            # invio automatico messaggio giornaliero
            if CHAT_ID:
                data_str = data.get("date", "Data non disponibile")
                msg = (
                    f"👋 Buongiorno 37100!\n"
                    f"🗓 *Data:* {data_str}\n"
                    f"🎉 *Evento del giorno:* {event}\n\n"
                    "Usa /ordina per fare un ordine 🍕"
                )
                await app.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
            else:
                print("⚠️ CHAT_ID non configurato, messaggio non inviato.")
        else:
            EVENTO_ATTUALE = None
            ORDINI_APERTI = False
            print("ℹ️ Nessun evento per oggi.")
    except Exception as e:
        print(f"⚠️ Errore durante il fetch evento: {e}")
        EVENTO_ATTUALE = None
        ORDINI_APERTI = False

# ----------------------------------------------
# Task ciclico giornaliero
# ----------------------------------------------
async def ciclo_eventi(app):
    while True:
        now = datetime.datetime.now()
        if now.hour == 8 and now.minute == 0:
            await fetch_evento_giorno(app)
        if now.hour == 20 and now.minute == 0:
            global ORDINI_APERTI
            ORDINI_APERTI = False
            print("🕗 Ordini chiusi per oggi.")
        await asyncio.sleep(60)

# ----------------------------------------------
# /start
# ----------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global EVENTO_ATTUALE
    if EVENTO_ATTUALE:
        data_str = EVENTO_ATTUALE.get("date", "Data non disponibile")
        title = EVENTO_ATTUALE.get("event", {}).get("title", "Nessun evento oggi")
    else:
        data_str = datetime.datetime.now().strftime("%Y-%m-%d")
        title = "Nessun evento oggi"

    msg = (
        f"👋 Benvenuto nel bot 37100!\n"
        f"🗓 *Data:* {data_str}\n"
        f"🎉 *Evento del giorno:* {title}\n\n"
        "Usa /ordina per fare un ordine 🍕"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# ----------------------------------------------
# /ordina e altri
# ----------------------------------------------
async def ordina(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ORDINI_APERTI
    user = update.effective_user
    nome = f"{user.first_name or ''} {user.last_name or ''}".strip()
    user_id = user.id

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

# ----------------------------------------------
# Setup bot + ciclo eventi
# ----------------------------------------------
async def post_init(app):
    asyncio.create_task(ciclo_eventi(app))
    await fetch_evento_giorno(app)



# ----------------------------------------------
# Cancella qualsiasi messaggio non comando
# ----------------------------------------------


# Lista dei comandi consentiti
COMANDI_CONSENTITI = ["/start", "/ordina", "/lista", "/cancella", "/clear"]

async def elimina_non_comandi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    if not msg:
        # Cancella qualsiasi altro tipo di messaggio (immagine, sticker, ecc.)
        try:
            await update.message.delete()
        except Exception as e:
            print(f"Impossibile cancellare messaggio: {e}")
        return

    # Se non è uno dei comandi consentiti → elimina
    if not any(msg.startswith(cmd) for cmd in COMANDI_CONSENTITI):
        try:
            await update.message.delete()
        except Exception as e:
            print(f"Impossibile cancellare messaggio: {e}")




app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("ordina", ordina))
app.add_handler(CommandHandler("lista", lista))
app.add_handler(CommandHandler("cancella", cancella))
app.add_handler(CommandHandler("clear", clear))
app.add_handler(MessageHandler(filters.ALL, elimina_non_comandi))

print("🤖 Bot 37100 avviato con invio automatico eventi alle 08:00...")
app.run_polling()
