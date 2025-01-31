import datetime
import json

import responses

from hipercow.dide import web
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
    res = cl.submit("1234", "myname")
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
