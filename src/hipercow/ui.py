"""Some quality of life printing utilities, ported from R's cli."""

from rich.console import Console

console = Console()


def h1(text: str) -> None:
    before = "─" * 3
    after = "─" * (max(console.width - len(before) - 3 - len(text), 0))
    console.print(
        f"[cyan]{before}[/cyan] [bold]{text}[/bold] [cyan]{after}[/cyan]"
    )


def text(text: str, **kwargs) -> None:
    console.print(text, **kwargs)


def logs(title: str, text: str | None, *, indent: int = 0) -> None:
    indent_str = " " * indent
    alert_arrow(title, indent=indent)
    if text is None:
        console.print(f"{indent_str}(no logs found)", style="dim")
    else:
        console.rule(style="dim")
        console.print(text, emoji=False, markup=False, crop=False)
        console.rule(style="dim")


def li(text: str, indent: int = 0, symbol: str = "*", title: str = ""):
    indent_str = " " * indent
    title = f"[bold]{title}[/bold] " if title else ""
    console.print(f"{indent_str}{symbol} {title}{text}")


def blank_line(n: int = 1) -> None:
    console.print("\n" * (n - 1))


def alert_danger(text: str, indent: int = 0) -> None:
    alert(":heavy_multiplication_x:", text, "bold red", indent=indent)


def alert_success(text: str, indent: int = 0) -> None:
    alert(":heavy_check_mark:", text, "bold green", indent=indent)


def alert_warning(text: str, indent: int = 0) -> None:
    alert("!", text, "bold orange", indent=indent)


def alert_info(text: str, indent: int = 0) -> None:
    alert("i", text, "bold cyan", indent=indent)


def alert_see_also(
    text: str, prefix: str = "For more information, see ", indent: int = 0
) -> None:
    alert(":books:", f"{prefix}{text}", indent=indent)


def alert_arrow(text: str, indent: int = 0) -> None:
    alert(":arrow_forward:", text, "bold yellow", indent=indent)


def alert(
    icon: str, text: str, style: str | None = None, indent: int = 0
) -> None:
    indent_str = " " * indent
    if style:
        console.print(f"{indent_str}[{style}]{icon}[/{style}] {text}")
    else:
        console.print(f"{indent_str}{icon} {text}")
