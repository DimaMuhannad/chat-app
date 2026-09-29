from pydantic import BaseModel, Field
from typing import Optional, List, Any


# --- Projects ---
class ProjectBase(BaseModel):
    name: str
    area: str = "ГУАП"
    status: str = "active"
    target_date: Optional[str] = None
    key_result: Optional[str] = None
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    area: Optional[str] = None
    status: Optional[str] = None
    target_date: Optional[str] = None
    key_result: Optional[str] = None
    description: Optional[str] = None


# --- Tasks ---
class TaskBase(BaseModel):
    title: str
    project_id: Optional[int] = None
    description: Optional[str] = None
    area: str = "ГУАП"
    priority: str = "P2"
    status: str = "todo"
    due_date: Optional[str] = None
    estimated_minutes: Optional[int] = None
    context_tag: Optional[str] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    project_id: Optional[int] = None
    description: Optional[str] = None
    area: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[str] = None
    estimated_minutes: Optional[int] = None
    context_tag: Optional[str] = None


class TaskStatusUpdate(BaseModel):
    status: str


# --- Reminders ---
class ReminderBase(BaseModel):
    what: str
    person: Optional[str] = None
    check_date: Optional[str] = None
    context: Optional[str] = None
    source_type: str = "manual"
    task_id: Optional[int] = None
    status: str = "active"


class ReminderCreate(ReminderBase):
    pass


class ReminderUpdate(BaseModel):
    what: Optional[str] = None
    person: Optional[str] = None
    check_date: Optional[str] = None
    context: Optional[str] = None
    status: Optional[str] = None


# --- Documents ---
class DocumentBase(BaseModel):
    title: str
    project_id: Optional[int] = None
    category: str = "general"
    content_markdown: str = ""


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    project_id: Optional[int] = None
    category: Optional[str] = None
    content_markdown: Optional[str] = None
