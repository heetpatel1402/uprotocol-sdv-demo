# FR-4: The Streamlit dashboard file exists and contains the main title text.
import pathlib

def test_dashboard_file_exists_and_has_title():
    p = pathlib.Path("demo/dashboard.py")
    assert p.exists(), "demo/dashboard.py is missing"
    text = p.read_text(encoding="utf-8")
    assert "Vehicle Status Dashboard" in text
