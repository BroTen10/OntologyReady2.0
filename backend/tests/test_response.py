from __future__ import annotations

from app.core.response import ok, error, paged, ApiResponse, PageInfo, PagedData


def test_ok_default():
    result = ok()
    assert result["code"] == 0
    assert result["message"] == "ok"
    assert result["data"] is None
    assert "timestamp" in result


def test_ok_with_data():
    result = ok({"name": "test"})
    assert result["code"] == 0
    assert result["data"] == {"name": "test"}


def test_ok_custom_message():
    result = ok(None, "success")
    assert result["message"] == "success"


def test_error_response():
    result = error(404, "Not found")
    assert result["code"] == 404
    assert result["message"] == "Not found"
    assert result["data"] is None


def test_error_with_data():
    result = error(422, "Validation error", {"field": "username"})
    assert result["code"] == 422
    assert result["data"] == {"field": "username"}


def test_paged_response():
    items = [{"id": 1}, {"id": 2}]
    result = paged(items, total=10, page=1, page_size=2)
    assert result["code"] == 0
    data = result["data"]
    assert len(data["items"]) == 2
    assert data["page_info"]["total"] == 10
    assert data["page_info"]["page"] == 1
    assert data["page_info"]["page_size"] == 2
    assert data["page_info"]["total_pages"] == 5


def test_paged_zero_items():
    result = paged([], total=0, page=1, page_size=20)
    assert result["data"]["page_info"]["total"] == 0
    assert result["data"]["page_info"]["total_pages"] == 0


def test_paged_single_page():
    result = paged([1, 2, 3], total=3, page=1, page_size=10)
    assert result["data"]["page_info"]["total_pages"] == 1


def test_api_response_model():
    resp = ApiResponse(code=0, message="ok", data="value")
    d = resp.model_dump(mode="json")
    assert d["code"] == 0
    assert d["data"] == "value"


def test_page_info_model():
    pi = PageInfo(page=2, page_size=10, total=25, total_pages=3)
    assert pi.page == 2
    assert pi.total == 25
    assert pi.total_pages == 3
