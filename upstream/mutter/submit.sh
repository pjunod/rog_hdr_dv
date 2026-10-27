#!/bin/sh
# Submit Mutter units to gitlab.gnome.org/GNOME/mutter.
# Usage: submit.sh 00            open the design-discussion issue (do this first)
#        submit.sh <NN|all> [--dry-run] [--draft] [--link URL|mr]   (details: README.md)
# "Link: TBD-MR" lines become the unit's own MR URL for standalone units and the
# design-discussion issue's URL for stacked ones, unless --link says otherwise.
PROJECT_DIR=$(cd "$(dirname "$0")" && pwd)
GL_HOST=gitlab.gnome.org
GL_UPSTREAM=GNOME/mutter
GL_TARGET=main
BRANCH_PREFIX=hdr-
LINK_POLICY=tbd
SERIES_ISSUE_FILE=$HOME/.config/upstream/gnome-mutter-series-issue
. "$PROJECT_DIR/../lib/gitlab-submit.sh"
