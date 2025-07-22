from typing import Annotated
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from sqlmodel import Field, Session, SQLModel, create_engine, select

class TodoBase(SQLModel):
    title: str = Field(..., min_length=1, max_length=10)

class Todo(TodoBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    completed: bool = Field(default=False)

class TodoCreate(TodoBase):
    pass

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

@app.post("/")
def create_todo(title: TodoCreate, session: SessionDep):
    db_todo = Todo.model_validate(title)
    session.add(db_todo)
    session.commit()
    session.refresh(db_todo)
    return db_todo
   

@app.get("/")
def get_all(session: SessionDep):
    todos = session.exec(select(Todo)).all()
    # .all()とつけることによって、一度結果をメモリにロードし、リストとして扱うことができる
    return todos

@app.patch("/{todo_id}/toggle")
def update_todo(todo_id: int, session: SessionDep):
    db_todo = session.get(Todo, todo_id)
    if not db_todo:
        raise HTTPException(status_code=404, detail="todo not found")
    db_todo.completed = not db_todo.completed
    session.add(db_todo)
    session.commit()
    session.refresh(db_todo)
    return db_todo

@app.delete("/")
def delete_completed_todo(session: SessionDep):
    completed_todos = session.exec(select(Todo).where(Todo.completed == True))
    for completed_todo in completed_todos:
        session.delete(completed_todo)
        session.commit()
    return {"ok": True}