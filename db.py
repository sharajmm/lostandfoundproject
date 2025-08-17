import mysql.connector
from mysql.connector import Error

def get_connection():
    try:
        connection = mysql.connector.connect(
    host="shinkansen.proxy.rlwy.net",
    user="root",
    password="zrZXqNinWJhpKVgJCsvCZpPDZzjmUYrh",
    database="railway",
    port=20241
)
        return connection
    except Error as e:
        print("❌ Error connecting to MySQL:", e)
        return None
