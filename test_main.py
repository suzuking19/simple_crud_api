import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from main import app, get_session, Todo

# pytest.fixtureにおけるyield
# yieldより前：テスト実行前に処理
# yieldより後：テスト実行後に処理

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False}, 
        poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session
    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    # 依存関係をクリア
    app.dependency_overrides.clear()

def test_create_todo(client: TestClient):
    response=client.post(
        "/",json={"title":"test_todo"}
    )
    data = response.json()
    
    response.status_code == 201
    assert data["id"] == 1
    assert data["title"] == "test_todo"
    assert data["completed"] == False

def test_get_all(session: Session, client: TestClient):
    todo_1 = Todo(title="todo_1")
    todo_2 = Todo(title="todo_2")
    session.add(todo_1)
    session.add(todo_2)
    session.commit()

    response = client.get("/")
    data = response.json()

    assert data[0]["id"] == 1
    assert data[0]["title"] == "todo_1"
    assert data[0]["completed"] == False
    assert data[1]["id"] == 2
    assert data[1]["title"] == "todo_2"
    assert data[1]["completed"] == False

def test_update_todo(session: Session, client: TestClient):
    db_todo = Todo(title="todo")
    session.add(db_todo)
    session.commit()

    response = client.patch("/1/toggle")
    data = response.json()

    assert data["id"] == 1
    assert data["title"] == "todo"
    assert data["completed"] == True

def test_non_update_todo(session: Session, client: TestClient):
    db_todo = Todo(title="todo")
    session.add(db_todo)
    session.commit()

    response = client.patch("/2/toggle")
    assert response.status_code == 404

def test_delete_completed_todo(session: Session, client: TestClient):
    """
    1. DBにtodo_1, todo_2を登録
    2. todo_1のみ更新(todo_1.completed -> True)
    3. delete_completed_todoを実行
    4. get_allでtodo_2のみが取得できているかを確認
    """
    todo_1 = Todo(title="todo_1")
    todo_2 = Todo(title="todo_2")
    session.add(todo_1)
    session.add(todo_2)
    session.commit()

    response = client.patch("/1/toggle")
    data = response.json()
    assert data["id"] == 1
    assert data["title"] == "todo_1"
    assert data["completed"] == True

    response = client.delete("/")
    data = response.json()
    assert data["ok"] == True

    response = client.get("/")
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == 2
    assert data[0]["title"] == "todo_2"
    assert data[0]["completed"] == False