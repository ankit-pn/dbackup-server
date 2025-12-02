import json
import os
import re
from pathlib import Path
from typing import List, Set, Tuple

def extract_message_ids_and_count_from_json(file_path: Path) -> Tuple[Set[str], int]:
    """
    Parse ChatGPT JSON export file, extract message IDs and count messages.
    Returns (set of message IDs, total message count).
    """
    message_ids = set()
    count = 0
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # ChatGPT export format may vary. Assume data is a list of conversations.
        # Each conversation may have 'messages' list with 'id' field.
        # We'll recursively search for 'id' fields within objects that also have 'message' or 'content'.
        def extract(obj):
            nonlocal count
            if isinstance(obj, dict):
                # Check if this looks like a message object
                if 'id' in obj and ('content' in obj or 'message' in obj):
                    msg_id = obj['id']
                    if isinstance(msg_id, (str, int)):
                        message_ids.add(str(msg_id))
                    count += 1
                # Recursively process values
                for v in obj.values():
                    extract(v)
            elif isinstance(obj, list):
                for item in obj:
                    extract(item)
        extract(data)
    except Exception as e:
        print(f"Error parsing JSON file {file_path}: {e}")
    return message_ids, count

def extract_message_ids_and_count_from_html(file_path: Path) -> Tuple[Set[str], int]:
    """
    Parse ChatGPT HTML export file (approximate). HTML may contain message IDs in data attributes.
    Returns (set of message IDs, total message count).
    """
    message_ids = set()
    count = 0
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        # Look for patterns like data-message-id="..."
        pattern = r'data-message-id=["\']([^"\']+)["\']'
        ids = re.findall(pattern, content)
        message_ids.update(ids)
        count = len(ids)
        # If no pattern, fallback to counting <div> with certain class?
    except Exception as e:
        print(f"Error parsing HTML file {file_path}: {e}")
    return message_ids, count

def parse_chatgpt_file(file_path: Path) -> Tuple[Set[str], int]:
    """
    Parse a single ChatGPT export file (.json or .html).
    Returns (set of message IDs, message count).
    """
    if file_path.suffix.lower() == '.json':
        return extract_message_ids_and_count_from_json(file_path)
    elif file_path.suffix.lower() in ('.html', '.htm'):
        return extract_message_ids_and_count_from_html(file_path)
    else:
        return set(), 0

def process_user_upload_directory(user_dir: Path) -> Tuple[Set[str], int]:
    """
    Process all .json and .html files in user directory.
    Returns combined message IDs and total message count.
    """
    all_message_ids = set()
    total_messages = 0
    for ext in ('*.json', '*.html'):
        for file_path in user_dir.glob(ext):
            ids, cnt = parse_chatgpt_file(file_path)
            all_message_ids.update(ids)
            total_messages += cnt
    return all_message_ids, total_messages

def validate_user_data(user_id: str, base_upload_dir: Path) -> dict:
    """
    Validate uploaded data for a user.
    Returns dict with validation results.
    """
    sanitized = user_id.replace("@", "_at_").replace("/", "_sl_")
    user_dir = base_upload_dir / sanitized
    if not user_dir.exists():
        return {"valid": False, "reason": "No uploaded data found"}

    message_ids, total_messages = process_user_upload_directory(user_dir)

    # Validation criteria
    meets_message_count = total_messages >= 200
    # Overlap calculation will be done separately using MongoDB
    # We'll just return message_ids and count
    return {
        "valid": meets_message_count,
        "total_messages": total_messages,
        "unique_message_ids": len(message_ids),
        "message_ids": list(message_ids),
        "meets_message_count": meets_message_count,
        "reason": None if meets_message_count else f"Message count {total_messages} < 200"
    }