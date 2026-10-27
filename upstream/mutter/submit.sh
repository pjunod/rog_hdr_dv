#!/bin/sh
# Submit Mutter units to gitlab.gnome.org/GNOME/mutter.
# Usage: submit.sh <NN|all> [--dry-run] [--draft] [--link URL|mr]   (details: README.md)
# Commits carry "Link: TBD-MR"; the script refuses to run until --link says
# what replaces it (the design-discussion issue's URL, or "mr" for the MR's own).
PROJECT_DIR=$(cd "$(dirname "$0")" && pwd)
GL_HOST=gitlab.gnome.org
GL_UPSTREAM=GNOME/mutter
GL_TARGET=main
BRANCH_PREFIX=hdr-
LINK_POLICY=tbd
. "$PROJECT_DIR/../lib/gitlab-submit.sh"
