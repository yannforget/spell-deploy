#!/usr/bin/env python3

import os
from pathlib import Path
from time import sleep
from flask import Flask, render_template, request, Response, redirect, url_for
from concurrent.futures import ThreadPoolExecutor

import deploy

executor = ThreadPoolExecutor(2)
app = Flask(__name__)
config = deploy.get_config("deploy.conf")


def locked():
    """Check if the app is locked (already running)."""
    cache_dir = config.get("Local", "cache_directory")
    lock_file = os.path.join(cache_dir, "deploy.lock")
    return os.path.isfile(lock_file)


@app.route("/")
def index():
    return render_template("index.html", locked=locked())


@app.route("/push")
def push():
    executor.submit(deploy.deploy())


@app.route("/zotero")
def zotero():
    executor.submit(deploy.fetch_publications())


@app.route("/testing")
def testing():
    print("Running...")
    lock_file = "cache/testing.lock"
    lock = Path(lock_file)
    lock.touch()
    sleep(3)
    print("Done.")


@app.route("/_log")
def log():
    if os.path.isfile("log/current.log"):
        with open("log/current.log") as log:
            lines = [line for line in log.readlines()]
            return "<br>".join(lines)
    else:
        return ""


if __name__ == "__main__":
    app.run(host="localhost", port=8080, debug=True, threaded=True)





