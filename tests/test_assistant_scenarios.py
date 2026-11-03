import io
import openpyxl
from docx import Document
from pptx import Presentation


def test_scenario_1_conversational_question_creates_no_file(client, auth_user_a):
    """
    Scenario 1: A general technical question returns a conversational answer and creates no file.
    Also: mentioning PowerPoint in an informational question ('How do I create a PowerPoint?') does not create a file.
    """
    res1 = client.post(
        "/api/v1/chat",
        json={"message": "Explain the difference between FastAPI and Django."},
        headers=auth_user_a["headers"],
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["intent"] == "conversation"
    assert data1["file"] is None
    assert "FastAPI" in data1["assistant_message"]
    assert "Django" in data1["assistant_message"]

    # Verify no file records were created
    files_res = client.get("/api/v1/files", headers=auth_user_a["headers"])
    assert len(files_res.json()) == 0

    # Also test mentioning office format in an informational question
    res2 = client.post(
        "/api/v1/chat",
        json={"message": "How do I create a PowerPoint presentation?"},
        headers=auth_user_a["headers"],
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["intent"] == "conversation"
    assert data2["file"] is None


def test_scenario_2_expense_tracker_creates_valid_excel(client, auth_user_a):
    """
    Scenario 2: An expense-tracker request creates a valid .xlsx file with expected sheets and formulas.
    """
    res = client.post(
        "/api/v1/chat",
        json={"message": "Create an Excel monthly expense tracker with category totals."},
        headers=auth_user_a["headers"],
    )
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "generate_document"
    assert data["file"] is not None
    file_info = data["file"]
    assert file_info["format"] == "excel"
    assert file_info["file_name"].endswith(".xlsx")

    # Download file and verify with openpyxl
    download_res = client.get(file_info["download_url"], headers=auth_user_a["headers"])
    assert download_res.status_code == 200
    assert len(download_res.content) > 0

    wb = openpyxl.load_workbook(io.BytesIO(download_res.content), data_only=False)
    assert "Expense Log" in wb.sheetnames
    sheet = wb["Expense Log"]
    # Check header
    assert sheet.cell(row=1, column=1).value == "Category"
    # Check formula presence
    formula_found = False
    for row in sheet.iter_rows():
        for cell in row:
            if isinstance(cell.value, str) and cell.value.startswith("=SUM"):
                formula_found = True
    assert formula_found, "Formula =SUM was not found in worksheet"
    wb.close()


def test_scenario_3_project_proposal_creates_valid_word(client, auth_user_a):
    """
    Scenario 3: A project-proposal request creates a readable .docx file with headings/sections.
    """
    res = client.post(
        "/api/v1/chat",
        json={"message": "Prepare a detailed project proposal for an AI chatbot."},
        headers=auth_user_a["headers"],
    )
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "generate_document"
    assert data["file"] is not None
    file_info = data["file"]
    assert file_info["format"] == "word"
    assert file_info["file_name"].endswith(".docx")

    # Download and verify with python-docx
    download_res = client.get(file_info["download_url"], headers=auth_user_a["headers"])
    assert download_res.status_code == 200
    doc = Document(io.BytesIO(download_res.content))
    paragraphs = [p.text for p in doc.paragraphs if p.text]
    assert any("Project Proposal" in p for p in paragraphs)
    assert any("Executive Summary" in p for p in paragraphs)
    assert len(doc.tables) > 0


def test_scenario_4_presentation_creates_valid_powerpoint(client, auth_user_a):
    """
    Scenario 4: An AI-presentation request creates a valid .pptx file with title and conclusion slides.
    """
    res = client.post(
        "/api/v1/chat",
        json={"message": "Create a 7-slide presentation about AI agents."},
        headers=auth_user_a["headers"],
    )
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "generate_document"
    assert data["file"] is not None
    file_info = data["file"]
    assert file_info["format"] == "powerpoint"
    assert file_info["file_name"].endswith(".pptx")

    # Download and verify with python-pptx
    download_res = client.get(file_info["download_url"], headers=auth_user_a["headers"])
    assert download_res.status_code == 200
    prs = Presentation(io.BytesIO(download_res.content))
    assert len(prs.slides) >= 4
    # Check title slide
    first_slide_text = [shape.text_frame.text for shape in prs.slides[0].shapes if shape.has_text_frame]
    assert any("AI Agents" in t for t in first_slide_text)


def test_scenario_5_explicit_preference_saved_to_persona(client, auth_user_a):
    """
    Scenario 5: An explicit stable preference is saved to the correct user's persona.
    """
    msg = "Always use a clean, minimal layout for business documents."
    res = client.post(
        "/api/v1/chat",
        json={"message": msg},
        headers=auth_user_a["headers"],
    )
    assert res.status_code == 200

    # Verify persona settings
    persona_res = client.get("/api/v1/persona", headers=auth_user_a["headers"])
    assert persona_res.status_code == 200
    data = persona_res.json()
    assert len(data["items"]) >= 1
    pref = data["items"][0]
    assert pref["source"] == "explicit"
    assert "clean" in str(pref["value"]) or "minimal" in str(pref["value"])


def test_scenario_6_and_7_preference_retrieval_and_override_precedence(client, auth_user_a):
    """
    Scenario 6 & 7:
    - Later request applies saved preference.
    - A one-time conflicting style instruction overrides persona for that output but does not mutate the saved preference.
    """
    # 1. Save an explicit preference for Excel: include_charts = True
    save_res = client.post(
        "/api/v1/persona/preferences",
        json={"category": "excel", "key": "include_charts", "value": True},
        headers=auth_user_a["headers"],
    )
    assert save_res.status_code == 201

    # 2. Make an Excel request with a one-time conflicting instruction: "without charts"
    chat_res = client.post(
        "/api/v1/chat",
        json={"message": "Generate an Excel budget report without charts for this run."},
        headers=auth_user_a["headers"],
    )
    assert chat_res.status_code == 200
    data = chat_res.json()
    assert data["file"] is not None

    # Download and verify the generated workbook has NO charts
    download_res = client.get(data["file"]["download_url"], headers=auth_user_a["headers"])
    wb = openpyxl.load_workbook(io.BytesIO(download_res.content))
    for ws in wb.worksheets:
        assert len(ws._charts) == 0, "Chart was found despite one-time override"
    wb.close()

    # 3. Check that the saved persona preference was NOT mutated in the database!
    persona_res = client.get("/api/v1/persona", headers=auth_user_a["headers"])
    assert persona_res.status_code == 200
    pdata = persona_res.json()
    assert pdata["excel"]["include_charts"] is True


def test_scenario_8_user_can_edit_and_delete_preference(client, auth_user_a):
    """
    Scenario 8: A user can edit and delete a saved preference.
    """
    # Create preference
    create_res = client.post(
        "/api/v1/persona/preferences",
        json={"category": "general", "key": "tone", "value": "concise"},
        headers=auth_user_a["headers"],
    )
    assert create_res.status_code == 201
    pref_id = create_res.json()["id"]

    # Edit preference
    patch_res = client.patch(
        f"/api/v1/persona/preferences/{pref_id}",
        json={"value": "formal"},
        headers=auth_user_a["headers"],
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["value"] == "formal"

    # Delete preference
    del_res = client.delete(
        f"/api/v1/persona/preferences/{pref_id}",
        headers=auth_user_a["headers"],
    )
    assert del_res.status_code == 204

    # Verify gone
    persona_res = client.get("/api/v1/persona", headers=auth_user_a["headers"])
    assert len(persona_res.json()["items"]) == 0


def test_scenario_9_user_isolation(client, auth_user_a, auth_user_b):
    """
    Scenario 9: User A cannot list, read, modify, or download User B's conversations, persona, or files.
    """
    # 1. User A creates a conversation, preference, and file
    chat_a = client.post(
        "/api/v1/chat",
        json={"message": "Create an Excel expense sheet for Alice."},
        headers=auth_user_a["headers"],
    )
    assert chat_a.status_code == 200
    conv_id_a = chat_a.json()["conversation_id"]
    file_id_a = chat_a.json()["file"]["id"]

    pref_a = client.post(
        "/api/v1/persona/preferences",
        json={"category": "general", "key": "secret_pref", "value": "alice_only"},
        headers=auth_user_a["headers"],
    )
    pref_id_a = pref_a.json()["id"]

    # 2. User B attempts to access User A's conversation
    get_conv_b = client.get(f"/api/v1/conversations/{conv_id_a}", headers=auth_user_b["headers"])
    assert get_conv_b.status_code == 404

    # 3. User B attempts to download User A's file
    get_file_b = client.get(f"/api/v1/files/{file_id_a}", headers=auth_user_b["headers"])
    assert get_file_b.status_code == 404

    dl_file_b = client.get(f"/api/v1/files/{file_id_a}/download", headers=auth_user_b["headers"])
    assert dl_file_b.status_code == 404

    # 4. User B attempts to delete User A's preference
    del_pref_b = client.delete(f"/api/v1/persona/preferences/{pref_id_a}", headers=auth_user_b["headers"])
    assert del_pref_b.status_code == 404

    # 5. User B's persona does not contain User A's preference
    persona_b = client.get("/api/v1/persona", headers=auth_user_b["headers"])
    assert "secret_pref" not in persona_b.json()["general"]


def test_scenario_10_mcp_status_and_fallback(client, auth_user_a):
    """
    Scenario 10: MCP status is reported honestly with discovered tools, and fallback to local generation is active.
    """
    status_res = client.get("/api/v1/integrations/microsoft/status", headers=auth_user_a["headers"])
    assert status_res.status_code == 200
    data = status_res.json()
    assert "fallback_active" in data
    assert data["fallback_active"] is True
    # If MCP is disabled, error explains the configuration status
    assert "Microsoft MCP" in (data["error"] or "") or data["enabled"] is False


def test_unauthenticated_requests_rejected(client):
    """
    Tests that endpoints are properly protected when no credentials are provided.
    """
    res = client.get("/api/v1/persona")
    assert res.status_code == 401

    res = client.get("/api/v1/files")
    assert res.status_code == 401

    res = client.post("/api/v1/chat", json={"message": "hello"})
    assert res.status_code == 401


def test_clarification_flow(client, auth_user_a):
    """
    Tests that an ambiguous request triggers a clarification rather than creating a file.
    """
    res = client.post(
        "/api/v1/chat",
        json={"message": "Create a document"},
        headers=auth_user_a["headers"],
    )
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "clarification"
    assert data["clarification_required"] is True
    assert data["file"] is None
    assert "What format would you like" in data["assistant_message"]
