"""
Minimal E2E check: run with DB + Redis up (e.g. docker-compose up -d).
  cd backend && python scripts/test_e2e.py
"""
import sys

def main():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)

    # 1. No-DB routes
    for path in ["/", "/health", "/health/ready"]:
        r = client.get(path)
        assert r.status_code == 200, f"{path} => {r.status_code}"
    print("OK: /, /health, /health/ready")

    # 2. Register
    r = client.post("/api/auth/register", json={
        "email": "e2e-test@example.com",
        "password": "testpass123",
        "practice_name": "E2E Practice",
    })
    if r.status_code not in (200, 201):
        if r.status_code == 400 and "already" in (r.json().get("detail") or "").lower():
            print("OK: register (user exists)")
        else:
            print(f"FAIL: register => {r.status_code} {r.text}")
            return 1
    else:
        print("OK: register")
        token = r.json().get("access_token")
        if not token:
            print("FAIL: no token in register response")
            return 1
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Auth-protected
        r = client.get("/api/auth/me", headers=headers)
        assert r.status_code == 200, f"/api/auth/me => {r.status_code}"
        print("OK: /api/auth/me")

        r = client.get("/api/claims", headers=headers)
        assert r.status_code in (200, 400), f"/api/claims => {r.status_code}"
        print("OK: /api/claims")

        r = client.get("/api/metrics", headers=headers)
        assert r.status_code in (200, 400), f"/api/metrics => {r.status_code}"
        print("OK: /api/metrics")

    print("E2E checks passed.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
