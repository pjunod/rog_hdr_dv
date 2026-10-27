# Shared GitLab submission logic for upstream/<project>/submit.sh.
# Sourced, not run. The caller sets, before sourcing:
#   PROJECT_DIR   directory holding units.tsv and the NN-slug unit directories
#   GL_HOST       GitLab host, for example gitlab.gnome.org
#   GL_UPSTREAM   upstream project path, for example GNOME/mutter
#   GL_TARGET     target branch, for example main
#   BRANCH_PREFIX prefix of the branches pushed to the fork
#   LINK_POLICY   "none", or "tbd" to require --link for "Link: TBD-MR"
#
# units.tsv columns (tab separated, '#' comments):
#   NN  slug  deps(comma separated NN, or -)  status(ready|draft|blocked|hold)  title
#   (draft = submitted, but always as a draft MR)
#
# Usage of the caller: submit.sh <NN|all> [--dry-run] [--draft] [--link URL|mr]
#   all          the units in order, stopping at the first one that is not "ready"
#   --dry-run    clone/fetch, apply with --signoff, check, print the MR payload;
#                no fork, no push, no MR
#   --draft      open the MR as a draft ("Draft: " title prefix)
#   --link URL   replace every "Link: TBD-MR" line with "Link: URL"
#   --link mr    replace it with the URL of the unit's own MR (opened first as
#                a draft, then updated)
#   --issue URL  the series' design-discussion issue, put where a DESCRIPTION.md
#                says @SERIES_ISSUE@ (defaults to --link when that is an issue URL)
# Environment: UPSTREAM_SUBMIT_DIR (default ~/.cache/upstream-submit) holds the
# working clone; ~/.config/upstream/$GL_HOST.token holds a personal access
# token with the "api" and "write_repository" scopes.

set -eu

die() { printf 'submit: %s\n' "$*" >&2; exit 1; }
note() { printf 'submit: %s\n' "$*" >&2; }

DRY_RUN=0
DRAFT=0
LINK=
ISSUE=
WHICH=
while [ $# -gt 0 ]; do
    case $1 in
        --dry-run) DRY_RUN=1 ;;
        --draft) DRAFT=1 ;;
        --link) [ $# -ge 2 ] || die '--link needs a URL or "mr"'; LINK=$2; shift ;;
        --link=*) LINK=${1#--link=} ;;
        --issue) [ $# -ge 2 ] || die '--issue needs a URL'; ISSUE=$2; shift ;;
        --issue=*) ISSUE=${1#--issue=} ;;
        -h|--help) sed -n '/^# Usage of the caller/,/^# token/p' "$PROJECT_DIR/../lib/gitlab-submit.sh"; exit 0 ;;
        -*) die "unknown option $1" ;;
        *) [ -z "$WHICH" ] || die 'give one unit (NN) or "all"'; WHICH=$1 ;;
    esac
    shift
done
[ -n "$WHICH" ] || die "usage: $(basename "$0") <NN|all> [--dry-run] [--draft] [--link URL|mr] [--issue URL]"
command -v git >/dev/null || die 'git is required'
command -v python3 >/dev/null || die 'python3 is required'
command -v curl >/dev/null || die 'curl is required'

UNITS=$PROJECT_DIR/units.tsv
[ -f "$UNITS" ] || die "missing $UNITS"
unit_field() { awk -F '\t' -v n="$1" -v f="$2" '!/^#/ && $1 == n { print $f }' "$UNITS"; }
unit_dir() { echo "$PROJECT_DIR/$1-$(unit_field "$1" 2)"; }

