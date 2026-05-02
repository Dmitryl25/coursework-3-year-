"""
Smoke / integration tests for Food Diary API.

Запуск:
    # внутри контейнера backend (после `docker compose up`)
    docker compose exec backend python run_tests.py

    # или с хоста
    BASE_URL=http://localhost:8000 python backend/run_tests.py

Использует только stdlib (urllib + json), чтобы не требовать новых пакетов.
В конце печатает таблицу результатов и возвращает exit code = число падений.
"""
from __future__ import annotations

import json
import os
import sys
import time
import uuid
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, date, timedelta
from typing import Any, Optional

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")
TIMEOUT = 30

# ---------- ANSI colors ----------
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
DIM = "\033[2m"
RESET = "\033[0m"


# ---------- HTTP helper ----------
def request(
    method: str,
    path: str,
    *,
    params: Optional[dict] = None,
    json_body: Any = None,
) -> tuple[int, Any]:
    url = BASE_URL + path
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    data = None
    headers = {"Accept": "application/json"}
    if json_body is not None:
        data = json.dumps(json_body, default=str).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body = resp.read().decode("utf-8") or "null"
            return resp.status, json.loads(body)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") or "null"
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = body
        return e.code, payload
    except urllib.error.URLError as e:
        return 0, str(e)


# ---------- Test runner ----------
class Runner:
    def __init__(self) -> None:
        self.results: list[tuple[str, bool, str]] = []

    def check(self, name: str, ok: bool, detail: str = "") -> bool:
        mark = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
        line = f"  [{mark}] {name}"
        if detail and not ok:
            line += f" {DIM}— {detail}{RESET}"
        print(line)
        self.results.append((name, ok, detail))
        return ok

    def section(self, title: str) -> None:
        print(f"\n{BLUE}== {title} =={RESET}")

    def summary(self) -> int:
        passed = sum(1 for _, ok, _ in self.results if ok)
        failed = len(self.results) - passed
        print()
        print("=" * 60)
        if failed == 0:
            print(f"{GREEN}ALL GREEN — {passed}/{len(self.results)} passed{RESET}")
        else:
            print(f"{RED}{failed} FAILED{RESET}, {GREEN}{passed} passed{RESET}  (total {len(self.results)})")
            print(f"\n{YELLOW}Failures:{RESET}")
            for name, ok, detail in self.results:
                if not ok:
                    print(f"  - {name}: {detail}")
        print("=" * 60)
        return failed


# ---------- Wait for service ----------
def wait_for_service(r: Runner) -> bool:
    print(f"{DIM}Waiting for {BASE_URL} ...{RESET}")
    deadline = time.time() + 60
    last_err = ""
    while time.time() < deadline:
        code, body = request("GET", "/health")
        if code == 200:
            print(f"{GREEN}Service is up.{RESET}")
            return True
        last_err = f"code={code} body={body!r}"
        time.sleep(1)
    r.check("service /health reachable", False, last_err)
    return False


