import datetime
import json
import math

import pytest
import responses

from hipercow.__about__ import __version__ as hipercow_version
from hipercow.dide import web
from hipercow.resources import TaskResources
from hipercow.task import TaskStatus


def create_client(*, logged_in=True):
    cl = web.DideWebClient(web.Credentials("", ""))
    if logged_in:
        cl._client._has_logged_in = True
    return cl


@responses.activate
def test_list_headnodes():
    ## https://stackoverflow.com/questions/40361308/create-a-functioning-response-object
    listheadnodes = responses.add(
        responses.POST,
        "https://mrcdata.dide.ic.ac.uk/hpc/_listheadnodes.php",
        body="foo\nbar\n",
        status=200,
    )
    cl = create_client()
    res = cl.headnodes()
    assert res == ["foo", "bar"]

    assert listheadnodes.call_count == 1
    req = listheadnodes.calls[0].request
    assert req.headers["Content-Type"] == "application/x-www-form-urlencoded"
    assert req.body == "user="


def test_can_parse_headnodes_responses():
    assert web._client_parse_headnodes("") == []
    assert web._client_parse_headnodes("foo\n") == ["foo"]
    assert web._client_parse_headnodes("foo\nbar\n") == ["foo", "bar"]


@responses.activate
def test_can_get_task_log():
    payload = '<html><head></head><body onload="document.fsub.submit();"><form name="fsub" id="fsub" action="result.php" method="post"><input type="hidden" id="title" name="title" value="Sm9iIDQ4OTg1MSBGYWlsdXJlIFN0YXR1cw=="/><input type="hidden" id="res" name="res" value="bG9nIGNvbnRlbnRzIQ=="/></form></body></html>\n'  # noqa: E501
    getlog = responses.add(
        responses.POST,
        "https://mrcdata.dide.ic.ac.uk/hpc/showjobfail.php",
        body=payload,
        status=200,
    )
    cl = create_client()
    res = cl.log("1234")
    assert res == "log contents!"

    assert getlog.call_count == 1
    req = getlog.calls[0].request
    assert req.body == "cluster=d3BpYS1obg%3D%3D&hpcfunc=showfail&id=1234"


@responses.activate
def test_can_get_status_for_user():
    payload = """493420	hipercow-py-test	Finished	1 core	DIDE\\rfitzjoh	20250129120445	20250129120445	20250129120446	AllNodes
489851		Failed	1 core	DIDE\\rfitzjoh	20250127160545	20250127160545	20250127160545	LinuxNodes
489823		Finished	1 core	DIDE\\rfitzjoh	20250127160453	20250127160453	20250127160454	LinuxNodes
"""  # noqa: E501
    status = responses.add(
        responses.POST,
        "https://mrcdata.dide.ic.ac.uk/hpc/_listalljobs.php",
        body=payload,
        status=200,
    )
    cl = create_client()
    res = cl.status_user()
    assert len(res) == 3
    assert res[0] == web.DideTaskStatus(
        "493420",
        "hipercow-py-test",
        TaskStatus.SUCCESS,
        "1 core",
        "rfitzjoh",
        datetime.datetime(2025, 1, 29, 12, 4, 45, tzinfo=datetime.timezone.utc),
        datetime.datetime(2025, 1, 29, 12, 4, 45, tzinfo=datetime.timezone.utc),
        datetime.datetime(2025, 1, 29, 12, 4, 46, tzinfo=datetime.timezone.utc),
        "AllNodes",
    )

    assert status.call_count == 1
    req = status.calls[0].request
    assert (
        req.body
        == "user=&scheduler=d3BpYS1obg%3D%3D&state=Kg%3D%3D&jobs=LTE%3D"
    )


@responses.activate
def test_can_get_job_status():
    status = responses.add(
        responses.GET,
        "https://mrcdata.dide.ic.ac.uk/hpc/api/v1/get_job_status/",
        body="Failed",
        status=200,
    )
    cl = create_client()
    res = cl.status_job("1234")
    assert res == TaskStatus.FAILURE
    assert status.call_count == 1


