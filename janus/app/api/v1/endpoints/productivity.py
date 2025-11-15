from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field

from app.repositories.user_repository import ConsentRepository
from app.core.embeddings.embedding_manager import embed_text
from app.db.vector_store import get_qdrant_client, get_or_create_collection
from qdrant_client import models
from app.core.infrastructure.filesystem_manager import read_file, write_file

router = APIRouter(tags=["Productivity"], prefix="/productivity")


def get_consent_repo(request: Request) -> ConsentRepository:
    return ConsentRepository()


def _ensure_consent(repo: ConsentRepository, user_id: int, scope: str) -> None:
    if not repo.has_consent(user_id, scope):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Consent required: {scope}")


class CalendarEvent(BaseModel):
    title: str
    start_ts: float
    end_ts: float
    location: Optional[str] = None
    notes: Optional[str] = None


class CalendarAddRequest(BaseModel):
    user_id: int
    event: CalendarEvent
    index: Optional[bool] = False


@router.post("/calendar/events/add")
async def calendar_add_event(payload: CalendarAddRequest, repo: ConsentRepository = Depends(get_consent_repo)):
    _ensure_consent(repo, payload.user_id, "calendar.write")
    path = f"workspace/productivity/calendar_{payload.user_id}.json"
    try:
        raw = read_file(path)
    except Exception:
        raw = ""
    items: List[Dict[str, Any]] = []
    try:
        if raw and not raw.startswith("Erro:"):
            import json
            items = json.loads(raw)
    except Exception:
        items = []
    evt = payload.event.model_dump()
    items.append(evt)
    import json
    text = json.dumps(items, ensure_ascii=False)
    from asyncio import get_event_loop
    loop = get_event_loop()
    await loop.run_in_executor(None, write_file, path, text, False)
    try:
        if bool(payload.index):
            client = get_qdrant_client()
            coll = get_or_create_collection(f"user_{payload.user_id}")
            content = f"{evt.get('title','')} @ {evt.get('location','')}"
            vec = embed_text(content)
            pid = f"calendar:{payload.user_id}:{int(evt.get('start_ts', 0))}:{int(evt.get('end_ts', 0))}"
            payload_q = {
                "content": content,
                "metadata": {
                    "type": "calendar_event",
                    "user_id": str(payload.user_id),
                    "timestamp": int(evt.get("start_ts") or 0),
                }
            }
            point = models.PointStruct(id=pid, vector=vec, payload=payload_q)
            client.upsert(collection_name=coll, points=[point])
    except Exception:
        pass
    return {"status": "ok", "count": len(items)}


@router.get("/calendar/events")
async def calendar_list_events(user_id: int, repo: ConsentRepository = Depends(get_consent_repo)):
    _ensure_consent(repo, user_id, "calendar.read")
    path = f"workspace/productivity/calendar_{user_id}.json"
    raw = read_file(path)
    try:
        if raw and not raw.startswith("Erro:"):
            import json
            return {"events": json.loads(raw)}
    except Exception:
        pass
    return {"events": []}


class MailMessage(BaseModel):
    to: str
    subject: str
    body: str


class MailSendRequest(BaseModel):
    user_id: int
    message: MailMessage
    index: Optional[bool] = False


@router.post("/mail/messages/send")
async def mail_send(payload: MailSendRequest, repo: ConsentRepository = Depends(get_consent_repo)):
    _ensure_consent(repo, payload.user_id, "mail.send")
    path = f"workspace/productivity/mail_{payload.user_id}.json"
    try:
        raw = read_file(path)
    except Exception:
        raw = ""
    items: List[Dict[str, Any]] = []
    try:
        if raw and not raw.startswith("Erro:"):
            import json
            items = json.loads(raw)
    except Exception:
        items = []
    import time
    msg = payload.message.model_dump()
    msg["sent_at"] = time.time()
    items.append(msg)
    import json
    text = json.dumps(items, ensure_ascii=False)
    from asyncio import get_event_loop
    loop = get_event_loop()
    await loop.run_in_executor(None, write_file, path, text, False)
    try:
        if bool(payload.index):
            client = get_qdrant_client()
            coll = get_or_create_collection(f"user_{payload.user_id}")
            content = f"To: {msg.get('to','')}\nSubject: {msg.get('subject','')}\n{msg.get('body','')}"
            vec = embed_text(content)
            pid = f"mail:{payload.user_id}:{int(msg.get('sent_at', time.time()))}:{hash(content)}"
            payload_q = {
                "content": content,
                "metadata": {
                    "type": "email_message",
                    "user_id": str(payload.user_id),
                    "timestamp": int(msg.get("sent_at") or time.time()),
                }
            }
            point = models.PointStruct(id=pid, vector=vec, payload=payload_q)
            client.upsert(collection_name=coll, points=[point])
    except Exception:
        pass
    return {"status": "queued", "count": len(items)}


@router.get("/mail/messages")
async def mail_list(user_id: int, repo: ConsentRepository = Depends(get_consent_repo)):
    _ensure_consent(repo, user_id, "mail.read")
    path = f"workspace/productivity/mail_{user_id}.json"
    raw = read_file(path)
    try:
        if raw and not raw.startswith("Erro:"):
            import json
            return {"messages": json.loads(raw)}
    except Exception:
        pass
    return {"messages": []}


class NoteItem(BaseModel):
    title: str
    content: str


class NoteAddRequest(BaseModel):
    user_id: int
    note: NoteItem
    index: Optional[bool] = False


@router.post("/notes/add")
async def notes_add(payload: NoteAddRequest, repo: ConsentRepository = Depends(get_consent_repo)):
    _ensure_consent(repo, payload.user_id, "notes.write")
    path = f"workspace/productivity/notes_{payload.user_id}.json"
    try:
        raw = read_file(path)
    except Exception:
        raw = ""
    items: List[Dict[str, Any]] = []
    try:
        if raw and not raw.startswith("Erro:"):
            import json
            items = json.loads(raw)
    except Exception:
        items = []
    note = payload.note.model_dump()
    items.append(note)
    import json
    text = json.dumps(items, ensure_ascii=False)
    from asyncio import get_event_loop
    loop = get_event_loop()
    await loop.run_in_executor(None, write_file, path, text, False)
    try:
        if bool(payload.index):
            client = get_qdrant_client()
            coll = get_or_create_collection(f"user_{payload.user_id}")
            content = f"{note.get('title','')}\n{note.get('content','')}"
            vec = embed_text(content)
            pid = f"note:{payload.user_id}:{hash(content)}"
            payload_q = {
                "content": content,
                "metadata": {
                    "type": "note_item",
                    "user_id": str(payload.user_id),
                    "timestamp": int(__import__('time').time()),
                }
            }
            point = models.PointStruct(id=pid, vector=vec, payload=payload_q)
            client.upsert(collection_name=coll, points=[point])
    except Exception:
        pass
    return {"status": "ok", "count": len(items)}


@router.get("/notes")
async def notes_list(user_id: int, repo: ConsentRepository = Depends(get_consent_repo)):
    _ensure_consent(repo, user_id, "notes.read")
    path = f"workspace/productivity/notes_{user_id}.json"
    raw = read_file(path)
    try:
        if raw and not raw.startswith("Erro:"):
            import json
            return {"notes": json.loads(raw)}
    except Exception:
        pass
    return {"notes": []}
