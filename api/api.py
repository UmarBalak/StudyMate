from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import psycopg2
from db import connect_db

app = FastAPI()

# 📌 User Model
class User(BaseModel):
    name: str
    age: int
    study_level: str
    preferred_subjects: list[str]
    strengths: list[str]
    weaknesses: list[str]
    learning_style: str
    study_preference: str
    availability: list[str]


@app.get("/")
def read_root():
    return {"message": "Welcome to Study Partner Recommendation API!"}

# 📌 Register a New User
@app.post("/register/")
def register_user(user: User):
    conn = connect_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = conn.cursor()
    query = """
    INSERT INTO users (name, age, study_level, preferred_subjects, strengths, weaknesses, learning_style, study_preference, availability)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING user_id;
    """
    cursor.execute(query, (
        user.name, user.age, user.study_level,
        user.preferred_subjects, user.strengths,
        user.weaknesses, user.learning_style,
        user.study_preference, user.availability
    ))

    new_user_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()

    return {"message": "User registered successfully!", "user_id": new_user_id}

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

    # Convert results to dictionary
    user_dict = {
        "user_id": user_data[0],
        "name": user_data[1],
        "age": user_data[2],
        "study_level": user_data[3],
        "preferred_subjects": user_data[4],
        "strengths": user_data[5],
        "weaknesses": user_data[6],
        "learning_style": user_data[7],
        "study_preference": user_data[8],
        "availability": user_data[9]
    }

    recommended_users_list = [
        {
            "user_id": rec[0],
            "name": rec[1],
            "age": rec[2],
            "study_level": rec[3],
            "preferred_subjects": rec[4],
            "strengths": rec[5],
            "weaknesses": rec[6],
            "learning_style": rec[7],
            "study_preference": rec[8],
            "availability": rec[9]
        }
        for rec in recommended_users
    ]
    
    return {
        "user": user_dict,
        "recommended_partners": recommended_users_list
    }