@responses.activate
def test_can_get_software_list():
    payload = {
        "software": [
            {"name": "R", "version": "4.2.3", "call": "setr64_4_2_3.bat"},
            {"name": "R", "version": "4.3.1", "call": "setr64_4_3_1.bat"},
            {"name": "python", "version": "3.11", "call": "python311.bat"},
        ],
        "linuxsoftware": [
            {"name": "R", "version": "4.2.1", "module": "r/4.2.1"},
            {"name": "python", "version": "3.12", "module": "python/3.12"},
        ],
    }
    software = responses.add(
        responses.GET,
        "https://mrcdata.dide.ic.ac.uk/hpc/api/v1/cluster_software",
        body=json.dumps(payload),
        status=200,
    )
    cl = create_client(logged_in=False)
    res = cl.software()
    assert res == {
        "linux": {
            "r": {"4.2.1": {"module": "r/4.2.1"}},
            "python": {"3.12": {"module": "python/3.12"}},
        },
        "windows": {
            "r": {
                "4.2.3": {"call": "setr64_4_2_3.bat"},
                "4.3.1": {"call": "setr64_4_3_1.bat"},
            },
            "python": {"3.11": {"call": "python311.bat"}},
        },
    }
    assert software.call_count == 1


@responses.activate
def test_can_submit_task():
    submit = responses.add(
        responses.POST,
        "https://mrcdata.dide.ic.ac.uk/hpc/submit_1.php",
        body="Job has been submitted. ID: 497979.\n",
        status=200,
    )
    cl = create_client()
    resources = TaskResources(queue="AllNodes")
    res = cl.submit("1234", "myname", resources)
    assert res == "497979"
    assert submit.call_count == 1


@responses.activate
def test_can_cancel_task():
    cancel = responses.add(
        responses.POST,
        "https://mrcdata.dide.ic.ac.uk/hpc/cancel.php",
        body="497979\tWRONG_USER.\n",
        status=200,
    )
    cl = create_client()
    res = cl.cancel("497979")
    assert res == {"497979": "WRONG_USER."}
    assert cancel.call_count == 1


def test_can_check_access():
    with pytest.raises(Exception, match="You do not have access to any"):
        web._client_check_access("wpia-hn", [])
    with pytest.raises(Exception, match="You do not have access to 'wpia-hn'"):
        web._client_check_access("wpia-hn", ["other"])
    with pytest.raises(Exception, match="try one of a, b"):
        web._client_check_access("wpia-hn", ["a", "b"])
    assert web._client_check_access("a", ["a"]) is None
    assert web._client_check_access("a", ["a", "b"]) is None


def test_throw_if_parse_on_submit_fails():
    with pytest.raises(Exception, match="Job submission has failed"):
        web._client_parse_submit("")


def test_wrap_ids_as_list_for_cancel():
    base = {"cluster": web.encode64("cl"), "hpcfunc": web.encode64("cancel")}
    assert web._client_body_cancel("1", "cl") == {"c1": "1", **base}
    assert web._client_body_cancel(["1"], "cl") == {"c1": "1", **base}
    assert web._client_body_cancel(["1", "2"], "cl") == {
        "c1": "1",
        "c2": "2",
        **base,
    }


def test_can_check_if_we_are_logged_in_from_web_client():
    cl = create_client()
    assert cl.logged_in()
    cl = create_client(logged_in=False)
    assert not cl.logged_in()


@responses.activate
def test_can_check_if_we_have_access():
    responses.add(
        responses.POST,
        "https://mrcdata.dide.ic.ac.uk/hpc/_listheadnodes.php",
        body="wpia-hn\n",
        status=200,
    )
    cl = create_client()
    assert cl.check_access() is None


@responses.activate
def test_can_log_in_and_out():
    login = responses.add(
        responses.POST,
        "https://mrcdata.dide.ic.ac.uk/hpc/index.php",
        body="",
        status=200,
    )
    logout = responses.add(
        responses.GET,
        "https://mrcdata.dide.ic.ac.uk/hpc/logout.php",
        status=200,
    )
    cl = create_client(logged_in=False)
    cl.login()
    assert login.call_count == 1
    assert cl.logged_in()
    cl.logout()
    assert login.call_count == 1
    assert logout.call_count == 1
    assert not cl.logged_in()


