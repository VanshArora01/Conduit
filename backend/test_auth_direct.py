import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings
from app.schemas.user import UserCreate
from app.services.auth import AuthService

async def test():
    settings = get_settings()
    engine = create_async_engine(settings.ASYNC_DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        user_in = UserCreate(email="test4@conduit.com", full_name="Test 4", password="Password1!")
        try:
            await AuthService.register_user(db, user_in)
            from app.schemas.user import UserLogin
            await AuthService.authenticate_user(db, UserLogin(email="test4@conduit.com", password="Password1!"))
            print("Login Success")
            print("Success")
        except Exception as e:
            import traceback
            traceback.print_exc()

asyncio.run(test())
