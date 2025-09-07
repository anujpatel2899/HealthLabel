# [file name]: history_manager.py
"""
History management module for food analysis records.
Uses SQLite for local storage with full CRUD operations.
"""

import sqlite3
import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HistoryManager:
    """Manages analysis history using SQLite database"""
    
    def __init__(self, db_path: str = "food_analysis_history.db"):
        self.db_path = Path(db_path)
        self.init_database()
    
    def init_database(self):
        """Initialize the SQLite database with required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Main analysis records table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS analysis_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        product_name TEXT NOT NULL,
                        brand TEXT,
                        barcode TEXT,
                        health_score INTEGER,
                        health_band TEXT,
                        summary TEXT,
                        analysis_result TEXT,
                        analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # User notes and tags table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS product_notes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        analysis_id INTEGER,
                        note TEXT,
                        tags TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (analysis_id) REFERENCES analysis_history (id)
                    )
                """)
                
                # Search cache table for performance
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS search_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        search_term TEXT UNIQUE,
                        results TEXT,
                        cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes for better performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_product_name ON analysis_history(product_name)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_brand ON analysis_history(brand)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_barcode ON analysis_history(barcode)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_analyzed_at ON analysis_history(analyzed_at)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_health_score ON analysis_history(health_score)")
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except sqlite3.Error as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def save_analysis(
        self,
        product_name: str,
        brand: str = "",
        barcode: str = "",
        health_score: int = 0,
        health_band: str = "Unknown",
        summary: str = "",
        analysis_result: str = ""
    ) -> int:
        """Save analysis result to history"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if this product already exists (by barcode if available, otherwise by name+brand)
                if barcode:
                    cursor.execute(
                        "SELECT id FROM analysis_history WHERE barcode = ? AND barcode != ''",
                        (barcode,)
                    )
                else:
                    cursor.execute(
                        "SELECT id FROM analysis_history WHERE product_name = ? AND brand = ?",
                        (product_name, brand)
                    )
                
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing record
                    cursor.execute("""
                        UPDATE analysis_history 
                        SET health_score = ?, health_band = ?, summary = ?, 
                            analysis_result = ?, analyzed_at = CURRENT_TIMESTAMP,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (health_score, health_band, summary, analysis_result, existing[0]))
                    
                    analysis_id = existing[0]
                    logger.info(f"Updated existing analysis for {product_name}")
                else:
                    # Insert new record
                    cursor.execute("""
                        INSERT INTO analysis_history 
                        (product_name, brand, barcode, health_score, health_band, summary, analysis_result)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (product_name, brand, barcode, health_score, health_band, summary, analysis_result))
                    
                    analysis_id = cursor.lastrowid
                    logger.info(f"Saved new analysis for {product_name}")
                
                conn.commit()
                return analysis_id
                
        except sqlite3.Error as e:
            logger.error(f"Failed to save analysis: {e}")
            raise
    
    def get_history_dataframe(self, limit: int = 100) -> pd.DataFrame:
        """Get analysis history as pandas DataFrame"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = """
                    SELECT id, product_name, brand, barcode, health_score, health_band, 
                           summary, analysis_result, analyzed_at, created_at
                    FROM analysis_history 
                    ORDER BY analyzed_at DESC 
                    LIMIT ?
                """
                
                df = pd.read_sql_query(query, conn, params=(limit,))
                
                # Convert timestamp columns
                timestamp_cols = ['analyzed_at', 'created_at']
                for col in timestamp_cols:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col])
                
                return df
                
        except Exception as e:
            logger.error(f"Failed to get history DataFrame: {e}")
            return pd.DataFrame()
    
    def get_recent_products(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recently analyzed products"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, product_name, brand, health_score, health_band, 
                           analysis_result, analyzed_at
                    FROM analysis_history 
                    ORDER BY analyzed_at DESC 
                    LIMIT ?
                """, (limit,))
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'id': row[0],
                        'product_name': row[1],
                        'brand': row[2],
                        'health_score': row[3],
                        'health_band': row[4],
                        'analysis_result': row[5],
                        'analyzed_at': row[6]
                    })
                
                return results
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get recent products: {e}")
            return []
    
    def search_history(
        self, 
        search_term: str = "", 
        min_score: int = 0, 
        date_from: Optional[datetime] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search analysis history with filters"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Build dynamic query
                conditions = ["1=1"]  # Always true condition to simplify building
                params = []
                
                if search_term:
                    conditions.append("(product_name LIKE ? OR brand LIKE ?)")
                    search_pattern = f"%{search_term}%"
                    params.extend([search_pattern, search_pattern])
                
                if min_score > 0:
                    conditions.append("health_score >= ?")
                    params.append(min_score)
                
                if date_from:
                    conditions.append("analyzed_at >= ?")
                    params.append(date_from.isoformat())
                
                query = f"""
                    SELECT id, product_name, brand, barcode, health_score, health_band,
                           summary, analysis_result, analyzed_at
                    FROM analysis_history 
                    WHERE {' AND '.join(conditions)}
                    ORDER BY analyzed_at DESC 
                    LIMIT ?
                """
                params.append(limit)
                
                cursor.execute(query, params)
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'id': row[0],
                        'product_name': row[1],
                        'brand': row[2],
                        'barcode': row[3],
                        'health_score': row[4],
                        'health_band': row[5],
                        'summary': row[6],
                        'analysis_result': row[7],
                        'analyzed_at': row[8]
                    })
                
                return results
                
        except sqlite3.Error as e:
            logger.error(f"History search failed: {e}")
            return []
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics of analysis history"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total products
                cursor.execute("SELECT COUNT(*) FROM analysis_history")
                total_products = cursor.fetchone()[0]
                
                # Average health score
                cursor.execute("SELECT AVG(health_score) FROM analysis_history WHERE health_score > 0")
                avg_score_result = cursor.fetchone()[0]
                avg_score = round(avg_score_result, 1) if avg_score_result else 0
                
                # Products analyzed this week
                week_ago = (datetime.now() - timedelta(days=7)).isoformat()
                cursor.execute(
                    "SELECT COUNT(*) FROM analysis_history WHERE analyzed_at >= ?", 
                    (week_ago,)
                )
                products_this_week = cursor.fetchone()[0]
                
                # Health band distribution
                cursor.execute("""
                    SELECT health_band, COUNT(*) 
                    FROM analysis_history 
                    GROUP BY health_band
                """)
                band_distribution = dict(cursor.fetchall())
                
                # Most analyzed brands
                cursor.execute("""
                    SELECT brand, COUNT(*) as count
                    FROM analysis_history 
                    WHERE brand != '' 
                    GROUP BY brand 
                    ORDER BY count DESC 
                    LIMIT 5
                """)
                top_brands = cursor.fetchall()
                
                return {
                    'total_products': total_products,
                    'avg_score': avg_score,
                    'products_this_week': products_this_week,
                    'band_distribution': band_distribution,
                    'top_brands': top_brands
                }
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get summary stats: {e}")
            return {
                'total_products': 0,
                'avg_score': 0,
                'products_this_week': 0,
                'band_distribution': {},
                'top_brands': []
            }
    
    def add_product_note(self, analysis_id: int, note: str, tags: str = "") -> bool:
        """Add a note/tag to an analysis record"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO product_notes (analysis_id, note, tags)
                    VALUES (?, ?, ?)
                """, (analysis_id, note, tags))
                
                conn.commit()
                logger.info(f"Added note to analysis {analysis_id}")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Failed to add note: {e}")
            return False
    
    def get_product_notes(self, analysis_id: int) -> List[Dict[str, Any]]:
        """Get notes for a specific analysis"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, note, tags, created_at
                    FROM product_notes 
                    WHERE analysis_id = ?
                    ORDER BY created_at DESC
                """, (analysis_id,))
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'id': row[0],
                        'note': row[1],
                        'tags': row[2],
                        'created_at': row[3]
                    })
                
                return results
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get notes: {e}")
            return []
    
    def delete_analysis(self, analysis_id: int) -> bool:
        """Delete an analysis record and its notes"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Delete notes first (foreign key constraint)
                cursor.execute("DELETE FROM product_notes WHERE analysis_id = ?", (analysis_id,))
                
                # Delete analysis record
                cursor.execute("DELETE FROM analysis_history WHERE id = ?", (analysis_id,))
                
                conn.commit()
                logger.info(f"Deleted analysis {analysis_id}")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Failed to delete analysis: {e}")
            return False
    
    def export_history_csv(self, filename: Optional[str] = None) -> str:
        """Export history to CSV file"""
        try:
            if not filename:
                filename = f"food_analysis_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            df = self.get_history_dataframe(limit=1000)  # Export up to 1000 records
            
            # Clean up data for export
            export_df = df.copy()
            
            # Remove the full analysis_result column for cleaner export
            if 'analysis_result' in export_df.columns:
                export_df = export_df.drop('analysis_result', axis=1)
            
            # Format dates
            for col in ['analyzed_at', 'created_at']:
                if col in export_df.columns:
                    export_df[col] = export_df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
            
            export_df.to_csv(filename, index=False)
            logger.info(f"Exported history to {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            raise
    
    def cache_search_results(self, search_term: str, results: List[Dict]) -> None:
        """Cache search results for performance"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Clean old cache entries (older than 1 hour)
                hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
                cursor.execute("DELETE FROM search_cache WHERE cached_at < ?", (hour_ago,))
                
                # Insert/update new cache entry
                cursor.execute("""
                    INSERT OR REPLACE INTO search_cache (search_term, results)
                    VALUES (?, ?)
                """, (search_term, json.dumps(results)))
                
                conn.commit()
                
        except sqlite3.Error as e:
            logger.warning(f"Failed to cache search results: {e}")
    
    def get_cached_search_results(self, search_term: str) -> Optional[List[Dict]]:
        """Get cached search results if available and recent"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check for recent cache entry (within 1 hour)
                hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
                cursor.execute("""
                    SELECT results FROM search_cache 
                    WHERE search_term = ? AND cached_at > ?
                """, (search_term, hour_ago))
                
                result = cursor.fetchone()
                if result:
                    return json.loads(result[0])
                
                return None
                
        except (sqlite3.Error, json.JSONDecodeError) as e:
            logger.warning(f"Failed to get cached search results: {e}")
            return None
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get database information and statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Database file size
                db_size_bytes = self.db_path.stat().st_size
                db_size_mb = round(db_size_bytes / (1024 * 1024), 2)
                
                # Table row counts
                cursor.execute("SELECT COUNT(*) FROM analysis_history")
                analysis_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM product_notes")
                notes_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM search_cache")
                cache_count = cursor.fetchone()[0]
                
                # Oldest and newest records
                cursor.execute("SELECT MIN(created_at), MAX(created_at) FROM analysis_history")
                date_range = cursor.fetchone()
                
                return {
                    'database_path': str(self.db_path),
                    'size_mb': db_size_mb,
                    'analysis_records': analysis_count,
                    'note_records': notes_count,
                    'cache_entries': cache_count,
                    'date_range': {
                        'oldest': date_range[0],
                        'newest': date_range[1]
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            return {}
    
    def cleanup_old_data(self, days_to_keep: int = 90) -> int:
        """Clean up old records older than specified days"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get count of records to be deleted
                cursor.execute(
                    "SELECT COUNT(*) FROM analysis_history WHERE created_at < ?", 
                    (cutoff_date,)
                )
                count_to_delete = cursor.fetchone()[0]
                
                if count_to_delete > 0:
                    # Delete old notes first
                    cursor.execute("""
                        DELETE FROM product_notes 
                        WHERE analysis_id IN (
                            SELECT id FROM analysis_history WHERE created_at < ?
                        )
                    """, (cutoff_date,))
                    
                    # Delete old analysis records
                    cursor.execute(
                        "DELETE FROM analysis_history WHERE created_at < ?", 
                        (cutoff_date,)
                    )
                    
                    # Clean up old cache entries
                    cursor.execute("DELETE FROM search_cache WHERE cached_at < ?", (cutoff_date,))
                    
                    conn.commit()
                    logger.info(f"Cleaned up {count_to_delete} old records")
                
                return count_to_delete
                
        except sqlite3.Error as e:
            logger.error(f"Cleanup failed: {e}")
            return 0