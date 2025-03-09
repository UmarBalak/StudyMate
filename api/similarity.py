import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# File paths
PROCESSED_DATA_PATH = "users_preprocessed.csv"
RECOMMENDATIONS_PATH = "users_recommendations.csv"

# Load the preprocessed dataset
df = pd.read_csv(PROCESSED_DATA_PATH)

# Define feature columns (excluding non-numerical data)
feature_columns = df.columns.difference(["user_id", "name"])

# Calculate cosine similarity between users
similarity_matrix = cosine_similarity(df[feature_columns])

# Generate recommendations
recommendations = {}
for idx, row in df.iterrows():
    similar_indices = similarity_matrix[idx].argsort()[-4:-1][::-1]  # Get top 3 similar users
    recommendations[row["user_id"]] = [(df.iloc[i]["user_id"], similarity_matrix[idx][i]) for i in similar_indices]

# Assign recommendations to the dataframe
df["recommendations"] = df["user_id"].map(recommendations)

# Save the recommendations dataset
df.to_csv(RECOMMENDATIONS_PATH, index=False)

print(f"✅ Recommendations Complete! Saved as {RECOMMENDATIONS_PATH}")