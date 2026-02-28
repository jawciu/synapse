import os
from dotenv import load_dotenv
from surrealdb import Surreal, RecordID
from datetime import datetime
import random

load_dotenv()

with Surreal(url=os.getenv("SURREAL_URL")) as db:
    db.use(os.getenv("SURREAL_NS"), os.getenv("SURREAL_DB"))
    db.signin({"username": os.getenv("SURREAL_USER"), "password": os.getenv("SURREAL_PASS")})

    # Create a record
    db.create(RecordID("project", str(random.randint(1, 1000000))), {
        "name": "SurrealDB Dashboard",
        "description": "A modern admin interface for SurrealDB",
        "status": "in_progress",
        "priority": "high",
        "tags": ["typescript", "react", "database"],
        "created_at": datetime.utcnow(),
    })

    # Select a specific record
    print(db.select(RecordID("project", "1")))

    # Print all records in the project table
    all_records = db.select("project")
    print("All records:", all_records)
