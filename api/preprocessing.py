import pandas as pd
import numpy as np
import json
import logging
from datetime import datetime
from sklearn.preprocessing import OneHotEncoder, MinMaxScaler
from db import connect_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('preprocessing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Main preprocessing workflow with comprehensive logging"""
    try:
        logger.info("🟢 Starting data preprocessing workflow")
        start_time = datetime.now()
        conn = None
        cursor = None

        # Database connection
        try:
            logger.debug("Initializing database connection")
            conn = connect_db()
            if not conn:
                logger.critical("🔴 FATAL: Database connection failed")
                raise ConnectionError("Database connection failed")
            cursor = conn.cursor()
            logger.info("✅ Database connection established")
        except Exception as e:
            logger.error(f"❌ Connection initialization failed: {str(e)}")
            raise

        # Data loading
        try:
            logger.info("📥 Fetching raw user data from NeonDB")
            df = pd.read_sql("SELECT * FROM users", conn)
            logger.info(f"📊 Loaded {len(df)} raw user records")
            logger.debug(f"Sample raw data:\n{df.head(2).to_string()}")
        except Exception as e:
            logger.error(f"❌ Data loading failed: {str(e)}")
            raise

        # Feature engineering
        try:
            logger.info("🔧 Processing categorical features")
            categorical_cols = ["learning_style", "study_preference", "study_level"]
            original_cols = df.columns.tolist()
            
            df = pd.get_dummies(df, columns=categorical_cols, drop_first=True)
            new_cols = list(set(df.columns) - set(original_cols))
            logger.info(f"➕ Added {len(new_cols)} one-hot encoded columns: {new_cols}")
        except Exception as e:
            logger.error(f"❌ Categorical encoding failed: {str(e)}")
            raise

        # Numerical normalization
        try:
            logger.info("📏 Normalizing numerical features")
            scaler = MinMaxScaler()
            df["age"] = scaler.fit_transform(df[["age"]])
            logger.debug(f"Age statistics after scaling:\n{df['age'].describe()}")
        except Exception as e:
            logger.error(f"❌ Feature scaling failed: {str(e)}")
            raise

        # JSON conversion
        try:
            logger.info("🔄 Converting features to JSON format")
            df["encoded_features"] = df.drop(columns=["user_id", "name"]).apply(
                lambda x: x.to_dict(), axis=1
            )
            logger.debug(f"Sample JSON encoding:\n{df['encoded_features'].iloc[0]}")
        except Exception as e:
            logger.error(f"❌ JSON conversion failed: {str(e)}")
            raise

        # Database operations
        try:
            logger.info("💾 Storing processed data in NeonDB")
            cursor.execute("DELETE FROM preprocessed")
            logger.debug("🧹 Cleared previous preprocessed data")
            
            inserted_count = 0
            for _, row in df.iterrows():
                cursor.execute(
                    "INSERT INTO preprocessed (user_id, encoded_features) VALUES (%s, %s)",
                    (row["user_id"], json.dumps(row["encoded_features"]))
                )
                inserted_count += 1
                
            conn.commit()
            logger.info(f"📥 Successfully stored {inserted_count} processed records")
            logger.debug(f"Sample stored entry: {df.iloc[0]['encoded_features']}")
        except Exception as e:
            logger.error(f"❌ Database storage failed: {str(e)}")
            conn.rollback()
            raise

    except Exception as e:
        logger.critical(f"🔴 Critical preprocessing failure: {str(e)}")
        raise
    finally:
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            logger.info("🔌 Database connection closed")
        except Exception as e:
            logger.warning(f"⚠️ Cleanup warning: {str(e)}")
        
        duration = datetime.now() - start_time
        logger.info(f"⏱ Total preprocessing time: {duration.total_seconds():.2f} seconds")

if __name__ == "__main__":
    try:
        main()
        logger.info("✅ Preprocessing complete! Data stored in NeonDB")
    except Exception as e:
        logger.critical("🔴 Preprocessing workflow failed", exc_info=True)
        exit(1)
