import base64
import datetime
import math
import re
from dataclasses import dataclass
from subprocess import list2cmdline
from urllib.parse import urljoin

import requests
from defusedxml import ElementTree

from hipercow.__about__ import __version__ as hipercow_version
from hipercow.resources import TaskResources
from hipercow.task import TaskStatus


def encode64(x: str) -> str:
    return base64.b64encode(x.encode("utf-8")).decode("utf-8")


def decode64(x: str) -> str:
    return base64.b64decode(x).decode("utf-8")


@dataclass
class Credentials:
    username: str
    password: str


@dataclass
class DideTaskStatus:
    dide_id: str
    name: str
    status: TaskStatus
    resources: str
    user: str
    time_start: float
    time_end: float
    time_submit: float
    template: str

    @staticmethod
    def from_string(entry):
        els = entry.strip().split("\t")
        els[2] = _parse_dide_status(els[2])
        els[4] = els[4].replace("DIDE\\", "")
        for i in range(5, 8):
            els[i] = _parse_dide_timestamp(els[i])
        return DideTaskStatus(*els)


class DideHTTPClient(requests.Session):
    _has_logged_in = False
    _credentials: Credentials

    def __init__(self, credentials: Credentials):
        super().__init__()
        self._credentials = credentials

    def request(self, method, path, *args, public=False, **kwargs):
        if not public and not self._has_logged_in:
            self.login()
        base_url = "https://mrcdata.dide.ic.ac.uk/hpc/"
        url = urljoin(base_url, path)
        headers = {"Accept": "text/plain"} if method == "POST" else {}
        response = super().request(
            method, url, *args, headers=headers, **kwargs
        )
        # To debug requests, you can do:
        # from requests_toolbelt.utils import dump
        # print(dump.dump_all(response).decode("utf-8"))
        response.raise_for_status()
        return response

    def login(self) -> None:
        data = {
            "us": encode64(self._credentials.username),
            "pw": encode64(self._credentials.password),
            "hpcfunc": encode64("login"),
        }
        res = self.request("POST", "index.php", data=data, public=True)
        no_access = "You don't seem to have any HPC access"
        if no_access in res.text:
            msg = "You do not have HPC access - please contact Wes"
            raise Exception(msg)
        self._has_logged_in = True

    def logout(self) -> None:
        self.request("GET", "logout.php", public=True)
        self._has_logged_in = False

    def username(self) -> str:
        return self._credentials.username

    def logged_in(self) -> bool:
        return self._has_logged_in


class DideWebClient:
    def __init__(self, credentials):
        self._client = DideHTTPClient(credentials)
        self._cluster = "wpia-hn"

    def login(self):
        self._client.login()

    def logout(self):
        self._client.logout()

    def headnodes(self) -> list[str]:
        data = {"user": encode64("")}
        response = self._client.request("POST", "_listheadnodes.php", data=data)
        return _client_parse_headnodes(response.text)

    def check_access(self) -> None:
        _client_check_access(self._cluster, self.headnodes())

    def logged_in(self) -> bool:
        return self._client.logged_in()

    def submit(
        self,
        path: str,
        name: str,
        resources: TaskResources,
        *,
        workdir: str | None = None,
    ) -> str:
        data = _client_body_submit(
            path, name, self._cluster, resources=resources, workdir=workdir
        )
        response = self._client.request("POST", "submit_1.php", data=data)
        return _client_parse_submit(response.text)

    def cancel(self, dide_id: str) -> bool:
        data = _client_body_cancel(dide_id, self._cluster)
        response = self._client.request("POST", "cancel.php", data=data)
        return _client_parse_cancel(response.text)

    def log(self, dide_id: str) -> str:
        data = _client_body_log(dide_id, self._cluster)
        response = self._client.request("POST", "showjobfail.php", data=data)
        return _client_parse_log(response.text)

    def status_user(self, state="*") -> list[DideTaskStatus]:
        data = _client_body_status_user(
            state, self._client.username(), self._cluster
        )
        response = self._client.request("POST", "_listalljobs.php", data=data)
        return _client_parse_status_user(response.text)

    def status_job(self, dide_id: str) -> TaskStatus:
        query = _client_query_status_job(dide_id, self._cluster)
        response = self._client.request("GET", "api/v1/get_job_status/", query)
        return _client_parse_status_job(response.text)

    def software(self):
        response = self._client.request(
            "GET", "api/v1/cluster_software", public=True
        )
        return _client_parse_software(response.json())


def check_access(credentials: Credentials) -> None:
    try:
        DideWebClient(credentials).check_access()
    except Exception as e:
        msg = "login failed"
        raise Exception(msg) from e


def _client_check_access(cluster: str, valid: list[str]) -> None:
    if cluster in valid:
        return
    if len(valid) == 0:
        msg = "You do not have access to any cluster"
    elif len(valid) == 1:
        msg = f"You do not have access to '{cluster}'; try '{valid[0]}'"
    else:
        valid_str = ", ".join(valid)
        msg = f"You do not have access to '{cluster}'; try one of {valid_str}"
    raise Exception(msg)


