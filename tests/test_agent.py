"""
tests/test_agent.py
-------------------
Unit tests for the Agent class of the Mammography AI Assistant.
"""

import sys, os
import pytest

# Ajout du dossier parent au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from agent import Agent
from memory import load_memory


@pytest.fixture
def agent_instance():
    """Creates a reusable Agent instance."""
    return Agent(console=None)


def test_greeting(agent_instance):
    """Test that greetings are correctly recognized."""
    messages = load_memory()
    messages, response = agent_instance.process_message(messages, "hello")
    assert "hello" in response.lower() or "assistant" in response.lower()


def test_small_talk(agent_instance):
    """Test basic small talk responses."""
    messages = load_memory()
    messages, response = agent_instance.process_message(messages, "how are you?")
    assert "thank" in response.lower() or "assist" in response.lower()


def test_no_image_found(agent_instance):
    """If there are no images, the assistant should warn the user."""
    messages = []
    messages, response = agent_instance.process_message(messages, "analyze image")
    assert "couldn’t find any" in response.lower() or "couldn't find" in response.lower()


def test_unknown_command(agent_instance):
    """Unknown commands should trigger the fallback response."""
    messages = []
    messages, response = agent_instance.process_message(messages, "what is the weather?")
    assert "assistant" in response.lower() or "analyze" in response.lower()
