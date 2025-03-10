from db import connect_db

conn = connect_db()
if conn:
    print("✅ Connected to NeonDB!")
else:
    print("❌ Connection failed!")
