# Shared GitLab submission logic for upstream/<project>/submit.sh.
# Sourced, not run. The caller sets, before sourcing:
#   PROJECT_DIR   directory holding units.tsv and the NN-slug unit directories
#   GL_HOST       GitLab host, for example gitlab.gnome.org
#   GL_UPSTREAM   upstream project path, for example GNOME/mutter
#   GL_TARGET     target branch, for example main
#   BRANCH_PREFIX prefix of the branches pushed to the fork
#   LINK_POLICY   "none", or "tbd" to resolve "Link: TBD-MR" automatically
#
# units.tsv columns (tab separated, '#' comments):
#   NN  slug  deps(comma separated NN, or -)  status(ready|draft|blocked|hold)  title
#   (draft = ready for submission, but always as a draft MR)
#
# Usage of the caller: submit.sh <NN|all> [--dry-run] [--draft] [--link URL|mr]
#   all          the units in order, stopping at the first one that is not "ready"
#   --dry-run    clone/fetch, apply unsigned, check, print the MR payload;
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
OWNER=$WORK/.git/upstream-submit-owner
UPSTREAM_URL=https://$GL_HOST/$GL_UPSTREAM.git
API=https://$GL_HOST/api/v4
UP_ENC=$(printf '%s' "$GL_UPSTREAM" | sed 's#/#%2F#g')
mkdir -p "$(dirname "$WORK")"
SESSION_TMP=$(mktemp -d "$WORK.tmp.XXXXXX")
LOCK=$WORK.lock
LOCK_OWNED=0
trap 'rm -rf "$SESSION_TMP"; if [ "$LOCK_OWNED" -eq 1 ]; then rmdir "$LOCK"; fi' EXIT
mkdir "$LOCK" 2>/dev/null || die "another submission owns $LOCK; check it before removing a stale lock"
LOCK_OWNED=1
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

api() { # api METHOD PATH [JSON] [allowed HTTP code]
    local method path data allowed out code
    method=$1; path=$2; data=${3:-}; allowed=${4:-}
    out=$(mktemp "$SESSION_TMP/api.XXXXXX")
    if [ -n "$data" ]; then
        code=$(curl -sS --connect-timeout 15 --max-time 120 -o "$out" -w '%{http_code}' -X "$method" -H "PRIVATE-TOKEN: $TOKEN" \
            -H 'Content-Type: application/json' --data-binary "$data" "$API$path") || { rm -f "$out"; die "curl $method $path failed"; }
    else
        code=$(curl -sS --connect-timeout 15 --max-time 120 -o "$out" -w '%{http_code}' -X "$method" -H "PRIVATE-TOKEN: $TOKEN" "$API$path") || { rm -f "$out"; die "curl $method $path failed"; }
    fi
    # Callers run api inside $(...) or a pipeline (a subshell), so the status
    # goes through a file; read it with api_code.
    printf '%s' "$code" > "$SESSION_TMP/api_code"
    if [ "$code" -lt 200 ] || [ "$code" -ge 300 ]; then
        if [ "$code" != "$allowed" ]; then
            rm -f "$out"
            die "GitLab $method $path failed (HTTP $code)"
        fi
    fi
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
    if [ ! -e "$WORK" ]; then
        note "cloning $UPSTREAM_URL into $WORK"
        retry git clone -q "$UPSTREAM_URL" "$WORK"
        printf '%s\n' "$UPSTREAM_URL" > "$OWNER"
    fi
    [ -f "$OWNER" ] && [ "$(cat "$OWNER")" = "$UPSTREAM_URL" ] ||
        die "refusing unowned cache $WORK; choose an empty UPSTREAM_SUBMIT_DIR"
    [ "$(g remote get-url origin)" = "$UPSTREAM_URL" ] || die "cache origin differs from $UPSTREAM_URL"
    [ -z "$(g status --porcelain --untracked-files=all)" ] || die "cache has local changes: $WORK"
    [ ! -d "$WORK/.git/rebase-apply" ] && [ ! -d "$WORK/.git/rebase-merge" ] ||
        die "cache has an interrupted am/rebase: $WORK"
    retry g fetch -q origin "$GL_TARGET"
    g checkout -q --no-overwrite-ignore --detach FETCH_HEAD
    BASE=$(g rev-parse HEAD)
    if [ "$DRY_RUN" -eq 0 ] && [ -n "${GL_BASE:-}" ] && [ "$BASE" != "$GL_BASE" ]; then
        die "upstream moved from qualified base $GL_BASE to $BASE; rebase and requalify before real submission (dry-run remains available)"
    fi
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
            python3 -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).read_text().replace("Link: TBD-MR\n", "Link: " + sys.argv[2] + "\n"), end="")' \
                "$p" "${EFFECTIVE_LINK:-TBD-MR}" > "$o/$(basename "$p")"
        else
            cp "$p" "$o/"
        fi
    done
}

