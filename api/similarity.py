import pandas as pd
import numpy as np
import json
from sklearn.metrics.pairwise import cosine_similarity
from db import connect_db

# Connect to NeonDB
conn = connect_db()
if not conn:
    print("❌ Database connection failed.")
    exit()

cursor = conn.cursor()

# Fetch preprocessed user data from NeonDB
query = "SELECT user_id, encoded_features FROM preprocessed"
df = pd.read_sql(query, conn)

# 🔹 Convert JSON features into structured DataFrame
def parse_json(x):
    if isinstance(x, str):  
        return json.loads(x)  
    return x  # If already a dictionary, return as is

df["encoded_features"] = df["encoded_features"].apply(parse_json)

# 🔹 Expand encoded features into separate columns
features = pd.json_normalize(df["encoded_features"])
features.insert(0, "user_id", df["user_id"])  # Restore user_id

# 🔹 Ensure all feature columns contain only numbers
feature_columns = features.columns.difference(["user_id"])
features[feature_columns] = features[feature_columns].apply(pd.to_numeric, errors="coerce").fillna(0)

# 🔹 Compute cosine similarity
similarity_matrix = cosine_similarity(features[feature_columns])

# 🔹 Generate recommendations
recommendations = {}
for idx, row in features.iterrows():
    similar_indices = similarity_matrix[idx].argsort()[-4:-1][::-1]  # Get top 3 similar users
    recommendations[row["user_id"]] = [int(features.iloc[i]["user_id"]) for i in similar_indices]

# 🔹 Store recommendations in NeonDB (`recommended` table)
cursor.execute("DELETE FROM recommended")  # Clear previous data
for user_id, recs in recommendations.items():
    postgres_array = "{" + ",".join(map(str, recs)) + "}"  # ✅ Convert list to PostgreSQL array format
    cursor.execute("INSERT INTO recommended (user_id, recommendations) VALUES (%s, %s)", (user_id, postgres_array))

conn.commit()
cursor.close()
conn.close()

print("✅ Recommendations Complete! Stored in NeonDB.")
