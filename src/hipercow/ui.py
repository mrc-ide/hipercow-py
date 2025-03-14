"""Some quality of life printing utilities, ported from R's cli."""

from rich.console import Console

console = Console()


# for h1/h2 we can use "Rule" I think
# https://rich.readthedocs.io/en/latest/console.html#rules
#
# Nested lists are harder, but bullets won't be that hard to get
# sorted.
#
# Pluralisation is the other thing we might want.


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
