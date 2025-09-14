import mysql.connector
from mysql.connector import Error

def get_connection():
    try:
        connection = mysql.connector.connect(
    host="nozomi.proxy.rlwy.net",
    user="root",
    password="ywmbuzUuphBSddsLtVqMksebsGEpQSRi",
    database="railway",
    port=49885
)
        return connection
    except Error as e:
        print("❌ Error connecting to MySQL:", e)
        return None
