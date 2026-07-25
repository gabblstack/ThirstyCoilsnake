from coilsnake.util.common import project
# In case the file was not properly generated or bundled...
try:
    from coilsnake.ui.git_commit import GIT_COMMIT
except:
    GIT_COMMIT = None

VERSION = project.VERSION_NAMES[project.FORMAT_VERSION]
if GIT_COMMIT:
    VERSION = f"{VERSION}-next-{GIT_COMMIT}"
RELEASE_DATE = "July 25, 2026"

WEBSITE = "http://pk-hack.github.io/CoilSnake"
AUTHOR = "the PK Hack community. (Forked from CoilSnake 4.2)"
ADDITIONAL_CREDITS = """- Some portions based on JHack, created by AnyoneEB
- Contributions by H.S, Michael1, John Soklaski,
  João Silva, ShadowOne333, stochaztic, Catador,
  cooprocks123e, and many others"""
DEPENDENCIES = [
    {"name": "Thirsty CoilSnake logo and icon",
     "author": "Rydel & Gabbi"},
    {"name": "Thirsty CoilSnake 1 logo",
     "author": "livvy94 and Gabbi"},
    {"name": "CCScript",
     "author": "Mr. Accident",
     "url": "http://starmen.net/pkhack/ccscript"},
    {"name": "CCScriptWriter",
     "author": "Lyrositor",
     "url": "https://github.com/Lyrositor/CCScriptWriter"},
    {"name": "EBYAML",
     "author": "Penguin",
     "url": "https://github.com/PKHackers/EBYAML"},
    {"name": "exhal Compression Library",
     "author": "Devin Acker",
     "url": "https://github.com/devinacker/exhal"},
    {"name": "EB++",
     "author": "Rufus",
     "url": "http://goo.gl/BnNqUM"}
]


def coilsnake_about():
    description = f"""Thirsty CoilSnake {VERSION} - {WEBSITE}
Created by {AUTHOR}
Released on {RELEASE_DATE}
"""

    for dependency in DEPENDENCIES:
        description += "\n- " + dependency["name"]
        if "author" in dependency:
            description += " created by {}".format(dependency["author"])
        if "url" in dependency:
            description += "\n  {}".format(dependency["url"])

    description += "\n" + ADDITIONAL_CREDITS
    return description
