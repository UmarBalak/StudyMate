from fastapi import FastAPI, HTTPException, Query, Depends, Header
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
import uuid
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()
# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI()

# CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def get_db_connection():
    return await asyncpg.create_pool(DATABASE_URL)

# Session storage (Temporary)
active_sessions = {}

# Pydantic Models
class SignUpData(BaseModel):
    username: str
    password: str

class PreferencesData(BaseModel):
    name: str
    age: int
    study_level: str
    preferred_subjects: list[str]
    strengths: list[str]
    weaknesses: list[str]
    learning_style: str
    study_preference: str
    availability: list[str]

class LoginData(BaseModel):
    username: str
    password: str

@app.get("/")
def read_root():
    return {"message": "Welcome to StudyMate API!"}

@app.post("/signup/")
async def signup(signup_data: SignUpData, db=Depends(get_db_connection)):
    async with db.acquire() as conn:
        existing_user = await conn.fetchrow("SELECT user_id FROM login WHERE username=$1", signup_data.username)
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exists")

        new_user = await conn.fetchrow(
            """
            INSERT INTO users (name, age, study_level, preferred_subjects, strengths, weaknesses, learning_style, study_preference, availability)
            VALUES ('', 0, '', ARRAY[]::TEXT[], ARRAY[]::TEXT[], ARRAY[]::TEXT[], '', '', ARRAY[]::TEXT[])
            RETURNING user_id;
            """
        )
        user_id = new_user["user_id"]
        await conn.execute(
            "INSERT INTO login (user_id, username, password) VALUES ($1, $2, $3)",
            user_id, signup_data.username, signup_data.password
        )
        return {"message": "Signup successful!", "user_id": user_id}

@app.post("/register/preferences/")
async def register_preferences(user_id: int, preferences: PreferencesData, db=Depends(get_db_connection)):
    async with db.acquire() as conn:
        user_exists = await conn.fetchrow("SELECT * FROM users WHERE user_id=$1", user_id)
        if not user_exists:
            raise HTTPException(status_code=404, detail="User not found. Please sign up first.")
        
        await conn.execute(
            """
            UPDATE users
            SET name=$1, age=$2, study_level=$3, preferred_subjects=$4, strengths=$5, weaknesses=$6, learning_style=$7, study_preference=$8, availability=$9
            WHERE user_id=$10;
            """,
            preferences.name, preferences.age, preferences.study_level,
            preferences.preferred_subjects, preferences.strengths,
            preferences.weaknesses, preferences.learning_style,
            preferences.study_preference, preferences.availability,
            user_id
        )

    # ✅ Ensure Preprocessing Completes First
    try:
        preprocess = await asyncio.create_subprocess_exec("python", "preprocessing.py")
        await preprocess.wait()  # 🔹 Wait for preprocessing to finish

        similarity = await asyncio.create_subprocess_exec("python", "similarity.py")
        await similarity.wait()  # 🔹 Only then run similarity

        print("✅ Preprocessing and similarity scripts executed successfully!")
    except Exception as e:
        print("❌ Error running scripts:", e)

    return {"message": "User preferences updated and recommendations generated!"}

@app.post("/login/")
async def login(login_data: LoginData, db=Depends(get_db_connection)):
    async with db.acquire() as conn:
        user = await conn.fetchrow("SELECT user_id FROM login WHERE username=$1 AND password=$2", login_data.username, login_data.password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        session_token = str(uuid.uuid4())
        active_sessions[session_token] = user["user_id"]
        return {"message": "Login successful", "session_token": session_token, "user_id": user["user_id"]}

@app.post("/logout/")
def logout(session_token: str):
    if session_token in active_sessions:
        del active_sessions[session_token]
        return {"message": "Logout successful"}
    raise HTTPException(status_code=401, detail="Invalid session token")

@app.get("/users/")
async def get_all_users(db=Depends(get_db_connection)):
    async with db.acquire() as conn:
        users = await conn.fetch("SELECT * FROM users")
    users_list = [{
        "user_id": user["user_id"],
        "name": user["name"],
        "age": user["age"],
        "study_level": user["study_level"],
        "preferred_subjects": user["preferred_subjects"],
        "strengths": user["strengths"],
        "weaknesses": user["weaknesses"],
        "learning_style": user["learning_style"],
        "study_preference": user["study_preference"],
        "availability": user["availability"]
    } for user in users]
    return {"users": users_list}

@app.get("/users/search/")
async def search_users(skill: str = Query(...), db=Depends(get_db_connection)):
    async with db.acquire() as conn:
        users = await conn.fetch("SELECT * FROM users WHERE $1 = ANY(preferred_subjects) OR $1 = ANY(strengths)", skill)
    if not users:
        return {"message": "No users found with this skill"}
    users_list = [{
        "user_id": user["user_id"],
        "name": user["name"],
        "age": user["age"],
        "study_level": user["study_level"],
        "preferred_subjects": user["preferred_subjects"],
        "strengths": user["strengths"],
        "weaknesses": user["weaknesses"],
        "learning_style": user["learning_style"],
        "study_preference": user["study_preference"],
        "availability": user["availability"]
    } for user in users]
    return {"users": users_list}

@app.get("/user/me/")
async def get_current_user_data(authorization: str = Header(...), db=Depends(get_db_connection)):
    session_token = authorization.split(" ")[1]  # Extract token from "Bearer <token>"
    user_id = active_sessions.get(session_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid session token")

    async with db.acquire() as conn:
        user_data = await conn.fetchrow("SELECT * FROM users WHERE user_id=$1", user_id)
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")

    return {
        "user_id": user_data["user_id"],
        "name": user_data["name"],
        "age": user_data["age"],
        "study_level": user_data["study_level"],
        "preferred_subjects": user_data["preferred_subjects"],
        "strengths": user_data["strengths"],
        "weaknesses": user_data["weaknesses"],
        "learning_style": user_data["learning_style"],
        "study_preference": user_data["study_preference"],
        "availability": user_data["availability"]
    }

# 📌 Get Study Partner Recommendations
@app.get("/recommend/{user_id}")
async def get_recommendations(user_id: int, db=Depends(get_db_connection)):
    async with db.acquire() as conn:
        # Check if user exists
        user_data = await conn.fetchrow("SELECT * FROM users WHERE user_id=$1", user_id)
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")

        # Fetch recommendations
        recommendations = await conn.fetchrow("SELECT recommendations FROM recommended WHERE user_id=$1", user_id)
        if not recommendations:
            return {"user_id": user_id, "recommended_partners": []}

        recommended_ids = recommendations["recommendations"]

        # Fetch details of recommended users
        recommended_users = await conn.fetch("SELECT * FROM users WHERE user_id = ANY($1::int[])", recommended_ids)

    return {"user": user_data, "recommended_partners": recommended_users}