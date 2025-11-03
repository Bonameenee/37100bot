from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import json
import os

# ----------------------------------------------
# Carica configurazione da file JSON esterno
# ----------------------------------------------
CONFIG_FILE = "config.json"

def carica_config():
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError("❌ File config.json non trovato! Crealo con TOKEN e ADMIN_ID.")
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

config = carica_config()
TOKEN = config["TOKEN"]
ADMIN_ID = config["ADMIN_ID"]

# File dove vengono salvati gli ordini
ORDINI_FILE = "ordini.json"

# ----------------------------------------------
# Funzione per caricare gli ordini dal file JSON
# ----------------------------------------------
def carica_ordini():
    if os.path.exists(ORDINI_FILE):
        with open(ORDINI_FILE, "r") as f:
            return json.load(f)
    return []

# ----------------------------------------------
# Funzione per salvare gli ordini nel file JSON
# ----------------------------------------------
def salva_ordini(ordini):
    with open(ORDINI_FILE, "w") as f:
        json.dump(ordini, f, indent=4)

# ----------------------------------------------
# Comando /start
# Messaggio di benvenuto iniziale
# ----------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Ciao! Sono il bot per gli ordini di cibo 🍕\n"
        "Usa /ordina per fare un ordine.\n"
        "Puoi cancellare il tuo con /cancella."
    )

# ----------------------------------------------
# Comando /ordina
# Ogni utente può avere solo un ordine
# ----------------------------------------------
async def ordina(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    nome = user.first_name or ""
    cognome = user.last_name or ""
    nome_completo = f"{nome} {cognome}".strip()
    user_id = user.id

    # Controlla che l'utente abbia scritto qualcosa dopo /ordina
    if not context.args:
        await update.message.reply_text("Devi scrivere cosa vuoi ordinare! Es: /ordina pizza margherita")
        return

    ordine_testo = " ".join(context.args)

    # Carica ordini esistenti
    ordini = carica_ordini()

    # Controlla se l'utente ha già un ordine registrato
    for o in ordini:
        if o["id"] == user_id:
            await update.message.reply_text("⚠️ Hai già fatto un ordine! Usa /cancella se vuoi modificarlo.")
            return

    # Aggiunge il nuovo ordine con ID utente
    ordini.append({
        "id": user_id,
        "nome": nome_completo,
        "ordine": ordine_testo
    })

    # Salva gli ordini aggiornati
    salva_ordini(ordini)

    await update.message.reply_text(f"✅ Ordine registrato per {nome_completo}: {ordine_testo}")

# ----------------------------------------------
# Comando /lista
# Mostra tutti gli ordini salvati
# ----------------------------------------------
async def lista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ordini = carica_ordini()

    if not ordini:
        await update.message.reply_text("📭 Nessun ordine presente.")
        return

    testo = "\n".join([f"{o['nome']}: {o['ordine']}" for o in ordini])
    await update.message.reply_text("📋 Lista ordini:\n" + testo)

# ----------------------------------------------
# Comando /cancella
# Permette all'utente di eliminare solo il proprio ordine
# ----------------------------------------------
async def cancella(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ordini = carica_ordini()

    # Filtra gli ordini mantenendo solo quelli che NON appartengono all'utente
    nuovi_ordini = [o for o in ordini if o["id"] != user_id]

    # Se la lista non cambia, vuol dire che l'utente non aveva un ordine
    if len(nuovi_ordini) == len(ordini):
        await update.message.reply_text("❌ Non hai nessun ordine da cancellare.")
        return

    # Salva la nuova lista di ordini
    salva_ordini(nuovi_ordini)
    await update.message.reply_text("🗑️ Il tuo ordine è stato cancellato.")

# ----------------------------------------------
# Comando /clear
# Cancella tutti gli ordini (solo admin)
# ----------------------------------------------
async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Controlla che chi esegue il comando sia nella lista degli admin
    if user_id not in ADMIN_ID:
        await update.message.reply_text("❌ Non hai i permessi per cancellare tutti gli ordini.")
        return

    salva_ordini([])  # Svuota completamente la lista
    await update.message.reply_text("🧹 Tutti gli ordini sono stati cancellati!")

# ----------------------------------------------
# Avvio del bot e registrazione dei comandi
# ----------------------------------------------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("ordina", ordina))
app.add_handler(CommandHandler("lista", lista))
app.add_handler(CommandHandler("cancella", cancella))
app.add_handler(CommandHandler("clear", clear))

print("Bot ordini cibo avviato... 🍕")
app.run_polling()