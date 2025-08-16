import mysql.connector
from mysql.connector import Error

def get_connection():
    try:
        import os
        connection = mysql.connector.connect(
            host=os.getenv("MYSQLHOST", "yamabiko.proxy.rlwy.net"),
            user=os.getenv("MYSQLUSER", "root"),
            password=os.getenv("MYSQLPASSWORD", "REQhKTFQXOPevISQZpCKcJAIgrxUOxuI"),
            database=os.getenv("MYSQLDATABASE", "railway"),
            port=int(os.getenv("MYSQLPORT", "31121"))
        )
        return connection
    except Error as e:
        print("❌ Error connecting to MySQL:", e)
        return None
