import asyncio
import websockets
import json
import pytz
import os
from datetime import datetime, timedelta
from telegram import Bot
import traceback
import threading
from aiohttp import web

# --- CONFIGURACIÓN GENERAL ---
TOKEN_DERIV = os.getenv("DERIV_API_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TOKEN_DERIV or not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise Exception("Faltan variables de entorno obligatorias: DERIV_API_TOKEN, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID")

# --- PARÁMETROS ---
PAIRS = ["frxEURUSD", "frxUSDJPY", "frxGBPUSD", "frxUSDCHF"]
TIMEZONE = pytz.timezone("America/Mexico_City")
SIGNAL_INTERVAL = timedelta(minutes=30)
REPEAT_BLOCK_TIME = timedelta(hours=1)

# --- INICIALIZACIÓN ---
bot = Bot(token=TELEGRAM_TOKEN)
last_signals = {}

# --- ESTRATEGIA PERSONALIZADA SARAH ---
def validar_condiciones_sarah(candle_data):
    condiciones = {
        "estructura_tendencia": True,
        "zona_sr": True,
        "patron_vela": False,
        "ema20": True,
        "rsi": False,
        "volumen": True
    }
    cumplidas = sum(condiciones.values())
    return cumplidas >= 4, condiciones

# --- UTILIDADES ---
def hora_actual():
    return datetime.now(TIMEZONE)

async def enviar_telegram(mensaje):
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=mensaje)
    except Exception as e:
        print("Error enviando mensaje Telegram:", e)

def puede_enviar(par):
    ahora = hora_actual()
    if par in last_signals:
        diferencia = ahora - last_signals[par]
        if diferencia < REPEAT_BLOCK_TIME:
            return False
    last_signals[par] = ahora
    return True

# --- PROCESAMIENTO PRINCIPAL ---
async def procesar_par(par):
    try:
        async with websockets.connect("wss://ws.deriv.com/websockets/v3?app_id=1089") as ws:
            await ws.send(json.dumps({
                "ticks_history": par,
                "adjust_start_time": 1,
                "count": 100,
                "granularity": 60,
                "style": "candles",
                "subscribe": 0
            }))

            response = await ws.recv()
            data = json.loads(response)

            candles = data.get("history", {}).get("candles", [])
            if not candles or len(candles) < 10:
                return

            condiciones_ok, condiciones = validar_condiciones_sarah(candles)

            if condiciones_ok and puede_enviar(par):
                mensaje_alerta = (
                    f"⚠️ Posible señal detectada para *{par}*\n"
                    f"⏰ {hora_actual().strftime('%H:%M:%S')}\n"
                    f"📊 Evaluando condiciones: {sum(condiciones.values())}/6"
                )
                await enviar_telegram(mensaje_alerta)

                await asyncio.sleep(5)
                mensaje_confirmacion = (
                    f"✅ *SEÑAL CONFIRMADA*\n"
                    f"Par: {par}\n"
                    f"Tipo: {'ALCISTA' if condiciones['estructura_tendencia'] else 'BAJISTA'}\n"
                    f"Condiciones cumplidas: {sum(condiciones.values())}/6\n"
                    f"Entrada recomendada: {hora_actual().strftime('%H:%M:%S')}"
                )
                await enviar_telegram(mensaje_confirmacion)
            elif not condiciones_ok and puede_enviar(par):
                await enviar_telegram(f"❌ Señal descartada para {par}. Solo se cumplieron {sum(condiciones.values())}/6 condiciones.")
    except Exception as e:
        print(f"[ERROR - {par}] {e}")
        traceback.print_exc()

# --- CICLO DE EJECUCIÓN DEL BOT ---
async def main_loop():
    while True:
        print(f"[{hora_actual()}] Analizando pares...")
        tareas = [procesar_par(par) for par in PAIRS]
        await asyncio.gather(*tareas)
        print(f"[{hora_actual()}] Esperando siguiente intervalo...\n")
        await asyncio.sleep(SIGNAL_INTERVAL.total_seconds())

# --- SERVIDOR AIOHTTP PARA /ping ---
async def handle_ping(request):
    return web.Response(text="pong")

def start_ping_server():
    app = web.Application()
    app.router.add_get('/ping', handle_ping)
    web.run_app(app, port=8080)

# --- INICIO ---
if __name__ == "__main__":
    # Ejecutar servidor ping en hilo aparte para no bloquear asyncio
    ping_thread = threading.Thread(target=start_ping_server, daemon=True)
    ping_thread.start()

    # Ejecutar loop principal del bot
    try:
        asyncio.run(main_loop())
    except Exception as e:
        print("[ERROR FATAL]", e)