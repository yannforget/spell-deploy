"""Deployment script."""

import os
import sys
import shutil
from subprocess import run
from pathlib import Path
import configparser
from fetch_zotero import fetch_zotero


def get_config(path):
    """Parse configuration file."""
    path = os.path.dirname(os.path.realpath(__file__))
    config_file = os.path.join(path, "deploy.conf")
    config = configparser.ConfigParser()
    config.read(config_file)
    return config


def already_running(cache_dir):
    """Check if another instance of the script is running."""
    return os.path.isfile(os.path.join(cache_dir, "deploy.lock"))


def lock(cache_dir):
    """Forbid another instance of the script to run."""
    Path(os.path.join(cache_dir, "deploy.lock")).touch()


def unlock(cache_dir):
    """Allow another instance of the script to run."""
    os.remove(os.path.join(cache_dir, "deploy.lock"))


def log(message):
    """Log message."""
    with open("log/current.log", "w") as txt:
        txt.write("\n{}".format(message))


def pull(local_repository):
    """Pull changes from Github."""
    os.chdir(local_repository)
    run(["git", "pull"])


def update_publications(repository, collection_id_lab, collection_id_external,
                        library_id, api_key):
    """Fetch all publications from Zotero."""
    if os.path.isfile("log/current.log"):
        os.remove("log/current.log")
    # Delete old publications content
    publications_dir = os.path.join(
        repository, "content", "publication")
    log("Removing old files...")
    shutil.rmtree(publications_dir)
    os.makedirs(publications_dir)

    # Fetch publications from Zotero
    log("Fetching lab publications...")
    fetch_zotero(
        api_key, library_id, collection_id_lab,
        publications_dir, lab_publication=True)
    log("Fetching team publications...")
    fetch_zotero(
        api_key, library_id, collection_id_external,
        publications_dir, lab_publication=False)
    log("Done.")


def build(repository):
    """Rebuild static website with Hugo."""
    public_dir = os.path.join(repository, "public")
    shutil.rmtree(public_dir)
    os.makedirs(public_dir)
    os.chdir(repository)
    run(["hugo"])


def add_slash(path):
    """Add a slash to the end of the path."""
    if path[-1] != "/":
        path += "/"
    return path


def generate_lftp(sftp_server, sftp_user, sftp_password, sftp_path,
                  local_dir, cache_dir):
    """Generate custom LFTP script file."""
    script_path = os.path.join(cache_dir, "deploy.lftp")
    if os.path.isfile(script_path):
        os.remove(script_path)

    dirs_to_del = [
        "about", "css", "fonts", "images", "js", "logo",
        "news", "page", "person", "project", "publication",
        "subject"]
    files_to_del = [
        "index.html", "index.xml", "sitemap.xml"]

    if sftp_path[-1] == "/":
        sftp_path = sftp_path[:-1]

    with open(script_path, "w") as lftp:
        lftp.write("open -u {} --env-password -p 22 sftp://{}{}".format(
            sftp_user, sftp_server, sftp_path))
        lftp.write("\nmkdir -p -f {}".format(sftp_path))
        lftp.write("\ncd {}".format(sftp_path))
        for directory in dirs_to_del:
            lftp.write("\nrm -r {}".format(directory))
        for file in files_to_del:
            lftp.write("\nrm {}".format(file))
        lftp.write("\ncd ..")
        lftp.write("\nmirror -R {} {}".format(local_dir, sftp_path))


def update(sftp_server, sftp_user, sftp_password, sftp_path,
           local_dir, cache_dir):
    """Update remote website.
    Remove old files and copy new website.
    """
    public_dir = os.path.join(local_dir, "public")
    generate_lftp(sftp_server, sftp_user, sftp_password, sftp_path,
                  public_dir, cache_dir)

    os.chdir(cache_dir)
    run(["lftp", "-f", "deploy.lftp"],
        env={"LFTP_PASSWORD": sftp_password})


def deploy():
    """Pull changes from Github, rebuild the website and deploy the new files."""
    path = os.path.dirname(os.path.realpath(__file__))

    if os.path.isfile("log/current.log"):
        os.remove("log/current.log")
    log("Parsing configuration parameters...")

    config = get_config(path)

    cache_dir = config.get("Local", "cache_directory")
    repository = config.get("Local", "spell_repository")

    sftp_server = config.get("SFTP", "server")
    sftp_user = config.get("SFTP", "username")
    sftp_password = config.get("SFTP", "password")
    sftp_path = config.get("SFTP", "path")

    log("SFTP server: %s" % sftp_server)
    log("SFTP user: %s" % sftp_server)
    log("SFTP path: %s" % sftp_path)

    # Exit if another instance of the script is running
    if already_running(cache_dir):
        log("Another instance of the script is already running. Exiting...")
        sys.exit()

    lock(cache_dir)
    log("Pulling changes from Github...")
    pull(repository)
    log("Rebuilding website...")
    build(repository)
    log("Uploading files...")
    update(sftp_server, sftp_user, sftp_password, sftp_path,
           repository, cache_dir)
    unlock(cache_dir)

    log("Done.")
    sys.exit()

def fetch_publications():
    """Fetch publications from Zotero and update website content locally."""
    # Get path of the deployment script directory
    path = os.path.dirname(os.path.realpath(__file__))
    if os.path.isfile("log/current.log"):
        os.remove("log/current.log")

    config = get_config(path)

    repository = config.get("Local", "spell_repository")
    cache_dir = config.get("Local", "cache_directory")

    collection_id_lab = config.get("Zotero", "collection_id_lab")
    collection_id_external = config.get("Zotero", "collection_id_external")
    api_key = config.get("Zotero", "api_key")
    library_id = config.get("Zotero", "library_id")

    # Exit if another instance of the script is running
    if already_running(cache_dir):
        sys.exit()

    lock(cache_dir)
    update_publications(
        repository, collection_id_lab, collection_id_external, library_id, api_key)
    unlock(cache_dir)

    sys.exit()

if __name__ == "__main__":
    if sys.argv[1] in ["-u", "--update"]:
        deploy()
    elif sys.argv[1] in ["-z", "--zotero"]:
        fetch_publications()
    elif sys.argv[1] in ["-h", "--help"]:
        print("-u, --update: Deploy website."
              "\n-z, --zotero: Update publications locally.")
    else:
        print("Missing option.")
