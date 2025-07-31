from pymongo import MongoClient
import psycopg2
from psycopg2.extras import Json

from typing import List, Dict, Any
from config import logger

class DatabaseManager:
    """Quản lý lưu trữ dữ liệu vào MongoDB hoặc PostgreSQL"""
    
    def __init__(self, db_type: str = "mongodb", **kwargs):
        self.db_type = db_type.lower()
        
        if self.db_type == "mongodb":
            self.mongo_client = MongoClient(kwargs.get('mongo_uri', 'mongodb://localhost:27017/'))
            self.db = self.mongo_client[kwargs.get('db_name', 'topik')]
            self.collection = self.db[kwargs.get('collection', 'questions')]
            logger.info("Đã kết nối MongoDB")
            
        elif self.db_type == "postgresql":
            self.pg_conn = psycopg2.connect(
                host=kwargs.get('host', 'localhost'),
                database=kwargs.get('database', 'topik'),
                user=kwargs.get('user', 'postgres'),
                password=kwargs.get('password', '')
            )
            self.table_name = kwargs.get('table', 'topik_questions')
            self._create_pg_table()
            logger.info("Đã kết nối PostgreSQL")
    
    def _create_pg_table(self):
        """Tạo bảng PostgreSQL nếu chưa tồn tại"""
        with self.pg_conn.cursor() as cur:
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id SERIAL PRIMARY KEY,
                    question_id VARCHAR(50) UNIQUE,
                    data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{self.table_name}_question_id ON {self.table_name}(question_id)")
            self.pg_conn.commit()
    
    async def save_questions(self, questions: List[Dict[str, Any]]) -> bool:
        """Lưu câu hỏi vào database"""
        try:
            if self.db_type == "mongodb":
                # MongoDB
                for question in questions:
                    self.collection.update_one(
                        {"question_id": question.get("question_id")},
                        {"$set": question},
                        upsert=True
                    )
                    
            elif self.db_type == "postgresql":
                # PostgreSQL
                with self.pg_conn.cursor() as cur:
                    for question in questions:
                        cur.execute(f"""
                            INSERT INTO {self.table_name} (question_id, data)
                            VALUES (%s, %s)
                            ON CONFLICT (question_id) 
                            DO UPDATE SET data = EXCLUDED.data
                        """, (question.get("question_id"), Json(question)))
                    self.pg_conn.commit()
            
            logger.info(f"Đã lưu {len(questions)} câu hỏi vào {self.db_type}")
            return True
            
        except Exception as e:
            logger.error(f"Lỗi lưu dữ liệu vào {self.db_type}: {e}")
            return False