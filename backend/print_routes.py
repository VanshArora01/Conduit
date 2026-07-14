import asyncio
from app.main import app
for route in app.routes:
    print(type(route), getattr(route, "path", "NO PATH"))
