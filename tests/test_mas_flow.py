import requests

PAYLOAD = {
    "turn1": "I think traveling is important because it help you to know different culture.",
    "turn2": "Yesterday I go to the museum with my friend, it was very fun.",
}

HIGH_RISK_PAYLOAD = {
    "turn1": "I am very confuse and me no understand homework.",
    "turn2": "Tomorrow I go to park with my family and it are fun.",
}


def test_backend_health_and_pipeline(backend_url):
    health = requests.get(f"{backend_url}/health", timeout=30)
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    resp = requests.post(f"{backend_url}/api/run-pipeline", json=PAYLOAD, timeout=30)
    assert resp.status_code == 200
    body = resp.json()

    assert "student_context" in body
    assert "diagnosis" in body
    assert "plan" in body
    assert "teacher" in body

    diagnosis = body["diagnosis"]
    assert diagnosis["level"] in {1, 2, 3, 4, 5}
    assert 0 <= float(diagnosis["confidence"]) <= 1
    assert diagnosis["breakdown"]["grammar"] >= 0

    plan = body["plan"]
    assert plan["suggestion"]
    assert plan["reasoning"]

    teacher = body["teacher"]
    assert teacher["status"] in {"monitor", "needs_support"}


def test_api_teacher_advisory_updates_plan(backend_url):
    resp = requests.post(f"{backend_url}/api/run-pipeline", json=PAYLOAD, timeout=30)
    resp.raise_for_status()
    diagnosis = resp.json()["diagnosis"]

    advice = {
        "diagnosis": diagnosis,
        "teacher_input": "加強過去式動詞與連接詞練習。",
    }
    plan_resp = requests.post(f"{backend_url}/api/plan", json=advice, timeout=30)
    assert plan_resp.status_code == 200
    plan = plan_resp.json()
    assert plan["suggestion"]
    assert "過去式" in plan["suggestion"] or "教師補充" in plan["suggestion"] or "句型" in plan["suggestion"]


def test_high_risk_student_routes_to_teacher_support(backend_url):
    resp = requests.post(f"{backend_url}/api/run-pipeline", json=HIGH_RISK_PAYLOAD, timeout=30)
    assert resp.status_code == 200
    body = resp.json()
    teacher = body["teacher"]
    diagnosis = body["diagnosis"]

    assert diagnosis["level"] <= 2 or diagnosis["breakdown"]["grammar"] < 50
    assert teacher["status"] == "needs_support"
    assert "教師介入" in teacher["summary"] or "微步距" in teacher["recommended_action"] or "結構化" in teacher["summary"]


def test_frontend_browser_flow(backend_url, browser_page):
    page = browser_page
    page.fill("#turn1", PAYLOAD["turn1"])
    page.fill("#turn2", PAYLOAD["turn2"])
    page.click("#submitBtn")

    page.wait_for_selector("#diagnosisView .level-display")
    diagnosis_text = page.locator("#diagnosisView").inner_text()
    assert "Lv." in diagnosis_text
    assert "詞彙" in diagnosis_text or "文法" in diagnosis_text

    page.wait_for_selector("#planningView .suggestion-box")
    plan_text = page.locator("#planningView").inner_text()
    assert len(plan_text.strip()) > 0

    page.fill("#advisoryInput", "請以簡短句型練習為主，重點修正過去式動詞。")
    page.click("#advisoryBtn")
    page.wait_for_selector("#planningView .suggestion-box")
    updated_plan = page.locator("#planningView").inner_text()
    assert len(updated_plan.strip()) > 0

    page.fill("#overrideInput", "這次練習重點是過去式動詞與簡短句型，請每天練習三句。")
    page.click("#overrideBtn")
    page.wait_for_selector("#planningView .suggestion-box.override")
    override_plan = page.locator("#planningView").inner_text()
    assert "過去式動詞" in override_plan or "簡短句型" in override_plan

    teacher_view = page.locator("#teacherDiagnosisView").inner_text()
    assert "狀態" in teacher_view or "教師介入建議" in teacher_view or "持續觀察" in teacher_view


def test_teacher_override_direct_publish(backend_url):
    payload = {"turn1": "I am happy because my family help me.", "turn2": "We go to school yesterday and it is fun."}
    run = requests.post(f"{backend_url}/api/run-pipeline", json=payload, timeout=30)
    run.raise_for_status()
    diagnosis = run.json()["diagnosis"]

    plan = requests.post(
        f"{backend_url}/api/plan",
        json={"diagnosis": diagnosis, "teacher_input": "補強動詞變化與句子連接。"},
        timeout=30,
    )
    plan.raise_for_status()
    suggestion = plan.json()["suggestion"]
    assert suggestion
    assert "教師補充" in suggestion or "句型" in suggestion or "動詞" in suggestion
