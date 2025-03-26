import pandas as pd
import ast

# Load the CSV file
file_path = "users.csv"
df = pd.read_csv(file_path)

# Columns that contain lists stored as strings
list_columns = ["preferred_subjects", "strengths", "weaknesses", "availability"]

# Function to safely convert string lists into actual lists
def safe_eval(value):
    try:
        if isinstance(value, str) and value.startswith("[") and value.endswith("]"):
            return ast.literal_eval(value)  # Convert only if it's a valid list
    except (ValueError, SyntaxError):
        pass  # Ignore errors and return an empty list
    return []

# Apply safe_eval to list-like columns
for col in list_columns:
    df[col] = df[col].apply(safe_eval)

# Extract unique values from each relevant column
unique_values = {
    "study_levels": sorted(df["study_level"].dropna().unique()),
    "preferred_subjects": sorted(set(item for sublist in df["preferred_subjects"] for item in sublist)),
    "learning_styles": sorted(df["learning_style"].dropna().unique()),
    "study_preferences": sorted(df["study_preference"].dropna().unique()),
    "availability_options": sorted(set(item for sublist in df["availability"] for item in sublist)),
}

# Return the extracted values
print(unique_values)
