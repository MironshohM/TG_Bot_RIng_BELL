from config import DB_HOST, DB_NAME, DB_USER, DB_PASS
import mysql.connector
from datetime import datetime

db_connection = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASS,
    database=DB_NAME
)
db_cursor = db_connection.cursor()


def save_message(user_id, username, message_text, message_url=None):
    timestamp = datetime.now()
    query = "INSERT INTO user_messages (user_id, username, message_text, message_time, message_url) VALUES (%s, %s, %s, %s, %s)"
    values = (user_id, username, message_text, timestamp, message_url)
    db_cursor.execute(query, values)
    db_connection.commit()
