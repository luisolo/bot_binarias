import os
import telebot
import schedule
import time
from datetime import datetime, timedelta
import threading
import pandas as pd
import numpy as np
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator

from deriv_api import DerivAPI  # Tu módulo para API Deriv

# --- Configuración tokens ---
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
DERIV_API_TOKEN = os.getenv('DERIV_API_TOKEN')

if not TELEGRAM_TOKEN or not DERIV_API_TOKEN:
    raise Exception("Configura las variables de entorno TELEGRAM_BOT_TOKEN y DERIV_API_TOKEN")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
deriv = DerivAPI(DERIV_API_TOKEN)

USER_ID = 1506143302

PARES_A_ANALIZAR = [
    'frxEURUSD',  # EUR/USD
    'frxUSDJPY',  # USD/JPY
    'frxGBPUSD',  # GBP/USD
    'frxAUDUSD'   # AUD/USD
]

# Para controlar señales enviadas pendientes de resultado
señales_pendientes = []  # Lista de dicts: {'par':..., 'tipo_mov':..., 'hora_entrada': datetime}

def obtener_datos_mercado(par='frxEURUSD', intervalo='1m', count=50):
    try:
        datos = deriv.get_candles(symbol=par, interval=intervalo, count=count)
        return datos
    except Exception as e:
        print(f"Error al obtener datos del mercado para {par}: {e}")
        return []

def calcular_indicadores(df):
    df['ema20'] = EMAIndicator(df['close'], window=20).ema_indicator()
    df['rsi'] = RSIIndicator(df['close'], window=14).rsi()
    return df

def evaluar_condiciones(df):
    if len(df) < 20:
        return False, ""

    df = calcular_indicadores(df)

    close_actual = df['close'].iloc[-1]
    ema20_actual = df['ema20'].iloc[-1]
    rsi_actual = df['rsi'].iloc[-1]

    condiciones_cumplidas = 0

    if close_actual > ema20_actual:
        tendencia = 'alcista'
        condiciones_cumplidas += 1
    else:
        tendencia = 'bajista'
        condiciones_cumplidas += 1

    if tendencia == 'alcista' and rsi_actual < 70:
        condiciones_cumplidas += 1
    elif tendencia == 'bajista' and rsi_actual > 30:
        condiciones_cumplidas += 1

    vela_actual_alcista = df['close'].iloc[-1] > df['open'].iloc[-1]
    vela_actual_bajista = df['close'].iloc[-1] < df['open'].iloc[-1]
    if (tendencia == 'alcista' and vela_actual_alcista) or (tendencia == 'bajista' and vela_actual_bajista):
        condiciones_cumplidas += 1

    if condiciones_cumplidas >= 3:
        return True, tendencia
    else:
        return False, tendencia

def enviar_senal(par, tipo_mov, hora):
    par_readable = par.replace('frx', '').replace('fr', '') 
    mensaje = (
        f"✅ *SEÑAL REAL*\n"
        f"Par: {par_readable}\n"
        f"Movimiento: {tipo_mov}\n"
        f"Hora entrada: {hora}\n"
        f"Temporalidad: M1\n"
        f"¡Evalúa y opera con precaución!"
    )
    bot.send_message(USER_ID, mensaje, parse_mode='Markdown')

    # Registrar señal pendiente para revisión posterior
    señales_pendientes.append({
        'par': par,
        'tipo_mov': tipo_mov,
        'hora_entrada': datetime.strptime(hora, '%Y-%m-%d %H:%M:%S')
    })

def enviar_resultado(señal, resultado):
    par_readable = señal['par'].replace('frx', '').replace('fr', '') 
    mensaje = (
        f"📊 *RESULTADO DE SEÑAL*\n"
        f"Par: {par_readable}\n"
        f"Movimiento: {señal['tipo_mov']}\n"
        f"Hora entrada: {señal['hora_entrada'].strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Resultado: *{resultado}*\n"
    )
    bot.send_message(USER_ID, mensaje, parse_mode='Markdown')

def enviar_senal_prueba():
    ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    mensaje = f"📢 *SEÑAL DE PRUEBA* - Bot activo a las {ahora}"
    bot.send_message(USER_ID, mensaje, parse_mode='Markdown')

def detectar_senales_reales():
    for par in PARES_A_ANALIZAR:
        datos = obtener_datos_mercado(par=par)
        if not datos:
            print(f"No hay datos para analizar {par}")
            continue
        df = pd.DataFrame(datos)
        signal, tendencia = evaluar_condiciones(df)
        if signal:
            hora_entrada = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            tipo_mov = "CALL" if tendencia == 'alcista' else "PUT"
            enviar_senal(par, tipo_mov, hora_entrada)
        else:
            print(f"No se cumplen condiciones para señal real en {par}")

def revisar_resultados():
    # Revisa señales enviadas hace al menos 1 vela (1 min)
    ahora = datetime.now()
    señales_a_revisar = []

    for señal in señales_pendientes:
        if ahora >= señal['hora_entrada'] + timedelta(minutes=1):
            señales_a_revisar.append(señal)

    for señal in señales_a_revisar:
        datos = obtener_datos_mercado(par=señal['par'], count=2)
        if not datos or len(datos) < 2:
            print(f"No hay datos suficientes para revisar resultado {señal['par']}")
            continue

        df = pd.DataFrame(datos)
        vela_entrada = df.iloc[-2]  # vela de entrada
        vela_siguiente = df.iloc[-1]  # vela posterior para resultado

        resultado = None
        if señal['tipo_mov'] == "CALL":
            if vela_siguiente['close'] > vela_entrada['close']:
                resultado = "GANADA 🎉"
            else:
                resultado = "PERDIDA ❌"
        else:  # PUT
            if vela_siguiente['close'] < vela_entrada['close']:
                resultado = "GANADA 🎉"
            else:
                resultado = "PERDIDA ❌"

        enviar_resultado(señal, resultado)
        señales_pendientes.remove(señal)

# --- Schedule ---
schedule.every(30).minutes.do(enviar_senal_prueba)
schedule.every(5).minutes.do(detectar_senales_reales)
schedule.every(1).minutes.do(revisar_resultados)  # Revisar resultados cada minuto

def run_schedule():
    enviar_senal_prueba()
    while True:
        schedule.run_pending()
        time.sleep(1)

threading.Thread(target=run_schedule, daemon=True).start()

print("Bot activo y enviando señales con reporte de resultados...")

while True:
    time.sleep(10)



