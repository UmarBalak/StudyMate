from db import connect_db

def create_tables():
    conn = connect_db()
    if not conn:
        print("❌ Database connection failed.")
        return

    cursor = conn.cursor()

    # SQL statements to create tables
    create_users_table = """
    CREATE TABLE IF NOT EXISTS users (
        user_id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        age INT NOT NULL,
        study_level TEXT NOT NULL,
        preferred_subjects TEXT[],
        strengths TEXT[],
        weaknesses TEXT[],
        learning_style TEXT NOT NULL,
        study_preference TEXT NOT NULL,
        availability TEXT[]
    );
    """

    create_recommended_table = """
    CREATE TABLE IF NOT EXISTS recommended (
        user_id INT PRIMARY KEY REFERENCES users(user_id),
        recommendations INT[] NOT NULL
    );
    """

    create_preprocessed_table = """
    CREATE TABLE IF NOT EXISTS preprocessed (
        user_id INT PRIMARY KEY REFERENCES users(user_id),
        encoded_features JSONB NOT NULL
    );
    """

    create_login_table = """
    CREATE TABLE IF NOT EXISTS login (
        user_id INT PRIMARY KEY REFERENCES users(user_id),
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL  -- Storing as plaintext for now
    );
    """

    # Execute queries
    cursor.execute(create_users_table)
    cursor.execute(create_recommended_table)
    cursor.execute(create_preprocessed_table)
    cursor.execute(create_login_table)

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Tables created (if not already exist)")

# Run table creation
create_tables()
