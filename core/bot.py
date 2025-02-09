from telegram.ext import Application

def create_bot(token: str) -> Application:
    return Application.builder().token(token).build()