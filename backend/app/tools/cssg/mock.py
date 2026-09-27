from uuid import uuid4

from app.db.database import Database
from app.tools.common.contracts import ContentInput, EmptyInput, ToolOutput, ToolSpec


def read_previous_meeting_minutes(db: Database, args: EmptyInput) -> ToolOutput:
    items = db.list_records("cssg", "minutes")
    return ToolOutput(items, f"Reviewed {len(items)} previous meeting record(s).")


def read_project_updates(db: Database, args: EmptyInput) -> ToolOutput:
    items = db.list_records("cssg", "updates")
    return ToolOutput(items, f"Reviewed {len(items)} project update(s).")


def read_action_items(db: Database, args: EmptyInput) -> ToolOutput:
    items = db.list_records("cssg", "actions")
    return ToolOutput(items, f"Reviewed {len(items)} action item(s).")


def write_meeting_minutes(db: Database, args: ContentInput) -> ToolOutput:
    minutes_id = uuid4().hex
    db.put_record("cssg", f"minutes:{minutes_id}", {"id": minutes_id, "title": "Meeting minutes", "notes": args.content})
    return ToolOutput({"id": minutes_id, "content": args.content}, f"Saved meeting minutes {minutes_id}.")


def create_discord_message_draft(db: Database, args: ContentInput) -> ToolOutput:
    draft_id = uuid4().hex
    db.put_record("cssg", f"drafts:{draft_id}", {"id": draft_id, "content": args.content})
    return ToolOutput({"id": draft_id, "content": args.content}, f"Created Discord draft {draft_id}; not posted.")


TOOLS = (
    ToolSpec("read_previous_meeting_minutes", "cssg", False, EmptyInput, read_previous_meeting_minutes),
    ToolSpec("read_project_updates", "cssg", False, EmptyInput, read_project_updates),
    ToolSpec("read_action_items", "cssg", False, EmptyInput, read_action_items),
    ToolSpec("write_meeting_minutes", "cssg", True, ContentInput, write_meeting_minutes),
    ToolSpec("create_discord_message_draft", "cssg", True, ContentInput, create_discord_message_draft),
)