WORK=${UPSTREAM_SUBMIT_DIR:-$HOME/.cache/upstream-submit}/$(echo "$GL_UPSTREAM" | tr '/' '_')
UPSTREAM_URL=https://$GL_HOST/$GL_UPSTREAM.git
API=https://$GL_HOST/api/v4
UP_ENC=$(printf '%s' "$GL_UPSTREAM" | sed 's#/#%2F#g')
mkdir -p "$(dirname "$WORK")"
SESSION_TMP=$(mktemp -d "$WORK.tmp.XXXXXX")
trap 'rm -rf "$SESSION_TMP"' EXIT
TOKEN_FILE=$HOME/.config/upstream/$GL_HOST.token
TOKEN=
if [ -f "$TOKEN_FILE" ]; then TOKEN=$(tr -d ' \n\r\t' < "$TOKEN_FILE"); fi
if [ "$DRY_RUN" -eq 0 ] && [ -z "$TOKEN" ]; then
    die "no token in $TOKEN_FILE (create one at https://$GL_HOST/-/user_settings/personal_access_tokens with api and write_repository)"
fi

# The DCO sign-off and the commits are Paul's; this identity is used for
# Signed-off-by and the committer of the rebuilt branch.
export GIT_COMMITTER_NAME='Paul Junod' GIT_COMMITTER_EMAIL='donujp@gmail.com'
g() { git -C "$WORK" -c user.name='Paul Junod' -c user.email=donujp@gmail.com "$@"; }

api() { # api METHOD PATH [JSON]; prints the body, fails on HTTP >= 400
    local method path data out code
    method=$1; path=$2; data=${3:-}
    out=$(mktemp "$SESSION_TMP/api.XXXXXX")
    if [ -n "$data" ]; then
        code=$(curl -sS -o "$out" -w '%{http_code}' -X "$method" -H "PRIVATE-TOKEN: $TOKEN" \
            -H 'Content-Type: application/json' --data-binary "$data" "$API$path") || { rm -f "$out"; die "curl $method $path failed"; }
    else
        code=$(curl -sS -o "$out" -w '%{http_code}' -X "$method" -H "PRIVATE-TOKEN: $TOKEN" "$API$path") || { rm -f "$out"; die "curl $method $path failed"; }
    fi
    # Callers run api inside $(...) or a pipeline (a subshell), so the status
    # goes through a file; read it with api_code.
    printf '%s' "$code" > "$SESSION_TMP/api_code"
    cat "$out"; rm -f "$out"
}
api_code() { cat "$SESSION_TMP/api_code" 2>/dev/null; }
json() { python3 -c 'import json,sys; d=json.load(sys.stdin); print(eval(sys.argv[1], {"d": d}))' "$1"; }

retry() { # the forges sometimes answer 502; try three times
    local i=1
    until "$@"; do
        [ $i -lt 3 ] || die "failed three times: $*"
        i=$((i + 1)); note "retrying in 10 s: $*"; sleep 10
    done
}

prepare_clone() {
    mkdir -p "$(dirname "$WORK")"
    if [ ! -d "$WORK/.git" ]; then
        note "cloning $UPSTREAM_URL into $WORK"
        retry git clone -q "$UPSTREAM_URL" "$WORK"
    fi
    g am --abort >/dev/null 2>&1 || true
    retry g fetch -q origin "$GL_TARGET"
    g checkout -q --detach FETCH_HEAD
    g reset -q --hard
    g clean -qfdx
    BASE=$(g rev-parse HEAD)
}

