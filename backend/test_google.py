import httpx
import asyncio

async def test_google():
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000/api/v1") as client:
        # Register user and login to get JWT token
        reg = await client.post("/auth/register", json={
            "email": "google_test@conduit.com",
            "full_name": "Google Test",
            "password": "Password1!"
        })
        
        login = await client.post("/auth/login", json={
            "email": "google_test@conduit.com",
            "password": "Password1!"
        })
        
        if login.status_code == 200:
            tokens = login.json()
            headers = {"Authorization": f"Bearer {tokens['access_token']}"}
            
            # Hit /google/connect
            print("Connecting to Google...")
            connect_resp = await client.get("/google/connect", headers=headers)
            print(connect_resp.status_code, connect_resp.text)
            
            # Check status
            print("Checking Google status...")
            status_resp = await client.get("/google/status", headers=headers)
            print(status_resp.status_code, status_resp.text)

asyncio.run(test_google())
