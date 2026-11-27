"""Publish changed Handbal Live files; never delete remote files."""
import ftplib
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import ssl
import subprocess
import sys
import urllib.request

PREFIX = "programmas/handbal-live/"


def git(*args):
    return subprocess.check_output(["git", *args]).decode("utf-8").strip()


def publishable(path):
    p = PurePosixPath(path)
    return (path.startswith(PREFIX) and ".." not in p.parts
            and (p.suffix in {".php", ".html", ".js", ".css"} or p.name == ".htaccess"))


def files_to_publish(event, event_name, manual_files, base_override=""):
    if event_name == "workflow_dispatch":
        requested = [name.strip() for name in manual_files.split(",") if name.strip()]
        if not requested:
            raise ValueError("Geef minstens één bestandsnaam op.")
        paths = []
        for name in requested:
            path = name if name.startswith(PREFIX) else PREFIX + name
            if not publishable(path):
                raise ValueError("Ongeldige bestandsnaam: " + name)
            paths.append(path)
    else:
        base = base_override or event.get("before", "")
        if not base or set(base) == {"0"}:
            raise ValueError("Geen vorige commit; publiceer handmatig met bestandsnamen.")
        raw = subprocess.check_output(
            ["git", "diff", "--name-only", "--diff-filter=ACMRT", "-z",
             base, "HEAD", "--", PREFIX]).decode("utf-8")
        paths = [path for path in raw.split("\0") if publishable(path)]
    result = sorted(set(paths))
    for path in result:
        local = Path(path)
        if not local.is_file() or local.is_symlink():
            raise ValueError("Bestand ontbreekt of is een koppeling: " + path)
    return result


def previous_successful_push():
    """Also publish changes from failed or skipped automatic publications."""
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GH_TOKEN", "")
    if not repo or not token:
        return ""
    url = ("https://api.github.com/repos/" + repo
           + "/actions/workflows/publish-handbal-live.yml/runs"
           + "?branch=main&event=push&status=success&per_page=100")
    request = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urllib.request.urlopen(request, timeout=30) as response:
        runs = json.load(response)["workflow_runs"]
    for run in runs:
        sha = run["head_sha"]
        if str(run["id"]) == os.environ.get("GITHUB_RUN_ID"):
            continue
        if subprocess.run(["git", "merge-base", "--is-ancestor", sha, "HEAD"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            return sha
    return ""


def validate(paths):
    for path in paths:
        if path.endswith(".php"):
            subprocess.run(["php", "-l", path], check=True)
        elif path.endswith(".js"):
            subprocess.run(["node", "--check", path], check=True)
        elif path.endswith(".html"):
            subprocess.run(["node", "-e",
                "const fs=require('fs'),vm=require('vm');"
                "const html=fs.readFileSync(process.argv[1],'utf8');"
                "for(const m of html.matchAll(/<script\\b([^>]*)>([\\s\\S]*?)<\\/script>/gi)){"
                "if(!/\\bsrc\\s*=|\\btype\\s*=\\s*['\\\"](?:module|application\\/)/i.test(m[1]))"
                "new vm.Script(m[2]);}", path], check=True)


def connect():
    password = os.environ.get("FTP_PASSWORD", "")
    if not password:
        raise ValueError("Voeg eerst de repository-secret FTP_PASSWORD toe in GitHub.")
    protocol = os.environ.get("FTP_PROTOCOL", "ftp")
    if protocol not in {"ftp", "ftps"}:
        raise ValueError("FTP_PROTOCOL moet ftp of ftps zijn.")
    client = ftplib.FTP_TLS(context=ssl.create_default_context()) if protocol == "ftps" else ftplib.FTP()
    client.connect(os.environ["FTP_HOST"], int(os.environ.get("FTP_PORT", "21")), timeout=30)
    client.login(os.environ["FTP_USERNAME"], password)
    if protocol == "ftps":
        client.prot_p()
    client.set_pasv(True)
    client.cwd(os.environ["FTP_REMOTE_DIR"])
    index = io.BytesIO()
    client.retrbinary("RETR index.html", index.write)
    content = index.getvalue().lower()
    # Older pages load competitions.php inline; current pages use index.js.
    recognised_version = b"competitions.php" in content or b"index.js" in content
    if b"handbal live" not in content or not recognised_version:
        client.close()
        raise ValueError("De FTP-doelmap bevat niet de verwachte Handbal Live-pagina.")
    return client


def upload(client, paths, run_id):
    for path in paths:
        remote = path[len(PREFIX):]
        name = PurePosixPath(remote)
        temporary = str(name.with_name("." + name.stem + ".upload-" + run_id + name.suffix))
        payload = Path(path).read_bytes()
        client.storbinary("STOR " + temporary, io.BytesIO(payload))
        received = hashlib.sha256()
        client.retrbinary("RETR " + temporary, received.update)
        if received.digest() != hashlib.sha256(payload).digest():
            raise ValueError("Controle van geüpload bestand mislukt: " + remote)
        client.rename(temporary, remote)
        print("Gepubliceerd: " + remote, flush=True)


def main():
    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as handle:
        event = json.load(handle)
    event_name = os.environ["GITHUB_EVENT_NAME"]
    if git("branch", "--show-current") != "main":
        raise ValueError("Publiceren is alleen toegestaan vanaf main.")
    base = previous_successful_push() if event_name == "push" else ""
    paths = files_to_publish(event, event_name, os.environ.get("PUBLISH_FILES", ""), base)
    if not paths:
        print("Geen gewijzigde websitebestanden om te publiceren.")
        return
    validate(paths)
    with connect() as client:
        upload(client, paths, os.environ.get("GITHUB_RUN_ID", "local"))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write("Gepubliceerd naar Handbal-Live:\n\n")
            handle.writelines("- " + path[len(PREFIX):] + "\n" for path in paths)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, ftplib.Error, subprocess.CalledProcessError) as exc:
        print("Publicatie mislukt: " + str(exc), file=sys.stderr)
        sys.exit(1)
