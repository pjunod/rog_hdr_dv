#!/bin/sh
# Submit GTK units to gitlab.gnome.org/GNOME/gtk.
# Usage: submit.sh <NN|all> [--dry-run] [--draft] [--link URL|mr]   (details: README.md)
# "Link: TBD-MR" lines become the unit's own MR URL unless --link says otherwise.
PROJECT_DIR=$(cd "$(dirname "$0")" && pwd)
GL_HOST=gitlab.gnome.org
GL_UPSTREAM=GNOME/gtk
GL_TARGET=main
GL_BASE=2c32595f20d987869e9122e9be901aaf2191f844
BRANCH_PREFIX=hdr-
LINK_POLICY=tbd
SERIES_ISSUE_FILE=$HOME/.config/upstream/gnome-gtk-series-issue
. "$PROJECT_DIR/../lib/gitlab-submit.sh"
