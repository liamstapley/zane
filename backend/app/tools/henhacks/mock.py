from uuid import uuid4

from app.db.database import Database
from app.tools.common.contracts import (
    ContentInput,
    EmptyInput,
    IdInput,
    LabelInput,
    SearchInput,
    ToolOutput,
    ToolSpec,
    TrackerInput,
)


def search_sponsor_emails(db: Database, args: SearchInput) -> ToolOutput:
    matches = [
        item
        for item in db.list_records("henhacks", "threads")
        if args.query.lower() in f"{item['sponsor']} {item['subject']} {item['message']}".lower()
    ]
    return ToolOutput(matches, f"Found {len(matches)} sponsor thread(s).")


def read_email_thread(db: Database, args: IdInput) -> ToolOutput:
    item = db.get_record("henhacks", f"threads:{args.id}")
    return ToolOutput(item, f"Reviewed sponsor thread {args.id}.")


def apply_henhacks_label(db: Database, args: LabelInput) -> ToolOutput:
    item = db.get_record("henhacks", f"threads:{args.id}")
    item["label"] = args.label
    db.put_record("henhacks", f"threads:{args.id}", item)
    return ToolOutput({"id": args.id, "label": args.label}, f"Updated label for {args.id}.")


def read_sponsor_tracker(db: Database, args: EmptyInput) -> ToolOutput:
    items = db.list_records("henhacks", "tracker")
    return ToolOutput(items, f"Reviewed {len(items)} sponsor tracker row(s).")


def update_sponsor_tracker(db: Database, args: TrackerInput) -> ToolOutput:
    item = db.get_record("henhacks", f"tracker:{args.id}")
    item["perk"] = args.perk
    db.put_record("henhacks", f"tracker:{args.id}", item)
    return ToolOutput({"id": args.id, "perk": args.perk}, f"Updated sponsor tracker row {args.id}.")


def create_email_draft_document(db: Database, args: ContentInput) -> ToolOutput:
    draft_id = uuid4().hex
    db.put_record("henhacks", f"drafts:{draft_id}", {"id": draft_id, "content": args.content})
    return ToolOutput({"id": draft_id, "content": args.content}, f"Created email draft document {draft_id}; not sent.")


TOOLS = (
    ToolSpec("search_sponsor_emails", "henhacks", False, SearchInput, search_sponsor_emails),
    ToolSpec("read_email_thread", "henhacks", False, IdInput, read_email_thread),
    ToolSpec("apply_henhacks_label", "henhacks", True, LabelInput, apply_henhacks_label),
    ToolSpec("read_sponsor_tracker", "henhacks", False, EmptyInput, read_sponsor_tracker),
    ToolSpec("update_sponsor_tracker", "henhacks", True, TrackerInput, update_sponsor_tracker),
    ToolSpec("create_email_draft_document", "henhacks", True, ContentInput, create_email_draft_document),
)
