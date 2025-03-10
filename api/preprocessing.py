import pandas as pd
import numpy as np
import json
from sklearn.preprocessing import OneHotEncoder, MinMaxScaler
from db import connect_db

# Connect to NeonDB
conn = connect_db()
if not conn:
    print("❌ Database connection failed.")
    exit()

cursor = conn.cursor()

# Fetch user data from NeonDB
query = "SELECT * FROM users"
df = pd.read_sql(query, conn)

# One-hot encode categorical variables
categorical_cols = ["learning_style", "study_preference", "study_level"]
df = pd.get_dummies(df, columns=categorical_cols, drop_first=True)

# Normalize age
scaler = MinMaxScaler()
df["age"] = scaler.fit_transform(df[["age"]])

# 🔹 Convert DataFrame to Dictionary (Ensuring Structured JSON Storage)
df["encoded_features"] = df.drop(columns=["user_id", "name"]).apply(lambda x: x.to_dict(), axis=1)

# Clear previous processed data
cursor.execute("DELETE FROM preprocessed")

# Store structured JSON data in NeonDB (`preprocessed` table)
for _, row in df.iterrows():
    query = """
    INSERT INTO preprocessed (user_id, encoded_features) VALUES (%s, %s)
    """
    cursor.execute(query, (row["user_id"], json.dumps(row["encoded_features"])))  # Store as proper JSON

conn.commit()
cursor.close()
conn.close()

print("✅ Data Preprocessing Complete! Stored in NeonDB with structured JSON.")
