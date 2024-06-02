
import json
import logging
import time
import re

import telebot
import random
import paho.mqtt.client as mqtt
from db_users import save_message
from config import BOT_TOKEN

AUTHORIZED_USERS = [1081721793]
logging.basicConfig(level=logging.INFO)
bot = telebot.TeleBot(BOT_TOKEN)

# MQTT configuration
MQTT_BROKER = "13.60.35.236"
MQTT_PORT = 1883
MQTT_TOPIC_REQUEST = "ttpu/User"
MQTT_TOPIC_RESPONSE = "ttpu/Response"
USERNAME = "userTTPU1"
PASSWORD = "mqttpass1"
client_id = f'python-mqtt-{random.randint(0, 1000)}'

# Initialize the MQTT client
mqtt_client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
mqtt_client.username_pw_set(USERNAME, PASSWORD)



responses = []

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker", flush=True)
        client.subscribe(MQTT_TOPIC_RESPONSE)  # Subscribe to the response topic
    else:
        print(f"Failed to connect to MQTT broker with result code {rc}", flush=True)

def on_message(client, userdata, msg):
    if msg.topic == MQTT_TOPIC_RESPONSE:
        response = msg.payload.decode()
        print(f"Received message on {MQTT_TOPIC_RESPONSE}: {response}", flush=True)
        responses.append(response)

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()

def is_authorized(user_id):
    return user_id in AUTHORIZED_USERS

def collect_responses(timeout, user_message, bot):
    start_time = time.time()
    while time.time() - start_time < timeout:
        if responses:
            for response in responses:
                bot.reply_to(user_message, response)
            responses.clear()
        time.sleep(0.1)
    responses.clear()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "You are not authorized to use this bot.")
        return
    bot.reply_to(message, "Hi! Send /ring to ring the bell.")
    save_message(message.from_user.id, message.from_user.username, message.text)

@bot.message_handler(commands=['ring'])
def ring_bell(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "You are not authorized to use this bot.")
        return

    mqtt_client.publish(MQTT_TOPIC_REQUEST, "ring")

    collect_responses(1.5, message, bot)
    save_message(message.from_user.id, message.from_user.username, message.text)

@bot.message_handler(commands=['status'])
def send_status(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "You are not authorized to use this bot.")
        return

    mqtt_client.publish(MQTT_TOPIC_REQUEST, "status")

    timeout = 1.5  # seconds
    start_time = time.time()
    while not responses and time.time() - start_time < timeout:
        time.sleep(0.1)

    if not responses:
        bot.reply_to(message, "Failed to get status update.")
    else:
        try:
            status_json = json.loads(responses[-1])
            response_message = json.dumps(status_json, indent=4)
            bot.reply_to(message, f"Status update:\n{response_message}")
        except json.JSONDecodeError as e:
            bot.reply_to(message, f"Failed to parse JSON status: {e}")
        responses.clear()
    save_message(message.from_user.id, message.from_user.username, message.text)

@bot.message_handler(commands=['play'])
def play_music(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "You are not authorized to use this bot.")
        return

    mqtt_client.publish(MQTT_TOPIC_REQUEST, "play")

    collect_responses(1.5, message, bot)
    save_message(message.from_user.id, message.from_user.username, message.text)

@bot.message_handler(commands=['stop'])
def ring_bell(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "You are not authorized to use this bot.")
        return

    mqtt_client.publish(MQTT_TOPIC_REQUEST, "stop")

    collect_responses(1.5, message, bot)
    save_message(message.from_user.id, message.from_user.username, message.text)

@bot.message_handler(content_types=['audio'])
def handle_audio(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "You are not authorized to use this bot.")
        return

    file_info = bot.get_file(message.audio.file_id)
    file_size = message.audio.file_size  # Size in bytes
    duration = message.audio.duration  # Duration in seconds

    if file_size > 2 * 1024 * 1024:  # 2 MB in bytes
        bot.reply_to(message, "Audio size must not exceed 2MB.")
    elif duration > 180:  # 3 minutes in seconds
        bot.reply_to(message, "Audio duration must not exceed 3 minutes.")
    else:
        file_path = file_info.file_path
        file_url = f'https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}'
        file_name = "ringbell_audio_1"
        mqtt_message = f'{file_name}: {file_url}'
        mqtt_client.publish(MQTT_TOPIC_REQUEST, mqtt_message)
        bot.reply_to(message, "Audio received and URL sent to MQTT broker.")
        collect_responses(60, message, bot)
        save_message(message.from_user.id, message.from_user.username, "Audio", file_url)

@bot.message_handler(content_types=['voice'])
def voice_processing(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "You are not authorized to use this bot.")
        return

    file_info = bot.get_file(message.voice.file_id)
    file_size = message.voice.file_size
    duration = message.voice.duration

    if file_size > 2 * 1024 * 1024:  # 2 MB in bytes
        bot.reply_to(message, "Voice message size must not exceed 2MB.")
    elif duration > 180:  # 3 minutes in seconds
        bot.reply_to(message, "Voice message duration must not exceed 3 minutes.")
    else:
        file_path = file_info.file_path
        file_url = f'https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}'
        file_name = "ringbell_audio_1"
        mqtt_message = f'{file_name}: {file_url}'
        mqtt_client.publish(MQTT_TOPIC_REQUEST, mqtt_message)
        bot.reply_to(message, "Voice message received and URL sent to MQTT broker.")
        collect_responses(60, message, bot)
        save_message(message.from_user.id, message.from_user.username, "Voice", file_url)

@bot.message_handler(func=lambda message: re.match(r'volume:\d$', message.text))
def set_volume(message):
    if not is_authorized(message.from_user.id):
        bot.reply_to(message, "You are not authorized to use this bot.")
        return

    volume_message = message.text
    volume_level = int(volume_message.split(":")[1])

    if 0 <= volume_level <= 9:
        mqtt_client.publish(MQTT_TOPIC_REQUEST, volume_message)
        bot.reply_to(message, f"Volume level set to {volume_level}.")
        save_message(message.from_user.id, message.from_user.username, message.text)
    else:
        bot.reply_to(message, "Invalid volume level. Please use a number between 0 and 9.")

if __name__ == "__main__":
    bot.polling()


