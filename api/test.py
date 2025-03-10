import pandas as pd

# Load the existing dataset
df = pd.read_csv("users.csv")

# Extract a balanced 40-user subset
beginners = df[df["study_level"] == "Beginner"].sample(10, random_state=42)
intermediates = df[df["study_level"] == "Intermediate"].sample(15, random_state=42)
advanced = df[df["study_level"] == "Advanced"].sample(15, random_state=42)

# Combine into a final dataset
df_selected = pd.concat([beginners, intermediates, advanced])

# Save the extracted dataset (for verification)
df_selected.to_csv("users_40.csv", index=False)

print("✅ Extracted 40 users and saved as 'users_40.csv'")
