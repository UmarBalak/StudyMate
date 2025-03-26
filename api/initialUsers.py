import pandas as pd
from db import connect_db  # Import database connection
import ast

# Load extracted 40 users
df = pd.read_csv("users_30.csv")

# Convert list-like columns to PostgreSQL-friendly format
def list_to_pg_array(value):
    if isinstance(value, str):  
        try:
            parsed_list = ast.literal_eval(value)  # Convert string to list safely
            if isinstance(parsed_list, list):
                return "{" + ",".join(parsed_list) + "}"  # Convert to PostgreSQL array format
        except:
            return "{}"  # If conversion fails, return an empty array
    return "{}"  # If value is not a string or list, return an empty array

# Insert users into NeonDB
def insert_users():
    conn = connect_db()  # Get the database connection
    if not conn:
        print("❌ Database connection failed.")
        return

    try:
        with conn.cursor() as cursor:  # Use the cursor to execute queries
            for _, row in df.iterrows():
                query = """
                INSERT INTO users (name, age, study_level, preferred_subjects, strengths, weaknesses, learning_style, study_preference, availability)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(query, (
                    row["name"], row["age"], row["study_level"],
                    list_to_pg_array(row["preferred_subjects"]),
                    list_to_pg_array(row["strengths"]),
                    list_to_pg_array(row["weaknesses"]),
                    row["learning_style"], row["study_preference"],
                    list_to_pg_array(row["availability"])
                ))
            conn.commit()  # Commit the transaction
            print("✅ 30 users inserted into NeonDB!")
    except Exception as e:
        print(f"❌ Error inserting users: {e}")
    finally:
        conn.close()  # Close the connection

# Run the function
insert_users()