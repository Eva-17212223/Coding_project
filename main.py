#!/usr/bin/env python3
"""
Main CLI entry point for the Mammography AI Assistant.
Provides a Rich-styled interactive console and integrates a PyQt image viewer.
"""

import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.theme import Theme
from rich.text import Text

from agent import Agent
from memory import load_memory, save_memory, get_memory_size_kb
from config import MEMORY_THRESHOLD_KB, ANNOTATED_DIR

# -------------------------------------------------------------
# ASCII Art - Branding
# -------------------------------------------------------------
ASCII_AIVANCITY = """

███╗░░░███╗███████╗██████╗░██╗░█████╗░░█████╗░██╗░░░░░
████╗░████║██╔════╝██╔══██╗██║██╔══██╗██╔══██╗██║░░░░░
██╔████╔██║█████╗░░██║░░██║██║██║░░╚═╝███████║██║░░░░░
██║╚██╔╝██║██╔══╝░░██║░░██║██║██║░░██╗██╔══██║██║░░░░░
██║░╚═╝░██║███████╗██████╔╝██║╚█████╔╝██║░░██║███████╗
╚═╝░░░░░╚═╝╚══════╝╚═════╝░╚═╝░╚════╝░╚═╝░░╚═╝╚══════╝
"""

ASCII_AGENT = """
                                         █████   
                                        ░░███    
  ██████    ███████  ██████  ████████   ███████  
 ░░░░░███  ███░░███ ███░░███░░███░░███ ░░░███░   
  ███████ ░███ ░███░███████  ░███ ░███   ░███    
 ███░░███ ░███ ░███░███░░░   ░███ ░███   ░███ ███
░░████████░░███████░░██████  ████ █████  ░░█████ 
 ░░░░░░░░  ░░░░░███ ░░░░░░  ░░░░ ░░░░░    ░░░░░  
           ███ ░███                              
          ░░██████                               
           ░░░░░░                                """

# -------------------------------------------------------------
# Initialize Rich console
# -------------------------------------------------------------
console = Console(theme=Theme({
    "user": "#33ccff bold",
    "assistant": "#33ccff bold",
    "tool": "yellow",
    "success": "green",
    "warning": "yellow",
    "error": "red bold",
    "dim": "dim"
}))

# -------------------------------------------------------------
# Helper functions
# -------------------------------------------------------------
def print_banner():
    """Displays the ASCII banners."""
    console.print(
        Panel(
            Text(ASCII_AIVANCITY.strip("\n") + "\n" + ASCII_AGENT.strip("\n"), justify="center"),
            border_style="user"
        )
    )


def print_help():
    """Displays available commands."""
    help_text = """
**Available commands:**
• /help           - Show this help message
• /clear          - Clear conversation history
• /stats          - Show memory statistics
• /show           - Show the latest annotated image (PyQt viewer)
• /exit           - Exit the assistant

Just type your message to interact with the AI!
"""
    console.print(Panel(help_text.strip(), title="[bold user]Help[/bold user]", border_style="user"))


def print_stats(messages):
    """Displays memory usage statistics."""
    size_kb = get_memory_size_kb(messages)
    percentage = (size_kb / MEMORY_THRESHOLD_KB) * 100
    stats_text = Markdown(f"""
- **Message Count:** {len(messages)} messages
- **Memory Size:** {size_kb:.2f} KB / {MEMORY_THRESHOLD_KB} KB ({percentage:.1f}%)
- **Status:** {'[warning]⚠️ Approaching threshold[/warning]' if size_kb > MEMORY_THRESHOLD_KB * 0.8 else '[success]✓ Healthy[/success]'}
""")
    console.print(Panel(stats_text, title="[bold user]Memory Statistics[/bold user]", border_style="user"))


# -------------------------------------------------------------
# PyQt Viewer Integration
# -------------------------------------------------------------
def show_latest_annotated():
    """Displays the latest annotated image in a PyQt6 window."""
    try:
        from viewer import show_image_simple, show_image_detached
        
        annotated_files = (
            sorted(ANNOTATED_DIR.glob("annotated_*.jpg")) +
            sorted(ANNOTATED_DIR.glob("annotated_*.png")) +
            sorted(ANNOTATED_DIR.glob("annotated_*.jpeg"))
        )

        if not annotated_files:
            console.print("[warning]No annotated images found. Try analyzing one first.[/warning]")
            return

        latest = annotated_files[-1]
        console.print(f"[dim]Opening {latest.name} in viewer...[/dim]")
        
        # Try detached viewer first (most reliable)
        success = show_image_detached(latest)
        
        if success:
            console.print("[success]✅ Viewer launched in separate process![/success]")
            console.print("[dim]Close the viewer window when done.[/dim]")
        else:
            console.print("[warning]⚠️  Could not launch detached viewer. Trying main thread...[/warning]")
            success = show_image_simple(latest)
            
            if success:
                console.print("[success]✅ Image displayed successfully![/success]")
            else:
                console.print("[error]❌ Failed to display image[/error]")

    except ImportError:
        console.print("[error]❌ PyQt6 not available. Install with: pip install PyQt6[/error]")
    except Exception as e:
        console.print(f"[error]❌ Could not display image: {e}[/error]")

# -------------------------------------------------------------
# Main CLI Loop
# -------------------------------------------------------------
def main():
    """Main CLI loop for the Mammography AI Assistant."""
    print_banner()
    console.print("[dim]Type /help for commands, /exit to quit[/dim]\n", justify="center")

    agent = Agent(console)
    messages = load_memory()
    if messages:
        console.print(f"[dim]✓ Loaded {len(messages)} messages from previous session[/dim]\n")

    while True:
        try:
            user_input = Prompt.ask("[bold user]You[/bold user]").strip()
            if not user_input:
                continue

            # --- Slash Commands ---
            if user_input.startswith("/"):
                cmd = user_input.lower()

                if cmd in ["/exit", "/quit"]:
                    console.print("\n[dim]Saving conversation and exiting...[/dim]")
                    save_memory(messages)
                    console.print("[success]Goodbye! 👋[/success]")
                    break

                elif cmd == "/help":
                    print_help()
                    continue

                elif cmd == "/clear":
                    messages = []
                    save_memory(messages)
                    console.print("[success]✓ Conversation cleared[/success]\n")
                    continue

                elif cmd == "/stats":
                    print_stats(messages)
                    continue

                elif cmd in ["/show", "/openannotated"]:
                    show_latest_annotated()
                    continue

                else:
                    console.print(f"[warning]Unknown command:[/warning] {user_input}")
                    continue

            # --- Normal conversation ---
            console.print(Panel(user_input, title="[bold user]👤 You[/bold user]", border_style="user"))
            messages, response = agent.process_message(messages, user_input)
            md = Markdown(response)
            console.print(Panel(md, title="[bold assistant]🤖 Assistant[/bold assistant]", border_style="assistant"))
            console.print()
            save_memory(messages)

        except (KeyboardInterrupt, EOFError):
            console.print("\n\n[dim]Saving conversation...[/dim]")
            save_memory(messages)
            console.print("[success]Goodbye! 👋[/success]")
            break


# -------------------------------------------------------------
# Entry point
# -------------------------------------------------------------
if __name__ == "__main__":
    main()
