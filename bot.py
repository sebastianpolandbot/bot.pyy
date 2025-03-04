import os
import requests
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from langdetect import detect  # Librería para detección de idioma
from textblob import TextBlob  # Librería para análisis de sentimientos

# Usar variables de entorno en producción
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
API_TOKEN = os.getenv('API_TOKEN')

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Diccionario para almacenar el contexto de la conversación
user_context = {}

# Definimos los idiomas soportados
SUPPORTED_LANGUAGES = ['en', 'pl', 'uk', 'ru']  # inglés, polaco, ucraniano, ruso

# Función para detectar el idioma del mensaje
def detect_language(text):
    try:
        return detect(text)  # Detecta el idioma del texto
    except:
        return "en"  # Si no se puede detectar, default a inglés

def detect_sentiment(text):
    # Usamos TextBlob para detectar el sentimiento en el mensaje
    analysis = TextBlob(text)
    if analysis.sentiment.polarity < -0.2:
        return "negative"  # Negativo (molesto, frustrado)
    elif analysis.sentiment.polarity > 0.2:
        return "positive"  # Positivo (feliz, interesado)
    else:
        return "neutral"  # Neutral

# Función para obtener la predicción de ventas utilizando Gemini API
def get_sales_prediction(product_name):
    try:
        # Usamos la API de Gemini para obtener la predicción de ventas
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
        headers = {'Content-Type': 'application/json'}
        
        data = {
            "contents": [{
                "role": "user",
                "parts": [{
                    "text": f"Please provide a detailed sales prediction for the product '{product_name}' in 2025. Include data on market trends, expected sales growth, potential consumer demand, and any advice for businesses on how to improve sales for this product in the upcoming year. Be as specific as possible."
                }]
            }],
            "generationConfig": {
                "maxOutputTokens": 250,
                "temperature": 0.7  # Higher temperature for more creative answers
            }
        }

        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 200:
            response_json = response.json()
            if 'candidates' in response_json and len(response_json['candidates']) > 0:
                sales_prediction = response_json['candidates'][0]['content']['parts'][0]['text']
                return sales_prediction
            else:
                return "Sorry, I couldn't retrieve a sales prediction. Please try again later."
        else:
            return "Oops, something went wrong while fetching the sales prediction. Please try again later."

    except Exception as e:
        return f"An error occurred while fetching the sales prediction: {str(e)}"


@dp.message(Command("start"))
async def start_message(message: types.Message):
    # Guardamos el contexto de la conversación cuando el usuario inicia
    user_context[message.from_user.id] = {"conversation": []}
    await message.reply("Hello! How can I assist you today? 😊 Feel free to ask me anything!")

@dp.message()
async def handle_message(message: types.Message):
    user_message = message.text
    user_id = message.from_user.id
    
    # Verificar el contexto de la conversación del usuario
    if user_id not in user_context:
        user_context[user_id] = {"conversation": []}
    
    # Detectamos el sentimiento del mensaje
    sentiment = detect_sentiment(user_message)
    
    # Guardamos el mensaje en el contexto del usuario
    user_context[user_id]["conversation"].append({"user": user_message, "sentiment": sentiment})
    
    # Respuestas predefinidas según el sentimiento
    if sentiment == "negative":
        reply = "I'm really sorry to hear that you're feeling upset. 😔 How can I help to make things better?"
    elif sentiment == "positive":
        reply = "I’m glad to hear you’re doing well! 😄 How can I assist you today?"
    else:
        reply = "I see you're just looking for some info! How can I assist you with your purchase today?"
    
    # Detectamos el idioma del mensaje del usuario
    detected_language = detect_language(user_message)
    print(f"Detected Language: {detected_language}")  # Para verificar el idioma detectado
    
    # Si el idioma detectado no está en los soportados, asignamos inglés como predeterminado
    if detected_language not in SUPPORTED_LANGUAGES:
        detected_language = 'en'

    # Si el usuario pregunta por la predicción de ventas de un producto
    if "sales prediction" in user_message.lower() or "predicción de ventas" in user_message.lower():
        # Extraemos el nombre del producto de la consulta
        product_name = user_message.split("sales prediction")[-1].strip()  # o puedes usar una expresión regular
        sales_prediction = get_sales_prediction(product_name)
        reply = f"Sales prediction for {product_name}: {sales_prediction}"

        # Complementamos la respuesta con recomendaciones y tendencias:
        reply += "\n\nFor better sales performance, consider focusing on key trends like:"
        reply += "\n1. Emphasizing ease of use and convenience for busy customers."
        reply += "\n2. Offering specialized features such as non-stick surfaces, quick cooking times, or multi-functional options."
        reply += "\n3. Targeting the growing trend of health-conscious consumers with products that offer lower-fat options or customizable features."

    # Recuperamos el último mensaje del usuario en el contexto para darle un toque más fluido a la conversación
    if len(user_context[user_id]["conversation"]) > 1:
        previous_message = user_context[user_id]["conversation"][-2]["user"]
        reply += f"\n\nLast time you mentioned: {previous_message}. How can I assist you further with that?"

    # Usamos la API de Gemini para generar una respuesta más detallada y creativa
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
        headers = {'Content-Type': 'application/json'}
        data = {
            "contents": [{
                "role": "user",
                "parts": [{
                    "text": f"You're interacting with a bot. Based on the tone of the conversation, please give a friendly and empathetic response in {detected_language}. Message: {user_message}"
                }]
            }],
            "generationConfig": {
                "maxOutputTokens": 150,
                "temperature": 0.7  # Higher temperature for more creative answers
            }
        }

        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 200:
            response_json = response.json()
            if 'candidates' in response_json and len(response_json['candidates']) > 0:
                bot_response = response_json['candidates'][0]['content']['parts'][0]['text']
                reply = bot_response
            else:
                reply = "Sorry, I didn't get that. Could you please rephrase?"
        else:
            reply = "Oops, something went wrong. Please try again later."

    except Exception as e:
        reply = "I'm experiencing technical issues. Please try again later."
        logging.error(f"Error: {str(e)}")

    # Enviamos la respuesta sin el parse_mode (sin formato Markdown)
    await message.reply(reply)  # Sin el parse_mode

async def on_start():
    await dp.start_polling(bot)

if __name__ == '__main__':
    import asyncio
    asyncio.run(on_start())