# ---------- Tests ----------
def main() -> int:
    print(f"Food Diary API tests against {BLUE}{BASE_URL}{RESET}")
    r = Runner()

    if not wait_for_service(r):
        return r.summary() or 1

    # ===== root / health =====
    r.section("Root & Health")
    code, body = request("GET", "/")
    r.check("GET /", code == 200 and isinstance(body, dict) and "version" in body, f"{code} {body}")
    code, body = request("GET", "/health")
    r.check("GET /health", code == 200 and body.get("status") == "healthy", f"{code} {body}")

    # ===== auth: register =====
    r.section("Auth")
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    password = "secret123"
    user_payload = {
        "email": email,
        "password": password,
        "gender": "male",
        "age": 25,
        "weight": 75.0,
        "height": 180.0,
        "activity_level": 1.5,
    }
    code, body = request("POST", "/auth/register", json_body=user_payload)
    ok = code == 201 and isinstance(body, dict) and body.get("email") == email
    r.check("POST /auth/register", ok, f"{code} {body}")
    user_id = body.get("id") if isinstance(body, dict) else None

    # duplicate registration
    code, body = request("POST", "/auth/register", json_body=user_payload)
    r.check("POST /auth/register duplicate -> 400", code == 400, f"{code} {body}")

    # validation error: weak password
    bad = dict(user_payload, email=f"x_{uuid.uuid4().hex[:6]}@e.com", password="123")
    code, body = request("POST", "/auth/register", json_body=bad)
    r.check("POST /auth/register weak password -> 422", code == 422, f"{code} {body}")

    # login OK
    code, body = request("POST", "/auth/login", json_body={"email": email, "password": password})
    r.check("POST /auth/login OK", code == 200 and body.get("user_id") == user_id, f"{code} {body}")

    # login wrong password
    code, body = request("POST", "/auth/login", json_body={"email": email, "password": "wrong"})
    r.check("POST /auth/login wrong password -> 401", code == 401, f"{code} {body}")

    # tdee
    if user_id is not None:
        code, body = request("GET", f"/auth/user/{user_id}/tdee")
        r.check(
            "GET /auth/user/{id}/tdee",
            code == 200 and isinstance(body, dict) and body.get("tdee", 0) > 0,
            f"{code} {body}",
        )
        code, body = request("GET", f"/auth/user/{user_id}/daily-needs")
        ok = (
            code == 200
            and isinstance(body, dict)
            and body.get("tdee", 0) > 0
            and body.get("recommended_proteins", 0) > 0
        )
        r.check("GET /auth/user/{id}/daily-needs", ok, f"{code} {body}")

        code, body = request("GET", "/auth/user/999999/tdee")
        r.check("GET /auth/user/{missing}/tdee -> 404", code == 404, f"{code} {body}")

    # ===== food =====
    r.section("Food")
    food_name = f"TestFood_{uuid.uuid4().hex[:6]}"
    food_payload = {
        "name": food_name,
        "calories": 250,
        "proteins": 10.0,
        "fats": 5.0,
        "carbohydrates": 40.0,
    }
    code, body = request("POST", "/food/", json_body=food_payload)
    ok = code == 201 and isinstance(body, dict) and body.get("name") == food_name
    r.check("POST /food/", ok, f"{code} {body}")
    food_id = body.get("id") if isinstance(body, dict) else None

    if food_id:
        code, body = request("GET", f"/food/{food_id}")
        r.check("GET /food/{id}", code == 200 and body.get("id") == food_id, f"{code} {body}")

    code, body = request("GET", "/food/999999")
    r.check("GET /food/{missing} -> 404", code == 404, f"{code} {body}")

    code, body = request("GET", "/food/search", params={"query": food_name[:6], "limit": 5})
    r.check(
        "GET /food/search",
        code == 200 and isinstance(body, list),
        f"{code} {body}",
    )

    code, body = request(
        "GET",
        "/food/search/advanced",
        params={"query": food_name[:6], "min_calories": 1, "max_calories": 10000, "limit": 5},
    )
    r.check("GET /food/search/advanced", code == 200 and isinstance(body, list), f"{code} {body}")

    code, body = request("GET", "/food/popular", params={"limit": 5})
    r.check("GET /food/popular", code == 200 and isinstance(body, list), f"{code} {body}")

    # validation: bad food
    code, body = request(
        "POST", "/food/", json_body={"name": "X", "calories": -1, "proteins": 1, "fats": 1, "carbohydrates": 1}
    )
    r.check("POST /food/ negative calories -> 422", code == 422, f"{code} {body}")

    # ===== diary =====
    r.section("Diary")
    entry_id = None
    if user_id is not None and food_id is not None:
        now_iso = datetime.now().isoformat()
        today_str = date.today().isoformat()

        entry_payload = {"food_id": food_id, "weight": 200.0, "datetime": now_iso}
        code, body = request("POST", "/diary/entry", params={"user_id": user_id}, json_body=entry_payload)
        ok = (
            code == 201
            and isinstance(body, dict)
            and abs(body.get("total_calories", 0) - food_payload["calories"] * 2.0) < 0.01
        )
        r.check("POST /diary/entry (calc check)", ok, f"{code} {body}")
        entry_id = body.get("id") if isinstance(body, dict) else None

        # food not found
        code, body = request(
            "POST",
            "/diary/entry",
            params={"user_id": user_id},
            json_body={"food_id": 999999, "weight": 100, "datetime": now_iso},
        )
        r.check("POST /diary/entry missing food -> 404", code == 404, f"{code} {body}")

        # bulk
        bulk_payload = {
            "datetime": now_iso,
            "items": [
                {
                    "raw_text": "test item",
                    "weight_g": 150.0,
                    "matched_food_id": food_id,
                    "matched_name": food_name,
                    "confidence": 0.95,
                },
                {
                    "raw_text": "no match",
                    "weight_g": 100.0,
                    "matched_food_id": None,
                    "confidence": 0.1,
                },
            ],
        }
        code, body = request("POST", "/diary/bulk", params={"user_id": user_id}, json_body=bulk_payload)
        r.check(
            "POST /diary/bulk (skips unmatched)",
            code == 201 and isinstance(body, list) and len(body) == 1,
            f"{code} {body}",
        )

        # day summary
        code, body = request("GET", f"/diary/day/{today_str}", params={"user_id": user_id})
        ok = code == 200 and isinstance(body, dict) and body.get("entries_count", 0) >= 2
        r.check("GET /diary/day/{date}", ok, f"{code} {body}")

        # bad date
        code, body = request("GET", "/diary/day/not-a-date", params={"user_id": user_id})
        r.check("GET /diary/day/{bad} -> 400", code == 400, f"{code} {body}")

        # week
        code, body = request("GET", "/diary/week", params={"user_id": user_id})
        r.check(
            "GET /diary/week",
            code == 200 and isinstance(body, dict) and "daily_stats" in body,
            f"{code} {body}",
        )

        # week with explicit date
        code, body = request(
            "GET", "/diary/week", params={"user_id": user_id, "end_date": today_str}
        )
        r.check("GET /diary/week?end_date=", code == 200, f"{code} {body}")

        # patch entry
        if entry_id is not None:
            code, body = request(
                "PATCH",
                f"/diary/entry/{entry_id}",
                params={"user_id": user_id, "weight": 333.0},
            )
            r.check(
                "PATCH /diary/entry/{id}",
                code == 200 and body.get("new_weight") == 333.0,
                f"{code} {body}",
            )

            # delete entry
            code, body = request(
                "DELETE", f"/diary/entry/{entry_id}", params={"user_id": user_id}
            )
            r.check("DELETE /diary/entry/{id}", code == 200, f"{code} {body}")

            # delete again -> 404
            code, body = request(
                "DELETE", f"/diary/entry/{entry_id}", params={"user_id": user_id}
            )
            r.check("DELETE /diary/entry/{id} again -> 404", code == 404, f"{code} {body}")

    # ===== recommendations =====
    r.section("Recommendations")
    if user_id is not None:
        code, body = request("GET", "/recommendations/today", params={"user_id": user_id})
        ok = (
            code == 200
            and isinstance(body, dict)
            and "tdee" in body
            and "remaining_calories" in body
            and "message" in body
        )
        r.check("GET /recommendations/today", ok, f"{code} {body}")

    code, body = request("GET", "/recommendations/today", params={"user_id": 999999})
    r.check("GET /recommendations/today missing user -> 404", code == 404, f"{code} {body}")

    # ===== OCR (text-only path) =====
    r.section("OCR")
    if user_id is not None:
        # match-text — это text-only ветка, не требует фото и быстрее.
        # Если FAISS не нашёл совпадения, эндпоинт всё равно отвечает 200 со status=failed.
        code, body = request(
            "POST",
            "/ocr/match-text",
            params={"text": food_name, "weight_g": 100, "user_id": user_id},
        )
        ok = code == 200 and isinstance(body, dict) and "items" in body and "status" in body
        r.check("POST /ocr/match-text", ok, f"{code} {body}")

        code, body = request("GET", f"/ocr/user/{user_id}", params={"limit": 5})
        r.check(
            "GET /ocr/user/{id}",
            code == 200 and isinstance(body, list),
            f"{code} {body}",
        )

        code, body = request("GET", "/ocr/pending", params={"limit": 5})
        r.check("GET /ocr/pending", code == 200 and isinstance(body, list), f"{code} {body}")

    return r.summary()


if __name__ == "__main__":
    sys.exit(main())
