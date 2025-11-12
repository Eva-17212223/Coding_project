"""
Memory management for Mammography AI Assistant.
Handles storing, summarizing, and compressing messages, images, and reports.
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any
from config import MEMORY_FILE, MEMORY_THRESHOLD_KB, MEMORY_KEEP_LAST_N


def load_memory() -> List[Dict[str, Any]]:
    """Load conversation history from JSON file.

    Returns:
        List of message dictionaries, empty list if file doesn't exist
    """
    if not MEMORY_FILE.exists():
        return []

    try:
        with open(MEMORY_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Warning: Could not parse {MEMORY_FILE}, starting fresh", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Warning: Error loading memory: {e}", file=sys.stderr)
        return []


def save_memory(messages: List[Dict[str, Any]]) -> None:
    """Save conversation history to JSON file.

    Args:
        messages: List of message dictionaries to save
    """
    try:
        with open(MEMORY_FILE, 'w') as f:
            json.dump(messages, f, indent=2)
    except Exception as e:
        print(f"Error saving memory: {e}", file=sys.stderr)


def get_memory_size_kb(messages: List[Dict[str, Any]]) -> float:
    """Calculate the size of conversation history in KB.

    Args:
        messages: List of message dictionaries

    Returns:
        Size in kilobytes
    """
    json_str = json.dumps(messages)
    size_bytes = len(json_str.encode('utf-8'))
    return size_bytes / 1024


def should_summarize(messages: List[Dict[str, Any]]) -> bool:
    """Check if memory should be summarized based on size threshold.

    Args:
        messages: List of message dictionaries

    Returns:
        True if memory exceeds threshold and should be summarized
    """
    size_kb = get_memory_size_kb(messages)
    return size_kb > MEMORY_THRESHOLD_KB


def create_summary_request(messages: List[Dict[str, Any]], summarization_prompt: str) -> str:
    """Create a summarization request from conversation history.

    Args:
        messages: List of message dictionaries to summarize
        summarization_prompt: Template for summarization prompt

    Returns:
        Formatted prompt for summarization
    """
    conversation_text = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        if isinstance(content, str):
            conversation_text.append(f"{role.upper()}: {content}")
        elif isinstance(content, list):
            # list of items, e.g., images or multipart text
            text_parts = [part.get("text", "") for part in content if part.get("type") == "text"]
            if text_parts:
                conversation_text.append(f"{role.upper()}: {' '.join(text_parts)}")
        elif isinstance(content, dict):
            # structured report
            report_summary = ", ".join(f"{k}: {v}" for k, v in content.items())
            conversation_text.append(f"{role.upper()} [REPORT]: {report_summary}")

    conversation = "\n".join(conversation_text)
    return summarization_prompt.format(conversation=conversation)


def compress_memory(messages: List[Dict[str, Any]], summary: str) -> List[Dict[str, Any]]:
    """Compress memory by replacing old messages with a summary.

    Args:
        messages: Original list of message dictionaries
        summary: Summary text to replace old messages

    Returns:
        Compressed list with summary + last N messages
    """
    summary_message = {
        "role": "system",
        "content": f"[Previous mammography analysis summary]: {summary}"
    }

    recent_messages = messages[-MEMORY_KEEP_LAST_N:] if len(messages) > MEMORY_KEEP_LAST_N else messages

    return [summary_message] + recent_messages


def add_message(messages: List[Dict[str, Any]], role: str, content: Any) -> List[Dict[str, Any]]:
    """Add a new message to the conversation history.

    Args:
        messages: Existing message list
        role: Role of the message sender (user, assistant, system)
        content: Message content (string, list, or dict)

    Returns:
        Updated message list
    """
    messages.append({
        "role": role,
        "content": content
    })
    return messages


# --------------------------
# Optional helper functions
# --------------------------

def add_text_message(messages: List[Dict[str, Any]], role: str, text: str) -> List[Dict[str, Any]]:
    """Convenience function to add text messages."""
    return add_message(messages, role, text)


def add_image_message(messages: List[Dict[str, Any]], role: str, image_path: Path) -> List[Dict[str, Any]]:
    """Add a message representing an analyzed image."""
    content = [{"type": "image", "path": str(image_path)}]
    return add_message(messages, role, content)


def add_report_message(messages: List[Dict[str, Any]], role: str, report: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Add a structured report message."""
    return add_message(messages, role, report)
