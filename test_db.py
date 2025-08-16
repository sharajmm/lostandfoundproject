from db import get_connection

conn = get_connection()

if conn:
    print("✅ MySQL Connected Successfully!")
    conn.close()
else:
    print("❌ Connection Failed!")