@responses.activate
def test_throw_if_user_has_no_access():
    body = "<html>You don't seem to have any HPC access</html>"
    responses.add(
        responses.POST,
        "https://mrcdata.dide.ic.ac.uk/hpc/index.php",
        body=body,
        status=200,
    )
    cl = create_client(logged_in=False)
    with pytest.raises(Exception, match="You do not have HPC access"):
        cl.login()


@responses.activate
def test_login_if_using_authenticated_endpoints():
    login = responses.add(
        responses.POST,
        "https://mrcdata.dide.ic.ac.uk/hpc/index.php",
        body="",
        status=200,
    )
    responses.add(
        responses.POST,
        "https://mrcdata.dide.ic.ac.uk/hpc/_listheadnodes.php",
        body="foo\nbar\n",
        status=200,
    )
    cl = create_client(logged_in=False)
    assert cl.headnodes() == ["foo", "bar"]
    assert login.call_count == 1
    assert cl.logged_in()


def test_raise_if_no_access(mocker):
    mocker.patch("hipercow.dide.web.DideWebClient.__init__", return_value=None)
    mocker.patch(
        "hipercow.dide.web.DideWebClient.check_access",
        side_effect=Exception("some error"),
    )
    with pytest.raises(Exception, match="login failed"):
        web.check_access(web.Credentials("a", "b"))


def test_no_error_if_access_is_ok(mocker):
    mocker.patch("hipercow.dide.web.DideWebClient.__init__", return_value=None)
    mocker.patch("hipercow.dide.web.DideWebClient.check_access")
    web.check_access(web.Credentials("a", "b"))


def test_create_basic_submit_data():
    path = r"\\server\share\script.bat"
    resources = TaskResources(queue="AllNodes")
    data = web._client_body_submit(
        path, "job", "windows", resources=resources, workdir=None
    )
    assert data == {
        "cluster": web.encode64("windows"),
        "template": web.encode64("AllNodes"),
        "jn": web.encode64("job"),
        "wd": web.encode64(""),
        "se": web.encode64(""),
        "so": web.encode64(""),
        "jobs": web.encode64(web._call_quote_batch_path(path, "call")),
        "dep": web.encode64(""),
        "hpcfunc": "submit",
        "ver": web.encode64(f"hipercow-py/{hipercow_version}"),
        "rc": web.encode64("1"),
        "rt": web.encode64("Cores"),
    }


def test_can_set_template():
    path = r"\\server\share\script.bat"
    r = TaskResources(queue="BuildQueue")
    r_cmp = TaskResources(queue="AllNodes")
    data = web._client_body_submit(
        path, "job", "windows", resources=r, workdir=None
    )
    data_cmp = web._client_body_submit(
        path, "job", "windows", resources=r_cmp, workdir=None
    )
    assert data == data_cmp | {"template": web.encode64("BuildQueue")}


def test_can_set_resources():
    def build(**kwargs):
        path = r"\\server\share\script.bat"
        resources = TaskResources(queue="AllNodes", **kwargs)
        return web._client_body_submit(
            path, "job", "windows", resources=resources, workdir=None
        )

    default = build()
    assert build(cores=2) == default | {"rc": web.encode64("2")}
    assert build(cores=math.inf) == default | {
        "rc": web.encode64("1"),
        "rt": web.encode64("Nodes"),
    }
    assert build(exclusive=True) == default | {"exc": web.encode64("1")}
    assert build(max_runtime=1000) == default | {"rnt": web.encode64("1000")}
    assert build(memory_per_node=1) == default | {"mpn": web.encode64("1000")}
    assert build(memory_per_task=2) == default | {"epm": web.encode64("2000")}


def test_can_set_workdir():
    path = r"\\server\share\script.bat"
    workdir = r"r\\server\share\some\path"
    resources = TaskResources(queue="AllNodes")
    data = web._client_body_submit(
        path, "job", "windows", resources=resources, workdir=workdir
    )
    data_cmp = web._client_body_submit(
        path, "job", "windows", resources=resources, workdir=None
    )
    assert data == data_cmp | {"wd": web.encode64(workdir)}
