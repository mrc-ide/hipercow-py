from dataclasses import dataclass
from pathlib import Path
import subprocess
import re


# def configure():
#     path = Path.cwd()
#     return {
#         "cluster": "wpia-hn",
#         "shares": _cluster_paths(path)
#     }

# @dataclass
# class WindowsPath:
#     local: Path
#     remote: Path
#     drive: str


# # ignoring shares for now
# # mostly hipercow.windows' dide_add_extra_root_share
# def _cluster_paths(path_root, mounts):
#     if mounts is None:
#         mounts = dide_detect_mounts()
    
#     pos = [el for el in path_root.has_parent(el.local)]
#     if len(pos) > 1:
#         msg = "More than one plausible mount for local directory"
#         raise Exception(msg)
#     elif len(pos) == 0:
#         msg = "Can't map local directory '{path_root}' to network path"
#         raise Exception(msg)
#     mount = pos[0]
#     drive = "V:"
#     return WindowsPath(mount.local, mount.remote, drive)


# def dide_detect_mounts():
#     pass


# def dide_detect_mounts_windows():
#     mounts_str = subprocess.run(
#         ["powershell", "-c", "Get-SmbMapping|ConvertTo-CSV"],
#         capture_output=True
#     )
#     # [Mount(l, r) for ]
#     # read as csv, skipping first line, split on commad check sttus




# def dide_detect_mounts_linux():
#     mount_type = "cifs"# or smbfs on mac
#     res = subprocess.run(
#         ["mount", "-t", "cifs"],
#         capture_output=True,
#         check=True
#     )
#     mounts_str = res.stdout.decode("utf-8").trim().splitlines())
#     pat = re.compile("//(?<user>[^@]*@)?(?<host>[^/]*)/(?<path>.*?)\\s+on\\s+(?<local>.+?) (?<extra>.+)$")

#     ret = []
#     for el in res:
#         m = pat.match(el)
#         if m:
#             host, path, local = m.groups()
#             host = re.sub("\\.dide\\.ic\\.ac\\.uk$", "", host)
#             path = path.replace("/", "\\\\")
#             remote = f"\\\\{host}\\{path}"
#             local = clean_path_local(local)
#             ret.append(Mount(remote, local))
