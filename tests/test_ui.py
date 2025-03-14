from unittest import mock

from hipercow import ui


def test_can_build_ui_styles(mocker):
    mocker.patch("hipercow.ui.console")

    ui.alert_danger("oh no")
    assert ui.console.print.call_count == 1
    assert ui.console.print.mock_calls[0] == mock.call(
        "[bold red]:heavy_multiplication_x:[/bold red] oh no"
    )

    ui.alert_success("yaaassss.", indent=2)
    assert ui.console.print.call_count == 2
    assert ui.console.print.mock_calls[1] == mock.call(
        "  [bold green]:heavy_check_mark:[/bold green] yaaassss."
    )

    ui.alert_warning("check it before you wreck it")
    assert ui.console.print.call_count == 3
    assert ui.console.print.mock_calls[2] == mock.call(
        "[bold orange]![/bold orange] check it before you wreck it"
    )

    ui.alert_info("here it is")
    assert ui.console.print.call_count == 4
    assert ui.console.print.mock_calls[3] == mock.call(
        "[bold cyan]i[/bold cyan] here it is"
    )

    ui.alert_see_also("this doc")
    assert ui.console.print.call_count == 5
    assert ui.console.print.mock_calls[4] == mock.call(
        ":books: For more information, see this doc"
    )

    ui.alert_arrow("hello")
    assert ui.console.print.call_count == 6
    assert ui.console.print.mock_calls[5] == mock.call(
        "[bold yellow]:arrow_forward:[/bold yellow] hello"
    )
