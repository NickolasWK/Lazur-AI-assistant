import time
import pytest
from fastapi.testclient import TestClient

from skeleton.main import DEFAULT_CRITERIA, create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}", mock_delay=0.01)
    with TestClient(app) as test_client:
        yield test_client


def wait_result(client, evaluation_id):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        response = client.get(f"/api/evaluations/{evaluation_id}/result")
        assert response.status_code == 200
        result = response.json()
        if result["status"] in {"completed", "failed"}:
            assert result["status"] == "completed", result
            return result
        time.sleep(0.03)
    pytest.fail("Воркер не завершил работу за 5 секунд")


def test_form_round_trip_and_html_escaping(client):
    assert client.get("/").status_code == 200
    assert client.get("/static/style.css").status_code == 200
    source = '<script>alert("test")</script>'
    response = client.post("/submit", data={
        "criteria_markdown": "1. Критерий А\n2. Критерий Б", "source_code": source,
    }, follow_redirects=False)
    assert response.status_code == 303
    location = response.headers["location"]
    evaluation_id = int(location.rsplit("/", 1)[-1])
    result = wait_result(client, evaluation_id)
    assert len(result["result_json"]["criteria"]) == 3
    assert all(item["status"] == "no_data" for item in result["result_json"]["criteria"])
    assert str(len(source)) in result["result_json"]["summary"]
    assert "# Результат обработки работы" in result["feedback_markdown"]
    page = client.get(location)
    assert page.status_code == 200
    assert source not in page.text
    assert "&lt;script&gt;" in page.text


def test_utf8_file_replaces_pasted_code(client):
    source = 'Console.WriteLine("Привет");'
    response = client.post("/submit", data={
        "criteria_markdown": "- Вывести приветствие", "source_code": "REPLACED",
    }, files={"source_file": ("work.cs", b"\xef\xbb\xbf" + source.encode(), "text/plain")},
        follow_redirects=False)
    assert response.status_code == 303
    page = client.get(response.headers["location"]).text
    assert "Привет" in page
    assert "REPLACED" not in page


@pytest.mark.parametrize("fields", [
    {"criteria_markdown": "1. Критерий", "source_code": "  "},
    {"criteria_markdown": "1. Критерий", "source_code": "x" * (128 * 1024 + 1)},
])
def test_invalid_form_preserves_input(client, fields):
    response = client.post("/submit", data=fields)
    assert response.status_code == 422
    assert 'role="alert"' in response.text
    assert fields["source_code"] in response.text


@pytest.mark.parametrize("filename,content", [
    ("work.exe", b"data"), ("work.cs", b"\xff\xfe"),
    ("work.cs", b"x" * (128 * 1024 + 1)), ("empty.cs", b""),
])
def test_invalid_upload(client, filename, content):
    response = client.post("/submit", data={"criteria_markdown": "1. Test", "source_code": "old"},
        files={"source_file": (filename, content, "text/plain")})
    assert response.status_code == 422
    assert 'role="alert"' in response.text


def test_existing_api_processes_several_jobs_without_ollama(client, monkeypatch):
    async def forbidden(*args, **kwargs):
        raise AssertionError("Вызов реальной модели запрещён в демо")

    monkeypatch.setattr("app.llm.ollama_client.evaluate_code", forbidden)
    ids = []
    for index in range(3):
        response = client.post("/api/evaluations", json={
            "criteria_markdown": "1. Пример", "source_code": f"work {index}",
        })
        assert response.status_code == 202
        ids.append(response.json()["id"])
    assert len(set(ids)) == 3
    for evaluation_id in ids:
        result = wait_result(client, evaluation_id)
        assert "Результаты проверки пока отсутствуют" in result["result_json"]["summary"]
        assert client.get(f"/api/evaluations/{evaluation_id}").json()["status"] == "completed"


def test_missing_and_empty_api_request(client):
    assert client.get("/evaluations/9999").status_code == 404
    assert client.get("/api/evaluations/9999").status_code == 404
    assert client.get("/api/evaluations/9999/result").status_code == 404
    assert client.post("/api/evaluations", json={"criteria_markdown": "", "source_code": ""}).status_code == 422
    assert client.get("/api/health").json() == {"status": "ok", "mode": "mock"}


def test_result_survives_restart(tmp_path):
    url = f"sqlite+aiosqlite:///{(tmp_path / 'persistent.db').as_posix()}"
    with TestClient(create_app(url, mock_delay=0)) as client:
        response = client.post("/api/evaluations", json={"criteria_markdown": "1. Test", "source_code": "saved code"})
        evaluation_id = response.json()["id"]
        wait_result(client, evaluation_id)
    with TestClient(create_app(url, mock_delay=0)) as client:
        assert client.get(f"/api/evaluations/{evaluation_id}/result").json()["status"] == "completed"
        assert "saved code" in client.get(f"/evaluations/{evaluation_id}").text


def test_interrupted_job_resumes(tmp_path):
    url = f"sqlite+aiosqlite:///{(tmp_path / 'resume.db').as_posix()}"
    with TestClient(create_app(url, mock_delay=30)) as client:
        response = client.post("/api/evaluations", json={"criteria_markdown": "1. Test", "source_code": "code"})
        evaluation_id = response.json()["id"]
        deadline = time.monotonic() + 5
        while client.get(f"/api/evaluations/{evaluation_id}").json()["status"] != "processing":
            assert time.monotonic() < deadline
            time.sleep(0.03)
    with TestClient(create_app(url, mock_delay=0)) as client:
        wait_result(client, evaluation_id)


def test_form_uses_server_criteria_and_clean_interface(client):
    page = client.get("/").text
    assert 'name="criteria_markdown"' not in page
    assert 'id="criteria"' not in page
    for marker in ("Демо", "заглушк", "демонстрацион", "→", "↗", "Локальный прототип"):
        assert marker not in page
    response = client.post("/submit", data={
        "source_code": "code", "criteria_markdown": "SPOOFED CRITERIA",
    }, follow_redirects=False)
    assert response.status_code == 303
    location = response.headers["location"]
    result = wait_result(client, int(location.rsplit("/", 1)[-1]))
    result_page = client.get(location).text
    assert "SPOOFED CRITERIA" not in result_page
    assert "Создать класс Student" in result_page
    assert result["result_json"]["criteria"][0]["criterion"] in DEFAULT_CRITERIA
    for marker in ("Демо", "заглушк", "демонстрацион", "→", "↗", "Локальный прототип"):
        assert marker not in result_page
