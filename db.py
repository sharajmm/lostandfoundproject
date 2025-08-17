import mysql.connector
from mysql.connector import Error

def get_connection():
    try:
        connection = mysql.connector.connect(
            host="mysql.railway.internal",
            user="root",
            password="zrZXqNinWJhpKVgJCsvCZpPDZzjmUYrh",
            database="railway",
            port=3306
        )
        return connection
    except Error as e:
        print("❌ Error connecting to MySQL:", e)
        return None