def _client_body_submit(
    path: str,
    name: str,
    cluster: str,
    *,
    resources: TaskResources,
    workdir: str | None,
) -> dict:
    # The str here keeps mypy happy, this will be a string by this
    # point.
    template = str(resources.queue)
    if template == "LinuxNodes":
        job_to_run = _call_quote_batch_path(path, "bash")
    else:
        job_to_run = _call_quote_batch_path(path, "call")
    data = {
        "cluster": encode64(cluster),
        "template": encode64(template),
        "jn": encode64(name or ""),  # job name
        "wd": encode64(workdir or ""),  # work dir
        "se": encode64(""),  # stderr
        "so": encode64(""),  # stdout
        "jobs": encode64(job_to_run),
        "dep": encode64(""),  # dependencies, eventually
        "hpcfunc": "submit",
        "ver": encode64(f"hipercow-py/{hipercow_version}"),
    }

    if resources.cores == math.inf:
        data["rc"] = encode64("1")
        data["rt"] = encode64("Nodes")
    else:
        data["rc"] = encode64(str(resources.cores))
        data["rt"] = encode64("Cores")

    if resources.exclusive:
        data["exc"] = encode64("1")

    if resources.memory_per_task is not None:
        data["epm"] = encode64(str(1000 * resources.memory_per_task))

    if resources.memory_per_node is not None:
        data["mpn"] = encode64(str(1000 * resources.memory_per_node))

    if resources.max_runtime is not None:
        data["rnt"] = encode64(str(resources.max_runtime))

    # Still missing:
    #
    # hold until (hu)
    # requested nodes (rn)
    # priority (pri)
    return data


def _client_body_cancel(dide_id: str | list[str], cluster: str) -> dict:
    if isinstance(dide_id, str):
        dide_id = [dide_id]
    return {
        "cluster": encode64(cluster),
        "hpcfunc": encode64("cancel"),
        **{"c" + i: i for i in dide_id},
    }


def _client_body_log(dide_id: str, cluster: str) -> dict:
    return {"cluster": encode64(cluster), "hpcfunc": "showfail", "id": dide_id}


def _client_body_status_user(state: str, username: str, cluster: str) -> dict:
    return {
        "user": encode64(username),
        "scheduler": encode64(cluster),
        "state": encode64(state),
        "jobs": encode64("-1"),
    }


def _client_query_status_job(dide_id: str, cluster: str) -> dict:
    return {"scheduler": cluster, "jobid": dide_id}


def _client_parse_headnodes(txt: str) -> list[str]:
    txt = txt.strip()
    return txt.split("\n") if txt else []


def _client_parse_submit(txt: str) -> str:
    m = re.match("^Job has been submitted. ID: +([0-9]+)\\.$", txt.strip())
    if not m:
        msg = "Job submission has failed; could be a login error"
        raise Exception(msg)
    return m.group(1)


def _client_parse_cancel(txt: str):
    return dict([x.split("\t") for x in txt.strip().split("\n")])


def _client_parse_log(txt: str) -> str:
    res = ElementTree.fromstring(txt).find('.//input[@id="res"]')
    assert res is not None  # noqa: S101
    output = decode64(res.attrib["value"])
    return re.sub("^Output\\s*:\\s*?\n+", "", output)


def _client_parse_status_user(txt: str) -> list[DideTaskStatus]:
    return [DideTaskStatus.from_string(x) for x in txt.strip().split("\n")]


def _client_parse_status_job(txt: str) -> TaskStatus:
    return _parse_dide_status(txt.strip())


def _client_parse_software(json: dict) -> dict:
    # Likely to change soon when the portal updates
    linux = json["linuxsoftware"]
    windows = json["software"]

    def process(x):
        ret = {}
        for el in x:
            name = el["name"].lower()
            version = el["version"]
            omit = {"name", "version"}
            value = {k: v for k, v in el.items() if k not in omit}
            if name not in ret:
                ret[name] = {}
            ret[name][version] = value
        return ret

    return {"linux": process(linux), "windows": process(windows)}


def _parse_dide_status(status: str) -> TaskStatus:
    remap = {
        "Running": TaskStatus.RUNNING,
        "Finished": TaskStatus.SUCCESS,
        "Queued": TaskStatus.SUBMITTED,
        "Failed": TaskStatus.FAILURE,
        "Canceled": TaskStatus.CANCELLED,
        "Cancelled": TaskStatus.CANCELLED,
    }
    return remap[status]


def _parse_dide_timestamp(time: str) -> datetime.datetime:
    return datetime.datetime.strptime(time, "%Y%m%d%H%M%S").astimezone(
        datetime.timezone.utc
    )


def _call_quote_batch_path(path: str, prefix: str) -> str:
    # NOTE: list2cmdline is undocumented but needed.
    # not documented https://github.com/conan-io/conan/pull/11553/
    return f"{prefix} {list2cmdline([path])}"
