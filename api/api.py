from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import uuid
from db import connect_db
import subprocess

app = FastAPI()

# Allow all origins for now (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# 📌 In-memory session storage (temporary)
active_sessions = {}

# 📌 User Models
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

# 📌 User Sign-Up (Account Creation)
@app.post("/signup/")
def signup(signup_data: SignUpData):
    conn = connect_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = conn.cursor()

    # 🔹 Check if username is already taken
    cursor.execute("SELECT user_id FROM login WHERE username = %s", (signup_data.username,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Username already exists")

    # 🔹 Insert user into `users` first to generate `user_id`
    query_users = """
    INSERT INTO users (name, age, study_level, preferred_subjects, strengths, weaknesses, learning_style, study_preference, availability)
    VALUES ('', 0, '', ARRAY[]::TEXT[], ARRAY[]::TEXT[], ARRAY[]::TEXT[], '', '', ARRAY[]::TEXT[])
    RETURNING user_id;
    """
    cursor.execute(query_users)
    new_user_id = cursor.fetchone()[0]  # Get the generated `user_id`

    # 🔹 Now insert into `login` with the same `user_id`
    query_login = """
    INSERT INTO login (user_id, username, password) VALUES (%s, %s, %s);
    """
    cursor.execute(query_login, (new_user_id, signup_data.username, signup_data.password))

    conn.commit()
    cursor.close()
    conn.close()

    return {"message": "Signup successful! Please update your profile.", "user_id": new_user_id}

# 📌 Register User Preferences (After Signup)
@app.post("/register/preferences/")
def register_preferences(user_id: int, preferences: PreferencesData):
    conn = connect_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = conn.cursor()

    # 🔹 Check if user exists in `users`
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="User not found. Please sign up first.")

    # 🔹 Update existing user preferences
    query_user = """
    UPDATE users
    SET name = %s, age = %s, study_level = %s, preferred_subjects = %s,
        strengths = %s, weaknesses = %s, learning_style = %s, 
        study_preference = %s, availability = %s
    WHERE user_id = %s;
    """
    cursor.execute(query_user, (
        preferences.name, preferences.age, preferences.study_level,
        preferences.preferred_subjects, preferences.strengths,
        preferences.weaknesses, preferences.learning_style,
        preferences.study_preference, preferences.availability,
        user_id  # 🔹 Ensure update is based on the correct user_id
    ))

    conn.commit()
    cursor.close()
    conn.close()

    
    # Run preprocessing and similarity scripts
    subprocess.run(["python", "e:/StudyMate/api/preprocessing.py"])
    subprocess.run(["python", "e:/StudyMate/api/similarity.py"])


    return {"message": "User preferences updated successfully!"}

# 📌 User Login
@app.post("/login/")
def login(login_data: LoginData):
    conn = connect_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = conn.cursor()

    # 🔹 Check if username & password match
    query = "SELECT user_id FROM login WHERE username = %s AND password = %s"
    cursor.execute(query, (login_data.username, login_data.password))
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # 🔹 Generate session token
    session_token = str(uuid.uuid4())
    active_sessions[session_token] = user[0]  # Store user_id in session

    return {"message": "Login successful", "session_token": session_token}

# 📌 User Logout
@app.post("/logout/")
def logout(session_token: str):
    if session_token in active_sessions:
        del active_sessions[session_token]
        return {"message": "Logout successful"}
    
    raise HTTPException(status_code=401, detail="Invalid session token")

# 📌 Fetch All Users
@app.get("/users/")
def get_all_users():
    conn = connect_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    cursor.close()
    conn.close()

    users_list = [
        {
            "user_id": user[0],
            "name": user[1],
            "age": user[2],
            "study_level": user[3],
            "preferred_subjects": user[4],
            "strengths": user[5],
            "weaknesses": user[6],
            "learning_style": user[7],
            "study_preference": user[8],
            "availability": user[9]
        }
        for user in users
    ]
    
    return {"users": users_list}

# 📌 Search Users by Skills (Preferred Subjects & Strengths)
@app.get("/users/search/")
def search_users(skill: str = Query(..., description="Skill to search for (subject or strength)")):
    conn = connect_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = conn.cursor()
    query = """
    SELECT * FROM users 
    WHERE %s = ANY(preferred_subjects) OR %s = ANY(strengths)
    """
    cursor.execute(query, (skill, skill))
    users = cursor.fetchall()
    cursor.close()
    conn.close()

    if not users:
        return {"message": "No users found with this skill"}

    users_list = [
        {
            "user_id": user[0],
            "name": user[1],
            "age": user[2],
            "study_level": user[3],
            "preferred_subjects": user[4],
            "strengths": user[5],
            "weaknesses": user[6],
            "learning_style": user[7],
            "study_preference": user[8],
            "availability": user[9]
        }
        for user in users
    ]
    
    return {"users": users_list}

# 📌 Get Study Partner Recommendations
@app.get("/recommend/{user_id}")
def get_recommendations(user_id: int):
    conn = connect_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = conn.cursor()

    # Check if user exists
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    user_data = cursor.fetchone()
    
    if not user_data:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")

    # Fetch recommendations
    cursor.execute("SELECT recommendations FROM recommended WHERE user_id = %s", (user_id,))
    recommendations = cursor.fetchone()
    
    if not recommendations:
        cursor.close()
        conn.close()
        return {"user_id": user_id, "recommended_partners": []}

    recommended_ids = recommendations[0]

    # Fetch details of recommended users
    cursor.execute("SELECT * FROM users WHERE user_id = ANY(%s)", (recommended_ids,))
    recommended_users = cursor.fetchall()

    cursor.close()
    conn.close()

    return {"user": user_data, "recommended_partners": recommended_users}