already_upstream() { # the unit's patches reverse-apply, last first, on pristine BASE
    local tmp rc p
    tmp=$(mktemp -d "$SESSION_TMP/rev.XXXXXX"); unit_patches "$1" "$tmp"
    rc=0
    python3 -c 'import pathlib,sys; print("\n".join(str(p) for p in sorted(pathlib.Path(sys.argv[1]).glob("*.patch"), reverse=True)))' "$tmp" > "$tmp/order"
    while IFS= read -r p; do
        g apply -R --index "$p" >/dev/null 2>&1 || { rc=1; break; }
    done < "$tmp/order"
    g reset -q --hard "$BASE"
    rm -rf "$tmp"; return $rc
}

apply_unit() { # apply_unit NN (sign off only during a real human submission)
    local tmp unit
    unit=$1
    tmp=$(mktemp -d "$SESSION_TMP/am.XXXXXX"); unit_patches "$unit" "$tmp"
    if [ "$DRY_RUN" -eq 1 ]; then
        set -- -q
    else
        set -- -q --signoff
    fi
    if ! g am "$@" "$tmp"/*.patch; then
        g am --abort >/dev/null 2>&1 || true
        rm -rf "$tmp"
        die "unit $unit no longer applies to $GL_UPSTREAM $GL_TARGET ($BASE); rebase it (see README.md)"
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
        *)
            if [ "$DRY_RUN" -eq 0 ]; then die "unit $n is '$status'; resolve its prerequisite/design hold before submission"; fi
            note "unit $n status is '$status': unsigned preview only" ;;

    esac
    branch=$BRANCH_PREFIX$n-$(unit_field "$n" 2)
    saved_issue=
    if [ -n "${SERIES_ISSUE_FILE:-}" ] && [ -f "$SERIES_ISSUE_FILE" ]; then saved_issue=$(cat "$SERIES_ISSUE_FILE"); fi
    [ -n "$ISSUE" ] || ISSUE=$saved_issue
    if [ "$LINK_POLICY" = tbd ] && [ -z "$LINK" ]; then
        # Default: a unit with no dependencies links its own MR; a stacked unit
        # links the design-discussion issue opened with "submit.sh 00".
        if [ "$(unit_field "$n" 3)" = - ]; then LINK_UNIT=mr
        elif [ -n "$ISSUE" ]; then LINK_UNIT=$ISSUE
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
    if g show-ref --verify --quiet "refs/heads/$branch"; then
        g update-ref "refs/upstream-submit/archive/$(basename "$SESSION_TMP")/$branch" "refs/heads/$branch"
    fi
    g checkout -q --no-overwrite-ignore -B "$branch" "$BASE"
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
    body=$(sed '1{/^# /d;}' "$desc")
    if printf '%s' "$body" | grep -q '@SERIES_ISSUE@'; then
        series=$ISSUE
        case $series:$LINK in :https://*/-/issues/*) series=$LINK ;; esac
        [ -n "$series" ] || die "DESCRIPTION.md of unit $n refers to the design-discussion issue; pass --issue <URL> (README.md)"
        body=$(printf '%s\n' "$body" | python3 -c 'import sys; print(sys.stdin.read().replace("@SERIES_ISSUE@",sys.argv[1]),end="")' "$series")
    fi
    if [ -n "$stacked" ]; then
        body=$(printf 'This merge request is stacked on the merge request(s) for unit(s)%s; only the last %s commit(s) are new here.\n\n%s' \
            "$stacked" "$(g rev-list --count "$own_from..HEAD")" "$body")
    fi

    if [ "$DRY_RUN" -eq 1 ]; then
        note "dry run: would push $branch to the fork of $GL_UPSTREAM and open an MR into $GL_TARGET"
        printf -- '--- MR title: %s\n--- MR description (%s lines)\n' "$mr_title" "$(printf '%s\n' "$body" | wc -l)"
        printf '%s\n' "$body" | head -20
        printf -- '--- unsigned preview (sign-off is added only by a real submission)\n'
        g log --format='%h %(trailers:key=Signed-off-by,valueonly,separator=%x2C )' "$own_from..HEAD"
        LINK=$LINK_SAVED
        return 0
    fi

    user=$(api GET /user | json 'd["username"]')
    [ "$(api_code)" = 200 ] || die "token rejected by $GL_HOST (HTTP $(api_code))"
    [ "$user" = pjunod ] || die "authenticated as $user, expected pjunod for these Paul-authored submissions"
    repo=${GL_UPSTREAM##*/}
    fork_enc=$(printf '%s/%s' "$user" "$repo" | sed 's#/#%2F#g')
    upstream_id=$(api GET "/projects/$UP_ENC" | json 'd["id"]')
    fork=$(api GET "/projects/$fork_enc" '' 404)
    if [ "$(api_code)" = 404 ]; then
        note "creating fork $user/$repo"
        api POST "/projects/$UP_ENC/fork" '{}' 409 >/dev/null
        case $(api_code) in 201|409) ;; 403) die "forking refused (HTTP 403): on gitlab.freedesktop.org the account needs user verification first (README.md)" ;; *) die "fork failed (HTTP $(api_code))" ;; esac
        i=0
        while :; do
            st=$(api GET "/projects/$fork_enc" | json 'd.get("import_status","finished")' 2>/dev/null || echo none)
            [ "$st" = finished ] && break
            i=$((i + 1)); [ $i -lt 60 ] || die "fork import did not finish (status $st)"
            sleep 5
        done
    fi
    fork=$(api GET "/projects/$fork_enc")
    fork_id=$(printf '%s' "$fork" | json 'd["id"]')
    [ "$(printf '%s' "$fork" | json 'd.get("forked_from_project",{}).get("id", "")')" = "$upstream_id" ] ||
        die "$user/$repo exists but is not a fork of $GL_UPSTREAM"

    askpass=$(mktemp "$SESSION_TMP/askpass.XXXXXX"); chmod 700 "$askpass"
    printf '#!/bin/sh\ncase "$1" in Username*) echo oauth2 ;; *) cat "$UPSTREAM_TOKEN_FILE" ;; esac\n' > "$askpass"
    export UPSTREAM_TOKEN_FILE=$TOKEN_FILE
    push() {
        # Capture the observed remote tip; a concurrent edit must not be overwritten.
        local remote expected published receipt
        remote=https://$GL_HOST/$user/$repo.git
        expected=$(GIT_ASKPASS=$askpass GIT_TERMINAL_PROMPT=0 git ls-remote "$remote" "refs/heads/$branch" | awk '{print $1}') || return
        receipt=$WORK/.git/upstream-submit-published/$branch
        published=
        [ ! -f "$receipt" ] || published=$(cat "$receipt")
        [ "$expected" = "$published" ] || {
            note "refusing to overwrite unowned or changed remote branch $branch; expected recorded tip ${published:-absent}, found ${expected:-absent}"
            return 1
        }
        mkdir -p "$(dirname "$receipt")" || return
        GIT_ASKPASS=$askpass GIT_TERMINAL_PROMPT=0 git -C "$WORK" push -q \
            "--force-with-lease=refs/heads/$branch:$expected" "$remote" "HEAD:refs/heads/$branch" || return
        g rev-parse HEAD > "$receipt.new" && mv "$receipt.new" "$receipt"

    }
    existing=$(api GET "/projects/$upstream_id/merge_requests?state=all&source_branch=$branch&author_username=$user")
    existing=$(printf '%s' "$existing" | python3 -c 'import json,sys; print(next((str(m["iid"])+" "+m.get("state","opened") for m in json.load(sys.stdin) if m.get("source_project_id") == int(sys.argv[1]) and m.get("target_project_id") == int(sys.argv[2]) and m.get("target_branch") == sys.argv[3]), ""))' "$fork_id" "$upstream_id" "$GL_TARGET")
    if [ -n "$existing" ]; then
        mr_state=${existing#* }; existing=${existing%% *}
        case $mr_state in
            merged) note "MR !$existing is already merged"; LINK=$LINK_SAVED; echo "https://$GL_HOST/$GL_UPSTREAM/-/merge_requests/$existing"; return 0 ;;
            closed) die "MR !$existing is closed; review its disposition before any resubmission" ;;
            opened) ;;
            *) die "unexpected MR state $mr_state" ;;
        esac
    fi
    push || { rm -f "$askpass"; die "push to $user/$repo failed"; }
    payload=$(python3 -c 'import json,sys; print(json.dumps({"title": sys.argv[1], "description": sys.argv[2], "source_branch": sys.argv[3], "target_branch": sys.argv[4], "target_project_id": int(sys.argv[5]), "remove_source_branch": True, "allow_collaboration": True}))' \
        "$mr_title" "$body" "$branch" "$GL_TARGET" "$upstream_id")
    if [ -n "$existing" ]; then
        api PUT "/projects/$upstream_id/merge_requests/$existing" "$payload" >/dev/null
        [ "$(api_code)" = 200 ] || die "MR update failed (HTTP $(api_code))"
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
        g checkout -q --no-overwrite-ignore -B "$branch" "$BASE"
        apply_unit "$n"
        push || { rm -f "$askpass"; die "second push failed"; }
        if [ "$UNIT_DRAFT" -eq 0 ]; then
            api PUT "/projects/$upstream_id/merge_requests/$iid" "$(python3 -c 'import json,sys; print(json.dumps({"title": sys.argv[1]}))' "${mr_title#Draft: }")" >/dev/null
            [ "$(api_code)" = 200 ] || die "MR un-draft failed (HTTP $(api_code))"
        fi
    fi
    rm -f "$askpass"
    LINK=$LINK_SAVED
    echo "$url"
}

open_series_issue() { # "submit.sh 00": open 00-ISSUE.md as an issue upstream, remember its URL
    local f title body payload url user
    f=$PROJECT_DIR/00-ISSUE.md
    [ -f "$f" ] || die "this project has no 00-ISSUE.md"
    [ -n "${SERIES_ISSUE_FILE:-}" ] || die "SERIES_ISSUE_FILE is not set by $(basename "$0")"
    if [ -f "$SERIES_ISSUE_FILE" ]; then note "already opened: $(cat "$SERIES_ISSUE_FILE")"; cat "$SERIES_ISSUE_FILE"; return 0; fi
    title=$(sed -n '1s/^# //p' "$f"); body=$(sed '1{/^# /d;}' "$f")
    [ -n "$title" ] || die "00-ISSUE.md must start with '# <title>'"
    if [ "$DRY_RUN" -eq 1 ]; then
        note "dry run: would open issue '$title' on $GL_UPSTREAM ($(printf '%s\n' "$body" | wc -l) lines) and save its URL to $SERIES_ISSUE_FILE"
        return 0
    fi
    user=$(api GET /user | json 'd["username"]')
    [ "$user" = pjunod ] || die "authenticated as $user, expected pjunod for this issue"
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
