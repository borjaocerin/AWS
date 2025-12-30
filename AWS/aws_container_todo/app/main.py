from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
import mysql.connector
import time
import uvicorn

app = FastAPI(title="CloudTasks TODO API")

# Database connection parameters from Environment Variables
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "password")
DB_NAME = os.environ.get("DB_NAME", "todos_db")

def get_db_connection():
    # Retry a few times in case MySQL is still starting
    last_err = None
    for _ in range(8):  # ~24s max
        try:
            return mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                connection_timeout=5
            )
        except Exception as e:
            last_err = e
            time.sleep(3)
    raise last_err

# Initialize DB (Simple check/create table)
def init_db():
    try:
        print("[init_db] Waiting for MySQL...")
        # Wait for MySQL server to be ready
        for _ in range(10):  # ~30s max
            try:
                conn = mysql.connector.connect(
                    host=DB_HOST,
                    user=DB_USER,
                    password=DB_PASSWORD,
                    connection_timeout=5
                )
                conn.ping(reconnect=True, attempts=3, delay=2)
                break
            except Exception:
                time.sleep(3)
        else:
            raise RuntimeError("MySQL no responde tras los reintentos")

        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        conn.close()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                completed BOOLEAN DEFAULT FALSE
            )
        """)
        conn.commit()
        conn.close()
        print("[init_db] Database and table ready.")
    except Exception as e:
        print(f"[init_db] Error initializing DB: {e}")

@app.on_event("startup")
def startup_event():
    init_db()

class Task(BaseModel):
    title: str
    description: Optional[str] = None
    completed: bool = False

class TaskOut(Task):
    id: int

@app.get("/")
def read_root():
    return {"message": "Welcome to CloudTasks API"}

@app.get("/tasks", response_model=List[TaskOut])
def get_tasks():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tasks")
    tasks = cursor.fetchall()
    conn.close()
    return tasks

@app.post("/tasks", response_model=TaskOut)
def create_task(task: Task):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    sql = "INSERT INTO tasks (title, description, completed) VALUES (%s, %s, %s)"
    val = (task.title, task.description, task.completed)
    cursor.execute(sql, val)
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return {**task.dict(), "id": new_id}