# Patch files of a unit, rewritten for --link when needed, in a temp dir.
unit_patches() { # unit_patches NN OUTDIR
    local n o d p
    n=$1; o=$2; d=$(unit_dir "$n")
    ls "$d"/*.patch >/dev/null 2>&1 || die "unit $n has no patches in $d"
    mkdir -p "$o"
    for p in "$d"/*.patch; do
        if [ "$LINK_POLICY" = tbd ] && grep -q '^Link: TBD-MR$' "$p"; then
            [ -n "$LINK" ] || die "unit $n still has 'Link: TBD-MR' lines; pass --link <issue-or-MR-URL> or --link mr (see README.md)"
            sed "s#^Link: TBD-MR\$#Link: ${EFFECTIVE_LINK:-TBD-MR}#" "$p" > "$o/$(basename "$p")"
        else
            cp "$p" "$o/"
        fi
    done
}

already_upstream() { # the unit's patches reverse-apply, last first, on pristine BASE
    local tmp rc p
    tmp=$(mktemp -d "$SESSION_TMP/rev.XXXXXX"); unit_patches "$1" "$tmp"
    rc=0
    for p in $(ls "$tmp"/*.patch | sort -r); do
        g apply -R --index "$p" >/dev/null 2>&1 || { rc=1; break; }
    done
    g reset -q --hard "$BASE"
    rm -rf "$tmp"; return $rc
}

apply_unit() { # apply_unit NN (with --signoff)
    local tmp
    tmp=$(mktemp -d "$SESSION_TMP/am.XXXXXX"); unit_patches "$1" "$tmp"
    if ! g am -q --signoff "$tmp"/*.patch; then
        g am --abort >/dev/null 2>&1 || true
        rm -rf "$tmp"
        die "unit $1 no longer applies to $GL_UPSTREAM $GL_TARGET ($BASE); rebase it (see README.md)"
    fi
    rm -rf "$tmp"
}

deps_closure() { # print NN's dependencies, deepest first, without duplicates
    _seen=" "
    _walk() {
        local _d
        for _d in $(unit_field "$1" 3 | tr ',' ' '); do
            [ "$_d" = - ] && continue
            case $_seen in *" $_d "*) continue ;; esac
            _walk "$_d"; _seen="$_seen$_d "; echo "$_d"
        done
    }
    _walk "$1"
}

submit_unit() {
    local n status title desc series branch stacked own_from mr_title body d user repo fork_enc upstream_id fork fork_id st i askpass existing payload iid url
    n=$1
    status=$(unit_field "$n" 4); title=$(unit_field "$n" 5)
    [ -n "$status" ] || die "unknown unit $n"
    desc=$(unit_dir "$n")/DESCRIPTION.md
    [ -f "$desc" ] || die "missing $desc"
    UNIT_DRAFT=$DRAFT
    case $status in
        ready) ;;
        draft) UNIT_DRAFT=1; note "unit $n is opened as a draft MR (README.md)" ;;
        *) note "unit $n status is '$status' (README.md): submitting anyway because it was asked for by number" ;;
    esac
    branch=$BRANCH_PREFIX$n-$(unit_field "$n" 2)
    saved_issue=
    if [ -n "${SERIES_ISSUE_FILE:-}" ] && [ -f "$SERIES_ISSUE_FILE" ]; then saved_issue=$(cat "$SERIES_ISSUE_FILE"); fi
    [ -n "$ISSUE" ] || ISSUE=$saved_issue
    if [ "$LINK_POLICY" = tbd ] && [ -z "$LINK" ]; then
        # Default: a unit with no dependencies links its own MR; a stacked unit
        # links the design-discussion issue opened with "submit.sh 00".
        if [ "$(unit_field "$n" 3)" = - ]; then LINK_UNIT=mr
        elif [ -n "$saved_issue" ]; then LINK_UNIT=$saved_issue
        else die "unit $n is stacked: open the design-discussion issue first with '$(basename "$0") 00' (or pass --link URL)"
        fi
    else
        LINK_UNIT=$LINK
    fi
    LINK_SAVED=$LINK; LINK=$LINK_UNIT
    EFFECTIVE_LINK=
    if [ "$LINK_POLICY" = tbd ] && [ -n "$LINK" ] && [ "$LINK" != mr ]; then
        case $LINK in https://*) EFFECTIVE_LINK=$LINK ;; *) die '--link takes an https:// URL or "mr"' ;; esac
    fi
    [ "$LINK" = mr ] && EFFECTIVE_LINK=https://$GL_HOST/$GL_UPSTREAM/-/merge_requests/PENDING

    prepare_clone
    g checkout -q -B "$branch" "$BASE"
    stacked=
    for d in $(deps_closure "$n"); do
        if already_upstream "$d"; then note "dependency $d is already in $GL_TARGET"; continue; fi
        stacked="$stacked $d"
    done
    if [ "$LINK" = mr ] && [ -n "$stacked" ]; then
        die "--link mr needs every dependency merged first (unmerged:$stacked); use --link <tracking issue URL>"
    fi
    for d in $stacked; do note "applying dependency unit $d"; apply_unit "$d"; done
    own_from=$(g rev-parse HEAD)
    apply_unit "$n"
    note "unit $n: $(g rev-list --count "$own_from..HEAD") commit(s) on $BASE${stacked:+, stacked on unit(s)$stacked}"
    g log --format='  %h %s' "$BASE..HEAD" >&2
    if g log --format=%B "$BASE..HEAD" | grep -q '^Link: TBD-MR$'; then
        die "unresolved 'Link: TBD-MR' in unit $n"
    fi

    mr_title=$(sed -n '1s/^# //p' "$desc")
    [ -n "$mr_title" ] || mr_title=$title
    if [ "$UNIT_DRAFT" -eq 1 ] || [ "$LINK" = mr ]; then mr_title="Draft: $mr_title"; fi
    body=$(sed '1{/^# /d}' "$desc")
    if printf '%s' "$body" | grep -q '@SERIES_ISSUE@'; then
        series=$ISSUE
        case $series:$LINK in :https://*/-/issues/*) series=$LINK ;; esac
        [ -n "$series" ] || die "DESCRIPTION.md of unit $n refers to the design-discussion issue; pass --issue <URL> (README.md)"
        body=$(printf '%s\n' "$body" | sed "s#@SERIES_ISSUE@#$series#g")
    fi
    if [ -n "$stacked" ]; then
        body=$(printf 'This merge request is stacked on the merge request(s) for unit(s)%s; only the last %s commit(s) are new here.\n\n%s' \
            "$stacked" "$(g rev-list --count "$own_from..HEAD")" "$body")
    fi

    if [ "$DRY_RUN" -eq 1 ]; then
        note "dry run: would push $branch to the fork of $GL_UPSTREAM and open an MR into $GL_TARGET"
        printf -- '--- MR title: %s\n--- MR description (%s lines)\n' "$mr_title" "$(printf '%s\n' "$body" | wc -l)"
        printf '%s\n' "$body" | head -20
        printf -- '--- signed-off-by check\n'
        g log --format='%h %(trailers:key=Signed-off-by,valueonly,separator=%x2C )' "$own_from..HEAD"
        return 0
    fi

    user=$(api GET /user | json 'd["username"]')
    [ "$(api_code)" = 200 ] || die "token rejected by $GL_HOST (HTTP $(api_code))"
    repo=${GL_UPSTREAM##*/}
    fork_enc=$(printf '%s/%s' "$user" "$repo" | sed 's#/#%2F#g')
    upstream_id=$(api GET "/projects/$UP_ENC" | json 'd["id"]')
    fork=$(api GET "/projects/$fork_enc" || true)
    if [ "$(api_code)" = 404 ]; then
        note "creating fork $user/$repo"
        api POST "/projects/$UP_ENC/fork" '{}' >/dev/null
        case $(api_code) in 201|409) ;; 403) die "forking refused (HTTP 403): on gitlab.freedesktop.org the account needs user verification first (README.md)" ;; *) die "fork failed (HTTP $(api_code))" ;; esac
        i=0
        while :; do
            st=$(api GET "/projects/$fork_enc" | json 'd.get("import_status","finished")' 2>/dev/null || echo none)
            [ "$st" = finished ] && break
            i=$((i + 1)); [ $i -lt 60 ] || die "fork import did not finish (status $st)"
            sleep 5
        done
    fi
    fork_id=$(api GET "/projects/$fork_enc" | json 'd["id"]')

    askpass=$(mktemp "$SESSION_TMP/askpass.XXXXXX"); chmod 700 "$askpass"
    printf '#!/bin/sh\ncase "$1" in Username*) echo oauth2 ;; *) cat %s ;; esac\n' "$TOKEN_FILE" > "$askpass"
    push() { GIT_ASKPASS=$askpass GIT_TERMINAL_PROMPT=0 git -C "$WORK" push -q --force "https://$GL_HOST/$user/$repo.git" "HEAD:refs/heads/$branch"; }
    push || { rm -f "$askpass"; die "push to $user/$repo failed"; }

    existing=$(api GET "/projects/$upstream_id/merge_requests?state=opened&source_branch=$branch&author_username=$user" | json 'd[0]["iid"] if d else ""')
    payload=$(python3 -c 'import json,sys; print(json.dumps({"title": sys.argv[1], "description": sys.argv[2], "source_branch": sys.argv[3], "target_branch": sys.argv[4], "target_project_id": int(sys.argv[5]), "remove_source_branch": True, "allow_collaboration": True}))' \
        "$mr_title" "$body" "$branch" "$GL_TARGET" "$upstream_id")
    if [ -n "$existing" ]; then
        api PUT "/projects/$upstream_id/merge_requests/$existing" "$payload" >/dev/null
        iid=$existing; note "updated existing MR !$iid"
    else
        iid=$(api POST "/projects/$fork_id/merge_requests" "$payload" | json 'd["iid"]')
        [ "$(api_code)" = 201 ] || die "MR creation failed (HTTP $(api_code))"
        note "opened MR !$iid"
    fi
    url=https://$GL_HOST/$GL_UPSTREAM/-/merge_requests/$iid

    if [ "$LINK" = mr ]; then
        note "rewriting Link: lines to $url"
        EFFECTIVE_LINK=$url
        g checkout -q -B "$branch" "$BASE"
        apply_unit "$n"
        push || { rm -f "$askpass"; die "second push failed"; }
        if [ "$UNIT_DRAFT" -eq 0 ]; then
            api PUT "/projects/$upstream_id/merge_requests/$iid" "$(python3 -c 'import json,sys; print(json.dumps({"title": sys.argv[1]}))' "${mr_title#Draft: }")" >/dev/null
        fi
    fi
    rm -f "$askpass"
    LINK=$LINK_SAVED
    echo "$url"
}

