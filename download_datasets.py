#!/usr/bin/env python3
import os
import sys
import json
import shutil
import subprocess
import requests
import click


OBJ = {"yes": False}


def arrow(*args, **kwargs):
    print("==>", *args, **kwargs)


def confirm(msg):
    if OBJ["yes"]:
        return True
    return input("==> {}".format(msg)).strip().lower() in ["y", "yes"]


def unknown(key, _, __, ___):
    arrow(f"Unknown action called {key}")


def download(_, target, droot, __):
    url = target["url"]
    fname = target.get("target", url.split("/")[-1])

    r = requests.get(
        url,
        stream=True,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.1 Safari/605.1.15"
        },
    )
    chars = "-\\|/"
    with open(f"{droot}/{fname}", "wb") as f:
        for i, chunk in enumerate(r.iter_content(chunk_size=1024)):
            arrow(f"Downloading... {chars[i%len(chars)]}", end="\r")
            if chunk:
                f.write(chunk)

    if fname.endswith(".zip") or fname.endswith(".tar.gz"):
        arrow(f"Unpacking {fname}...")
        shutil.unpack_archive(f"{droot}/{fname}", droot)


def license(_, target, __, dataset):  # pylint: disable=redefined-builtin
    if target.endswith(".txt"):
        confirm(
            "==> You will now see the license of {dataset}. "
            "Press [q] to exit the pager program. Press [Return]."
        )
        if not OBJ["yes"]:
            subprocess.run(["less", target])
    else:
        print(target)
    if not confirm(
        f"Do you agree with this license for {dataset}? [y/N] "
    ):
        raise PermissionError("Did not agree to license")


def message(_, target, __, dataset):
    arrow(f"Message from {dataset}:")
    print(target)


def cite(_, target, __, dataset):
    arrow(f"If using {dataset}, please cite:\n")
    print(target)


def command(_, target, droot, __):
    subprocess.run(target, cwd=droot, shell=True)


def git(_, target, droot, __):
    if isinstance(target, dict):
        url = target["url"]
        commit = target["commit"]
    else:
        url = target
        commit = None
    shutil.rmtree(droot)
    subprocess.run(["git", "clone", url, droot])
    if commit:
        subprocess.run(["git", "checkout", commit])


handlers = {
    "download": download,
    "license": license,
    "cite": cite,
    "command": command,
    "git": git,
    "message": message,
}


@click.command()
@click.option("--yes", help="Agree to all licenses", is_flag=True)
@click.pass_obj
def main(obj, yes):
    obj["yes"] = yes
    test_requirements()
    with open("sources.json") as f:
        data = json.load(f)
        root = data["_settings"].get("folder", "datasets")
        os.makedirs(root, exist_ok=True)
        for dataset in data:
            if dataset.startswith("_"):
                continue
            actions = data[dataset]
            droot = f"{root}/{dataset}"
            if os.path.exists(droot):
                arrow(f"{dataset} already exists, skipping...")
                continue
            arrow("Working on", dataset)
            os.makedirs(droot, exist_ok=True)
            try:
                for action in actions:
                    key, value = [*action.items()][0]
                    handlers.get(key, unknown)(key, value, droot, dataset)
            except Exception as e:  # pylint: disable=broad-except
                arrow(f"Can't continue on {dataset}, removing...")
                print(e)
                shutil.rmtree(droot, ignore_errors=True)
            if os.path.exists(droot) and not os.listdir(droot):
                shutil.rmtree(droot, ignore_errors=True)
            confirm(f"==> Done with {dataset}, press [Return] to continue...")
            print()
        arrow("All done")


def test_requirements():
    arrow("Testing requirements")
    try:
        subprocess.run(["git", "help"], stdout=subprocess.DEVNULL)
    except FileNotFoundError:
        arrow("Fatal error: Missing git executable.")
        print(
            {
                "darwin": "Install it with: brew install git",
                "linux": "Install it with: sudo apt-get install git",
            }.get(sys.platform, "Consult your administrator on how to install git")
        )
        sys.exit(1)
    try:
        subprocess.run(["less"], stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        arrow("Fatal error: Missing less executable.")
        print(
            "We suggest installing the Windows Subsystem for Linux:",
            "https://docs.microsoft.com/windows/wsl/"
        )
        sys.exit(1)
    arrow("All requirements met.")


if __name__ == "__main__":
    main(obj=OBJ)  # pylint: disable=no-value-for-parameter
