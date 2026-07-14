import httpx
import asyncio

async def test_auth():
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000/api/v1") as client:
        print("Registering user...")
        reg_resp = await client.post("/auth/register", json={
            "email": "test@conduit.com",
            "full_name": "Test User",
            "password": "Password1!"
        })
        print(reg_resp.status_code, reg_resp.text)
        
        print("\nLogging in...")
        login_resp = await client.post("/auth/login", json={
            "email": "test@conduit.com",
            "password": "Password1!"
        })
        print(login_resp.status_code, login_resp.text)
        
        if login_resp.status_code == 200:
            tokens = login_resp.json()
            print("\nRefreshing token...")
            refresh_resp = await client.post("/auth/refresh", json=tokens["refresh_token"])
            print(refresh_resp.status_code, refresh_resp.text)

asyncio.run(test_auth())
