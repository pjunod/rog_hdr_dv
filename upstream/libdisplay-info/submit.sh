#!/bin/sh
# Submit libdisplay-info units to gitlab.freedesktop.org/emersion/libdisplay-info.
# Usage: submit.sh <NN|all> [--dry-run] [--draft]   (details: README.md)
PROJECT_DIR=$(cd "$(dirname "$0")" && pwd)
GL_HOST=gitlab.freedesktop.org
GL_UPSTREAM=emersion/libdisplay-info
GL_TARGET=main
GL_BASE=af382cf311ce60983708a9e664728a61843143e7
BRANCH_PREFIX=ldi-
LINK_POLICY=none
. "$PROJECT_DIR/../lib/gitlab-submit.sh"
