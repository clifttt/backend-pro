from app.models.base import Base
import app.models

print("OK: models imported")
print("Tables:", list(Base.metadata.tables.keys()))
