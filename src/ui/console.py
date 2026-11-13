from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.rule import Rule

_console = Console()

_MAX_DOC_LEN = 32  # truncate long filenames in sources


def _short_doc(name: str) -> str:
    stem = name.rsplit(".pdf", 1)[0]
    if len(stem) > _MAX_DOC_LEN:
        stem = stem[:_MAX_DOC_LEN - 1] + "…"
    return stem


def print_startup(mode: str) -> None:
    _console.print(
        Panel(
            f"[bold]Indian Income Tax RAG Assistant[/bold]\n"
            f"[dim]mode: [cyan]{mode}[/cyan]  ·  type [cyan]quit[/cyan] or press Enter to exit[/dim]",
            border_style="cyan",
            padding=(0, 2),
        )
    )


def print_user(question: str) -> None:
    t = Text()
    t.append("You  ▶  ", style="bold cyan")
    t.append(question, style="cyan")
    _console.print(t)


def print_bot(answer: str) -> None:
    _console.print(Panel(answer, title="[bold green]Bot[/bold green]", border_style="green", padding=(0, 1)))


def print_sources(hits: list[dict]) -> None:
    seen: list[str] = []
    for h in hits:
        key = (h["doc"], h["page"])
        if key not in seen:
            seen.append(key)
    if not seen:
        return
    lines = []
    for i, (doc, page) in enumerate(seen):
        connector = "└─" if i == len(seen) - 1 else "├─"
        lines.append(f"  [dim]{connector}[/dim] [bold yellow]{doc}[/bold yellow] [dim]p.{page}[/dim]")
    _console.print("[bold yellow]  Sources[/bold yellow]")
    for line in lines:
        _console.print(line)


def print_timing(embed_ms: float, retrieve_ms: float, context_ms: float, llm_ms: float, total_ms: float) -> None:
    _console.print(
        f"[dim]  ⏱  embed {embed_ms:.0f} ms  retrieve {retrieve_ms:.0f} ms  "
        f"LLM {llm_ms:.0f} ms  total {total_ms:.0f} ms[/dim]"
    )


def print_rule() -> None:
    _console.print(Rule(style="dim"))


def ask_user() -> str:
    return _console.input("[bold cyan]You  ▶  [/bold cyan]")
