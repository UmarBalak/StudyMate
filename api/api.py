from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
import subprocess
import os

# File paths
USERS_CSV = "users.csv"
PROCESSED_CSV = "users_preprocessed.csv"
RECOMMENDATIONS_CSV = "users_recommendations.csv"

app = FastAPI()

# 📌 User Registration Model (Matches CSV Structure)
class User(BaseModel):
    name: str
    age: int
    study_level: str  # Beginner, Intermediate, Advanced
    preferred_subjects: list[str]  # List of selected subjects
    strengths: list[str]
    weaknesses: list[str]
    learning_style: str  # Visual, Auditory, Problem-Solving, Text-based
    study_preference: str  # Solo or Group
    availability: list[str]  # Morning, Afternoon, Evening, Night

# 📌 Load dataset functions
def load_users():
    if not os.path.exists(USERS_CSV):
        return pd.DataFrame(columns=["user_id", "name", "age", "study_level", "preferred_subjects", "strengths",
                                     "weaknesses", "learning_style", "study_preference", "availability"])
    return pd.read_csv(USERS_CSV, dtype={"user_id": int})  # Force user_id as int

def load_recommendations():
    if not os.path.exists(RECOMMENDATIONS_CSV):
        return pd.DataFrame(columns=["user_id", "recommendations"])
    return pd.read_csv(RECOMMENDATIONS_CSV)

@app.get("/")
def home():
    return {"message": "StudyMate API is running!"}

# ✅ Register a new user
@app.post("/register/")
def register_user(user: User):
    try:
        df = load_users()

        # Ensure "user_id" column exists and is numeric
        if df.empty or "user_id" not in df.columns:
            new_user_id = 1
        else:
            df["user_id"] = pd.to_numeric(df["user_id"], errors="coerce").fillna(0).astype(int)
            new_user_id = df['user_id'].max() + 1

        print(f"New User ID: {new_user_id}")

        # Convert User object to dictionary
        user_data = user.dict()
        user_data["user_id"] = new_user_id

        # Create DataFrame and reorder columns to put user_id first
        new_user_df = pd.DataFrame([user_data])
        columns = ["user_id"] + [col for col in new_user_df.columns if col != "user_id"]
        new_user_df = new_user_df[columns]

        # Append to CSV
        new_user_df.to_csv(USERS_CSV, mode='a', header=not os.path.exists(USERS_CSV), index=False)
        
        # 🔄 Recalculate recommendations
        subprocess.run(["python", "preprocessing.py"])
        subprocess.run(["python", "similarity.py"])

        return {"message": "User registered successfully!", "user_id": new_user_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ✅ Get study partner recommendations
@app.get("/recommend/{user_id}")
def get_recommendations(user_id: int):
    df = load_recommendations()
    users_data = load_users()

    if df.empty or user_id not in df["user_id"].values:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_info = {}
    user = users_data[users_data["user_id"] == user_id].to_dict(orient="records")[0]
    user.pop("user_id")
    user_info[user_id] = user

    recommendations = eval(df[df["user_id"] == user_id]["recommendations"].values[0])
    recommended_users = {}

    for user in recommendations:
        id = int(user[0])
        user_data = users_data[users_data["user_id"] == id].to_dict(orient="records")[0]
        user_data.pop("user_id")
        user_data["score"] = float(user[1])
        recommended_users[id] = user_data


    return {
        "user": user_info,
        "recommendations": recommended_users
    }
