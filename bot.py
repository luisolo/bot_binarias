import os
import telebot
import schedule
import time
from datetime import datetime
from deriv_api import DerivAPI
import threading

# Carga tokens desde variables de entorno
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
DERIV_API_TOKEN = os.getenv('DERIV_API_TOKEN')

if not TELEGRAM_TOKEN or not DERIV_API_TOKEN:
    raise Exception("Por favor configura las variables de entorno TELEGRAM_BOT_TOKEN y DERIV_API_TOKEN")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
USER_ID = 1506143302  # Tu ID de Telegram para recibir los mensajes

# Instancia de conexión a Deriv
deriv = DerivAPI(DERIV_API_TOKEN)

# ✅ Función para verificar el token Deriv
def verificar_token_deriv():
    try:
        respuesta = deriv.send({"authorize": DERIV_API_TOKEN})
        if "error" in respuesta:
            print(f"[❌ DERIV] Token inválido: {respuesta['error']['message']}")
            bot.send_message(USER_ID, f"❌ Token de Deriv inválido: {respuesta['error']['message']}")
        else:
            login_id = respuesta.get("authorize", {}).get("loginid", "Desconocido")
            print(f"[✅ DERIV] Token válido. Usuario: {login_id}")
            bot.send_message(USER_ID, f"✅ Token de Deriv válido. Usuario: {login_id}")
    except Exception as e:
        print(f"[⚠️ DERIV] Error de conexión: {e}")
        bot.send_message(USER_ID, f"⚠️ Error al verificar token de Deriv: {e}")

# Llamada inicial
verificar_token_deriv()

# 📊 Obtener datos de mercado
def obtener_datos_mercado(par='frxEURUSD', intervalo='1m'):
    datos = deriv.get_candles(symbol=par, interval=intervalo, count=10)
    return datos

# 📢 Señal de prueba
def enviar_senal_prueba():
    ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    mensaje = (
        f"📢 *SEÑAL DE PRUEBA*\n"
        f"Par: EUR/USD\nMovimiento: Alcista\n"
        f"Sesión: Sesión Europea\n"
        f"Entrada recomendada a las: {ahora}\n"
        f"Temporalidad: M1\n"
        f"Estado: Señal de prueba, no operar con esta señal."
    )
    bot.send_message(USER_ID, mensaje, parse_mode='Markdown')

# ✅ Señales reales
def detectar_senales_reales():
    datos = obtener_datos_mercado()
    if datos and len(datos) > 1:
        ultima = datos[-1]
        anterior = datos[-2]
        if ultima['close'] > anterior['close']:
            ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            mensaje = (
                f"✅ *SEÑAL REAL DETECTADA*\n"
                f"Par: EUR/USD\nMovimiento: Alcista\n"
                f"Sesión: Sesión Europea\n"
                f"Entrada recomendada a las: {ahora}\n"
                f"Temporalidad: M1\n"
                f"Estado: Señal real, evaluar para operar."
            )
            bot.send_message(USER_ID, mensaje, parse_mode='Markdown')

# ⚠️ Alerta previa
def alerta_posible_senal():
    ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    condicion = "Volumen creciente + Cierre cerca de resistencia"
    mensaje = (
        f"⚠️ *ATENCIÓN: POSIBLE ENTRADA*\n"
        f"Condición a cumplirse: {condicion}\n"
        f"Hora estimada: {ahora}\n"
        f"Monitorear para confirmación."
    )
    bot.send_message(USER_ID, mensaje, parse_mode='Markdown')

# 🕒 Jobs programados
schedule.every(30).minutes.do(enviar_senal_prueba)
schedule.every(5).minutes.do(detectar_senales_reales)
schedule.every(10).minutes.do(alerta_posible_senal)
schedule.every().hour.do(verificar_token_deriv)  # Verificación cada hora

# 🔁 Hilo para ejecutar programación
def run_schedule():
    enviar_senal_prueba()
    while True:
        schedule.run_pending()
        time.sleep(1)

threading.Thread(target=run_schedule, daemon=True).start()

# 🟢 Mantener el bot activo
print("Bot activo y enviando señales...")

while True:
    time.sleep(10)