open_series_issue() { # "submit.sh 00": open 00-ISSUE.md as an issue upstream, remember its URL
    local f title body payload url
    f=$PROJECT_DIR/00-ISSUE.md
    [ -f "$f" ] || die "this project has no 00-ISSUE.md"
    [ -n "${SERIES_ISSUE_FILE:-}" ] || die "SERIES_ISSUE_FILE is not set by $(basename "$0")"
    if [ -f "$SERIES_ISSUE_FILE" ]; then note "already opened: $(cat "$SERIES_ISSUE_FILE")"; cat "$SERIES_ISSUE_FILE"; return 0; fi
    title=$(sed -n '1s/^# //p' "$f"); body=$(sed '1{/^# /d}' "$f")
    [ -n "$title" ] || die "00-ISSUE.md must start with '# <title>'"
    if [ "$DRY_RUN" -eq 1 ]; then
        note "dry run: would open issue '$title' on $GL_UPSTREAM ($(printf '%s\n' "$body" | wc -l) lines) and save its URL to $SERIES_ISSUE_FILE"
        return 0
    fi
    payload=$(python3 -c 'import json,sys; print(json.dumps({"title": sys.argv[1], "description": sys.argv[2]}))' "$title" "$body")
    url=$(api POST "/projects/$UP_ENC/issues" "$payload" | json 'd["web_url"]')
    [ "$(api_code)" = 201 ] || die "issue creation failed (HTTP $(api_code))"
    mkdir -p "$(dirname "$SERIES_ISSUE_FILE")"; printf '%s\n' "$url" > "$SERIES_ISSUE_FILE"
    note "opened $url (saved to $SERIES_ISSUE_FILE)"; echo "$url"
}

if [ "$WHICH" = 00 ]; then
    open_series_issue
elif [ "$WHICH" = all ]; then
    # Units are stacked: stop at the first one that is not ready.
    for n in $(awk -F '\t' '!/^#/ { print $1 }' "$UNITS"); do
        st=$(unit_field "$n" 4)
        if [ "$st" != ready ] && [ "$st" != draft ]; then note "stopping at unit $n (status '$st'; see README.md)"; break; fi
        submit_unit "$n"
    done
else
    submit_unit "$WHICH"
fi
