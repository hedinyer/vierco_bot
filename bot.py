#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Mar 26 15:15:48 2026

@author: hedinyer
"""

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import logging
import os


async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(f"Hello {update.effective_user.first_name}")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Responde a mensajes de texto normales para que el bot no parezca "muerto"
    si el usuario no escribe el comando con '/'.
    """
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()
    if text.startswith("/"):
        # No intentamos manejar comandos aquí; los de CommandHandler se encargan.
        return
    await update.message.reply_text("Recibido: " + text + "\n\nPrueba: /hello")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
)

# RECOMENDADO: define el token con una variable de entorno `TELEGRAM_BOT_TOKEN`.
# Dejamos fallback al token existente para que puedas probar rápido.
BOT_TOKEN = (
    os.environ.get("TELEGRAM_BOT_TOKEN")
)

if BOT_TOKEN is None:
    BOT_TOKEN = "8560443034:AAGaDYgab47RbD8REFiQnncajFC8Ocpt7q8"

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("hello", hello))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

app.run_polling()