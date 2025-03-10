import psycopg2
from db import connect_db

# Connect to NeonDB
conn = connect_db()
if not conn:
    print("❌ Database connection failed.")
    exit()

cursor = conn.cursor()

# Fetch all users from the `users` table
cursor.execute("SELECT user_id, name FROM users")
users = cursor.fetchall()

# Insert user credentials into `login` table
for user in users:
    user_id, name = user
    username = name.replace(" ", "").lower()  # Convert to lowercase, remove spaces
    password = username  # Username and password are the same for dummy data

    query = """
    INSERT INTO login (user_id, username, password) VALUES (%s, %s, %s)
    """
    cursor.execute(query, (user_id, username, password))

conn.commit()
cursor.close()
conn.close()

print("✅ Login table populated successfully!")
