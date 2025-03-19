import pandas as pd
import numpy as np
import json
import logging
from datetime import datetime
from sklearn.metrics.pairwise import cosine_similarity
from db import connect_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('similarity.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Main execution flow with comprehensive logging"""
    try:
        # Database connection
        logger.info("🟢 Starting similarity computation workflow")
        start_time = datetime.now()
        
        logger.debug("Initializing database connection")
        conn = connect_db()
        if not conn:
            logger.critical("🔴 FATAL: Database connection failed")
            raise ConnectionError("Database connection failed")
            
        cursor = conn.cursor()
        logger.info("✅ Database connection established")

        # Data loading
        try:
            logger.info("📥 Fetching preprocessed data from NeonDB")
            df = pd.read_sql("SELECT user_id, encoded_features FROM preprocessed", conn)
            logger.info(f"📊 Loaded {len(df)} records from database")
        except Exception as e:
            logger.error(f"❌ Data loading failed: {str(e)}")
            raise

        # Feature processing
        try:
            logger.debug("Processing encoded features")
            df["encoded_features"] = df["encoded_features"].apply(
                lambda x: json.loads(x) if isinstance(x, str) else x
            )
            
            features = pd.json_normalize(df["encoded_features"])
            features.insert(0, "user_id", df["user_id"])
            
            feature_columns = features.columns.difference(["user_id"])
            features[feature_columns] = features[feature_columns].apply(
                pd.to_numeric, errors="coerce"
            ).fillna(0)
            
            logger.info(f"🔧 Processed {len(feature_columns)} features for {len(features)} users")
            logger.debug(f"Feature columns: {feature_columns.tolist()}")
        except Exception as e:
            logger.error(f"❌ Feature processing failed: {str(e)}")
            raise

        # Similarity computation
        try:
            logger.info("🧮 Computing cosine similarities")
            similarity_matrix = cosine_similarity(features[feature_columns])
            logger.debug(f"Computed similarity matrix of shape {similarity_matrix.shape}")
        except Exception as e:
            logger.error(f"❌ Similarity computation failed: {str(e)}")
            raise

        # Recommendation generation
        try:
            logger.info("📈 Generating recommendations")
            recommendations = {}
            for idx, row in features.iterrows():
                similar_indices = similarity_matrix[idx].argsort()[-4:-1][::-1]
                recommendations[row["user_id"]] = [
                    int(features.iloc[i]["user_id"]) for i in similar_indices
                ]
            
            logger.info(f"🎯 Generated recommendations for {len(recommendations)} users")
            logger.debug(f"Sample recommendations: {list(recommendations.items())[:3]}")
        except Exception as e:
            logger.error(f"❌ Recommendation generation failed: {str(e)}")
            raise

        # Database storage
        try:
            logger.info("💾 Storing recommendations in NeonDB")
            cursor.execute("DELETE FROM recommended")
            logger.debug("Cleared previous recommendations")
            
            for user_id, recs in recommendations.items():
                postgres_array = "{" + ",".join(map(str, recs)) + "}"
                cursor.execute(
                    "INSERT INTO recommended (user_id, recommendations) VALUES (%s, %s)",
                    (user_id, postgres_array)
                )
            
            conn.commit()
            logger.info(f"📥 Successfully stored {len(recommendations)} recommendations")
            logger.debug(f"Sample stored entry: {list(recommendations.items())[0]}")
        except Exception as e:
            logger.error(f"❌ Database storage failed: {str(e)}")
            conn.rollback()
            raise

    except Exception as e:
        logger.critical(f"🔴 Critical failure: {str(e)}")
        raise
    finally:
        try:
            cursor.close()
            conn.close()
            logger.info("🔌 Database connection closed")
        except Exception as e:
            logger.warning(f"⚠️ Cleanup warning: {str(e)}")
        
        duration = datetime.now() - start_time
        logger.info(f"⏱ Total execution time: {duration.total_seconds():.2f} seconds")

if __name__ == "__main__":
    try:
        main()
        logger.info("✅ Recommendations complete! NeonDB updated successfully")
    except Exception as e:
        logger.critical("🔴 Recommendation workflow failed", exc_info=True)
        exit(1)
