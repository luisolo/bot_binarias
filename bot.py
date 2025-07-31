



import os
import telebot
import schedule
import time
from datetime import datetime
import threading
import requests
import pytz  # Para zona horaria

from deriv_api import DerivAPI  # Asegúrate que tu módulo esté correctamente importado

# Carga tokens desde variables de entorno
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
DERIV_API_TOKEN = os.getenv('DERIV_API_TOKEN')

if not TELEGRAM_TOKEN or not DERIV_API_TOKEN:
    raise Exception("Por favor configura las variables de entorno TELEGRAM_BOT_TOKEN y DERIV_API_TOKEN")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
deriv = DerivAPI(DERIV_API_TOKEN)

USER_ID = 1506143302  # Tu ID de Telegram

# Zona horaria Guadalajara, Jalisco (UTC-6 sin horario de verano)
zona_mexico = pytz.timezone('America/Mexico_City')

def hora_actual_mexico():
    ahora_utc = datetime.utcnow().replace(tzinfo=pytz.utc)
    ahora_mexico = ahora_utc.astimezone(zona_mexico)
    return ahora_mexico.strftime('%Y-%m-%d %H:%M:%S')

# ✅ Verificar token Deriv
def verificar_token_deriv():
    try:
        response = requests.post(
            "https://frontend.binaryws.com/websockets/v3",
            json={"authorize": DERIV_API_TOKEN}
        )
        res_data = response.json()
        if "error" in res_data:
            bot.send_message(USER_ID, f"❌ Token inválido en Deriv: {res_data['error']['message']}")
        else:
            bot.send_message(USER_ID, "✅ Token de Deriv válido. Conexión exitosa.")
    except Exception as e:
        bot.send_message(USER_ID, f"❌ Error al verificar token de Deriv: {str(e)}")

verificar_token_deriv()

# 📈 Obtener datos del mercado
def obtener_datos_mercado(par='frxEURUSD', intervalo='1m'):
    try:
        datos = deriv.get_candles(symbol=par, interval=intervalo, count=10)
        return datos
    except Exception as e:
        print("Error al obtener datos del mercado:", e)
        return []

# 📢 Señal de prueba
def enviar_senal_prueba():
    ahora = hora_actual_mexico()
    par = 'EUR/USD'
    movimiento = 'Alcista'
    sesion = 'Sesión Europea'
    temporalidad = 'M1'
    mensaje = (f"📢 *SEÑAL DE PRUEBA*\n"
               f"Par: {par}\n"
               f"Movimiento: {movimiento}\n"
               f"Sesión: {sesion}\n"
               f"Entrada recomendada a las: {ahora}\n"
               f"Temporalidad: {temporalidad}\n"
               f"Estado: Señal de prueba, no operar con esta señal.")
    bot.send_message(USER_ID, mensaje, parse_mode='Markdown')

# ✅ Detección de señales reales para varios pares
pares_a_analizar = ['frxEURUSD', 'frxUSDJPY', 'frxGBPUSD', 'frxAUDUSD']

def detectar_senales_reales():
    for par in pares_a_analizar:
        datos = obtener_datos_mercado(par=par)
        if datos and len(datos) > 1:
            ultima_candle = datos[-1]
            anterior_candle = datos[-2]
            if ultima_candle['close'] > anterior_candle['close']:
                ahora = hora_actual_mexico()
                mensaje = (f"✅ *SEÑAL REAL DETECTADA*\n"
                           f"Par: {par[3:6]}/{par[6:]}\n"
                           f"Movimiento: Alcista\n"
                           f"Sesión: Sesión Europea\n"
                           f"Entrada recomendada a las: {ahora}\n"
                           f"Temporalidad: M1\n"
                           f"Estado: Señal real, evaluar para operar.")
                bot.send_message(USER_ID, mensaje, parse_mode='Markdown')
                # Reportar resultado tras 1 minuto
                threading.Timer(60, reportar_resultado, args=(par, ultima_candle, anterior_candle)).start()

# Reporte de ganada o perdida basado en cierre siguiente vela
def reportar_resultado(par, ultima_candle, anterior_candle):
    try:
        datos = obtener_datos_mercado(par=par)
        if datos and len(datos) > 0:
            siguiente_candle = datos[-1]
            ahora = hora_actual_mexico()
            # Simple ejemplo: ganada si cierre siguiente vela mayor que cierre anterior señal
            ganada = siguiente_candle['close'] > ultima_candle['close']
            resultado = "✅ Ganada" if ganada else "❌ Perdida"
            mensaje = (f"📊 *RESULTADO SEÑAL*\n"
                       f"Par: {par[3:6]}/{par[6:]}\n"
                       f"Resultado: {resultado}\n"
                       f"Hora reporte: {ahora}")
            bot.send_message(USER_ID, mensaje, parse_mode='Markdown')
    except Exception as e:
        print(f"Error al reportar resultado: {e}")

# ⚠️ Alerta previa de posible señal
def alerta_posible_senal():
    posible = True  # Aquí va la lógica real
    if posible:
        ahora = hora_actual_mexico()
        condicion = "Volumen creciente + Cierre cerca de resistencia"
        mensaje = (f"⚠️ *ATENCIÓN: POSIBLE ENTRADA*\n"
                   f"Condición a cumplirse: {condicion}\n"
                   f"Hora estimada: {ahora}\n"
                   f"Monitorear para confirmación.")
        bot.send_message(USER_ID, mensaje, parse_mode='Markdown')

# ⏱️ Programación de tareas
schedule.every(30).minutes.do(enviar_senal_prueba)
schedule.every(5).minutes.do(detectar_senales_reales)
schedule.every(10).minutes.do(alerta_posible_senal)

# 🧵 Hilo para ejecutar tareas
def run_schedule():
    enviar_senal_prueba()
    while True:
        schedule.run_pending()
        time.sleep(1)

threading.Thread(target=run_schedule, daemon=True).start()

# 🟢 Mantener bot activo
print("Bot activo y enviando señales con reporte de resultados...")

while True:
    time.sleep(10)
