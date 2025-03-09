import ast
import pandas as pd
import numpy as np
from sklearn.preprocessing import OneHotEncoder, MinMaxScaler

# File paths (centralized configuration)
RAW_DATA_PATH = "users.csv"
PROCESSED_DATA_PATH = "users_preprocessed.csv"

# Load dataset
df = pd.read_csv(RAW_DATA_PATH)

# Function to safely convert list-like strings into lists
def safe_eval(value):
    try:
        return ast.literal_eval(value)
    except:
        return []

# Convert list-like string columns to actual lists
list_columns = ["preferred_subjects", "strengths", "weaknesses", "availability"]
for col in list_columns:
    df[col] = df[col].apply(safe_eval)

# One-hot encode categorical variables
categorical_cols = ["learning_style", "study_preference", "study_level"]
df = pd.get_dummies(df, columns=categorical_cols, drop_first=True)

# Extract unique subjects for multi-hot encoding
unique_subjects = sorted(set(sub for sublist in df["preferred_subjects"] for sub in sublist))

# Multi-hot encode preferred subjects
subject_df = pd.DataFrame(0, index=df.index, columns=unique_subjects)
for idx, subjects in enumerate(df["preferred_subjects"]):
    subject_df.loc[idx, subjects] = 1

# Normalize age
scaler = MinMaxScaler()
df["age"] = scaler.fit_transform(df[["age"]])

# Merge processed data
df = pd.concat([df.drop(columns=["preferred_subjects", "strengths", "weaknesses", "availability"]), subject_df], axis=1)

# Save the processed dataset
df.to_csv(PROCESSED_DATA_PATH, index=False)

print(f"✅ Data Preprocessing Complete! Saved as {PROCESSED_DATA_PATH}")
