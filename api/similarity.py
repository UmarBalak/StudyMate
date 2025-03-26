
import pandas as pd
import numpy as np
import json
import logging
from datetime import datetime
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
from scipy.stats import pearsonr
from db import connect_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('similarity_advanced.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def compute_multi_dimensional_similarity(features, feature_columns):
    """
    Compute similarity using multiple dimensions and weighted strategies
    
    Args:
        features (pd.DataFrame): Processed user features
        feature_columns (list): Columns to use for similarity computation
    
    Returns:
        np.ndarray: Multi-dimensional similarity matrix
    """
    # Subject interest similarity
    preferred_cols = [col for col in feature_columns if col.startswith('preferred_')]
    strength_cols = [col for col in feature_columns if col.startswith('strength_')]
    weak_cols = [col for col in feature_columns if col.startswith('weak_')]
    
    # Compute individual similarity matrices
    preferred_sim = cosine_similarity(features[preferred_cols])
    strength_sim = cosine_similarity(features[strength_cols])
    weak_sim = cosine_similarity(features[weak_cols])
    
    # Compute demographic and learning style similarity
    # Dynamically collect demographic + categorical columns
    demographic_cols = ['age']
    demographic_cols += [col for col in features.columns if col.startswith('learning_style_')]
    demographic_cols += [col for col in features.columns if col.startswith('study_preference_')]
    demographic_cols += [col for col in features.columns if col.startswith('study_level_')]

    numeric_scaler = StandardScaler()
    scaled_numeric = numeric_scaler.fit_transform(features[demographic_cols])

    demographic_sim = 1 - np.abs(cosine_similarity(scaled_numeric) - 1)
    
    # Weighted combination of similarity matrices
    weights = {
        'preferred_weight': 0.3,   # Subject interests
        'strength_weight': 0.7,   # Technical strengths
        'weak_weight': 0.0,       # Complementary weaknesses
        'demographic_weight': 0.0  # Learning style & demographics
    }
    
    multi_sim = (
        weights['preferred_weight'] * preferred_sim +
        weights['strength_weight'] * strength_sim
    )
    # multi_sim = (
    #     weights['preferred_weight'] * preferred_sim +
    #     weights['strength_weight'] * strength_sim +
    #     weights['weak_weight'] * weak_sim +
    #     weights['demographic_weight'] * demographic_sim
    # )
    
    return multi_sim

def advanced_recommendation_strategy(similarity_matrix, features, top_k=5):
    """
    Generate advanced recommendations considering multiple factors
    
    Args:
        similarity_matrix (np.ndarray): Computed similarity matrix
        features (pd.DataFrame): User features dataframe
        top_k (int): Number of recommendations to generate
    
    Returns:
        dict: User-specific recommendations
    """
    recommendations = {}
    
    for idx, row in features.iterrows():
        # Find similar users
        similar_indices = similarity_matrix[idx].argsort()[::-1][1:top_k+1]
        
        # Score recommendations based on multiple criteria
        rec_scores = {}
        for rec_idx in similar_indices:
            user_id = int(features.iloc[rec_idx]["user_id"])
            rec_score = similarity_matrix[idx][rec_idx]
            
            # Additional scoring factors
            interests_overlap = np.dot(
                features.iloc[idx][features.columns.str.startswith('preferred_')],
                features.iloc[rec_idx][features.columns.str.startswith('preferred_')]
            )
            
            # Complementary weakness calculation
            # Align vectors for consistent shape
            weak_cols = [col for col in features.columns if col.startswith('weak_')]
            strength_cols = [col for col in features.columns if col.startswith('strength_')]
            weak_vector = features.loc[idx, weak_cols].values
            strength_vector = features.loc[rec_idx, strength_cols].values
            min_len = min(len(weak_vector), len(strength_vector))
            weak_vector = weak_vector[:min_len]
            strength_vector = strength_vector[:min_len]
            complementary_weakness_score = 1 - np.abs(np.dot(weak_vector, strength_vector))
            
            # Final recommendation score
            final_score = (
                0.7 * rec_score + 
                0.3 * interests_overlap
            )
            # final_score = (
            #     0. * rec_score + 
            #     0.3 * interests_overlap + 
            #     0.2 * complementary_weakness_score
            # )
            
            rec_scores[user_id] = final_score
        
        # Sort recommendations by score
        recommendations[row["user_id"]] = sorted(
            rec_scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:top_k]
    
    return {k: [rec[0] for rec in reversed(v)] for k, v in recommendations.items()}


def main():
    """Advanced recommendation workflow"""
    try:
        logger.info("Starting advanced similarity computation workflow")
        start_time = datetime.now()
        
        conn = connect_db()
        if not conn:
            logger.critical("FATAL: Database connection failed")
            raise ConnectionError("Database connection failed")
            
        cursor = conn.cursor()
        logger.info("Database connection established")

        # Data loading and processing (similar to previous implementation)
        df = pd.read_sql("SELECT user_id, encoded_features FROM preprocessed", conn)
        df["encoded_features"] = df["encoded_features"].apply(
            lambda x: json.loads(x) if isinstance(x, str) else x
        )
        
        features = pd.json_normalize(df["encoded_features"])
        features.insert(0, "user_id", df["user_id"])
        
        feature_columns = features.columns.difference(["user_id"])
        features[feature_columns] = features[feature_columns].apply(
            pd.to_numeric, errors="coerce"
        ).fillna(0)
        
        # Advanced similarity computation
        multi_similarity_matrix = compute_multi_dimensional_similarity(
            features, feature_columns
        )
        
        # Advanced recommendation generation
        recommendations = advanced_recommendation_strategy(
            multi_similarity_matrix, features
        )
        
        # Database storage of recommendations
        cursor.execute("DELETE FROM recommended")
        logger.debug("Cleared previous recommendations")
        
        for user_id, recs in recommendations.items():
            postgres_array = "{" + ",".join(map(str, recs)) + "}"
            cursor.execute(
                "INSERT INTO recommended (user_id, recommendations) VALUES (%s, %s)",
                (user_id, postgres_array)
            )
        
        conn.commit()
        logger.info(f"Successfully stored {len(recommendations)} advanced recommendations")

    except Exception as e:
        logger.critical(f"Advanced recommendation workflow failed: {str(e)}")
        raise
    finally:
        try:
            cursor.close()
            conn.close()
        except Exception as e:
            logger.warning(f"Cleanup warning: {str(e)}")
        
        duration = datetime.now() - start_time
        logger.info(f"Total advanced recommendation time: {duration.total_seconds():.2f} seconds")

if __name__ == "__main__":
    try:
        main()
        logger.info("Advanced recommendations complete!")
    except Exception as e:
        logger.critical("Advanced recommendation workflow failed", exc_info=True)
        exit(1)