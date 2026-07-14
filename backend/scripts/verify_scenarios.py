import asyncio
import httpx
import json
import io
import time
import sys

BASE_URL = "http://localhost:8000/api/v1"
EMAIL = f"test_{int(time.time())}@example.com"
PASSWORD = "SecurePass123!"

async def run_scenarios():
    print(f"--- CONDUIT E2E SCENARIO VERIFICATION ---")
    async with httpx.AsyncClient(timeout=120.0) as client:
        # 1. Register & Login
        print(f"\n[1] Registering user: {EMAIL}")
        reg_resp = await client.post(f"{BASE_URL}/auth/register", json={
            "email": EMAIL,
            "password": PASSWORD,
            "full_name": "E2E Tester",
            "username": EMAIL.split("@")[0]
        })
        if reg_resp.status_code not in (200, 201):
            print(f"Registration failed: {reg_resp.text}")
            sys.exit(1)

        login_resp = await client.post(f"{BASE_URL}/auth/login", json={
            "email": EMAIL,
            "password": PASSWORD
        })
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("    -> Success.")

        # 2. Upload Document
        print(f"\n[2] Uploading mock 'Synopsis' document...")
        doc_content = b"""
        DRM (Digital Rights Management) Synopsis.
        DRM is a systematic approach to copyright protection for digital media. 
        The purpose of DRM is to prevent unauthorized redistribution of digital media 
        and restrict the ways consumers can copy content they've purchased.
        """
        files = {"file": ("synopsis.txt", io.BytesIO(doc_content), "text/plain")}
        doc_resp = await client.post(f"{BASE_URL}/documents/upload", files=files, headers=headers)
        doc_id = doc_resp.json()["document_id"]
        
        # Wait for processing
        for _ in range(10):
            status = await client.get(f"{BASE_URL}/documents/{doc_id}/status", headers=headers)
            if status.json().get("status") == "ready":
                break
            await asyncio.sleep(1)
        print("    -> Uploaded and processed.")

        # 3. Create Conversation & Attach
        print(f"\n[3] Creating conversation and attaching document...")
        conv_resp = await client.post(f"{BASE_URL}/conversations", json={"title": "E2E Testing"}, headers=headers)
        conv_id = conv_resp.json()["id"]
        await client.post(f"{BASE_URL}/conversations/{conv_id}/documents?document_id={doc_id}", headers=headers)
        print(f"    -> Attached to Conversation {conv_id}.")

        # Helper to run query
        async def run_query(desc, query, expected_task, expected_tools):
            print(f"\n--- Scenario: {desc} ---")
            print(f"Query: '{query}'")
            resp = await client.post(f"{BASE_URL}/conversations/{conv_id}/query", json={"query": query}, headers=headers)
            if resp.status_code != 200:
                print(f"    [FAIL] HTTP Error {resp.status_code}: {resp.text}")
                return False
            
            data = resp.json()
            meta = data.get("debug_metadata", {})
            plan = meta.get("plan", {})
            task = plan.get("task")
            tools = [s.get("tool") for s in meta.get("tool_graph", [])]
            
            print(f"    Task Assigned: {task}")
            print(f"    Tools Run:     {tools}")
            print(f"    Reasoning:     {plan.get('reasoning')}")
            if plan.get("is_fallback"):
                print(f"    Fallback:      {plan.get('fallback_reason')}")
            
            success = True
            if task != expected_task:
                print(f"    [FAIL] Expected task '{expected_task}', got '{task}'")
                success = False
            
            # general_llm is always at the end, verify intermediate tools
            for t in expected_tools:
                if t not in tools:
                    print(f"    [FAIL] Expected tool '{t}' to run, but got {tools}")
                    success = False
            
            if success:
                print(f"    [PASS] Scenario passed.")
            return success

        # 4. Run Scenarios
        passed = 0
        scenarios = [
            ("Greeting (Heuristic Bypass)", "Hello there!", "GENERAL", ["general_llm"]),
            ("Document Summary", "Summarize my synopsis", "DOCUMENT_SUMMARY", ["document_reader"]),
            ("Document QA", "Explain DRM based on the synopsis", "DOCUMENT_QA", ["document_search"]),
            ("General Knowledge (Hybrid)", "Improve my synopsis with outside facts", "HYBRID", ["document_search", "general_llm"]),
            ("General Knowledge (Pure)", "Who won the FIFA 2022 World Cup?", "GENERAL", ["general_llm"]),
        ]

        for desc, query, exp_task, exp_tools in scenarios:
            if await run_query(desc, query, exp_task, exp_tools):
                passed += 1

        print(f"\n=== SUMMARY ===")
        print(f"Passed {passed} / {len(scenarios)} scenarios.")
        if passed == len(scenarios):
            print("[SUCCESS] ALL SCENARIOS PASSED")
            sys.exit(0)
        else:
            print("[WARNING] SOME SCENARIOS FAILED")
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_scenarios())
