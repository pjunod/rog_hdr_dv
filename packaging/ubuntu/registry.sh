# Forgejo Debian registry helpers, sourced by publish.sh and rebuild.sh.
#
# Needs FORGEJO_URL, FORGEJO_OWNER and CODENAME; writes need FORGEJO_TOKEN.
# The token reaches curl through a config on a file descriptor, never on the
# command line, so it does not show in the process list of a shared host.

registry=$FORGEJO_URL/api/packages/$FORGEJO_OWNER/debian
pool=$registry/pool/$CODENAME/main

authed_curl() {  # authed_curl CURL-ARGS...
  : "${FORGEJO_TOKEN:?FORGEJO_TOKEN is not set}"
  curl -K <(printf 'header = "Authorization: token %s"\n' "$FORGEJO_TOKEN") "$@"
}

# The registry's Packages index for an architecture. An index that does not
# exist yet is empty; any other failure stops the caller, because "could not
# read the registry" must never be mistaken for "not published".
packages_index() {  # packages_index ARCH
  local body code
  body=$(curl -s -w '\n%{http_code}' "$registry/dists/$CODENAME/main/binary-$1/Packages") \
    || { echo "registry.sh: cannot reach $registry" >&2; return 1; }
  code=${body##*$'\n'} body=${body%$'\n'*}
  case $code in
    200) printf '%s\n' "$body" ;;
    404) ;;
    *) echo "registry.sh: $registry answered HTTP $code for the $1 index" >&2; return 1 ;;
  esac
}

# "name version" for every binary package of a source in an index.
binaries_of() {  # binaries_of SOURCE ARCH
  local index
  index=$(packages_index "$2") || return 1
  printf '%s\n' "$index" | awk -v src="$1" '
    /^Package: / {name = $2; source = $2; version = ""}
    /^Source: /  {source = $2}
    /^Version: / {version = $2}
    /^$/ && name != "" {if (source == src) print name, version; name = ""}
    END {if (name != "" && source == src) print name, version}'
}

is_published() {  # is_published PACKAGE VERSION ARCH
  local index
  index=$(packages_index "$3") || return 2
  printf '%s\n' "$index" | awk -v p="$1" -v v="$2" '
    $1 == "Package:" {name = $2} $1 == "Version:" && name == p && $2 == v {found = 1}
    END {exit !found}'
}

delete_package() {  # delete_package NAME VERSION ARCH
  local code
  code=$(authed_curl -s -o /dev/null -w '%{http_code}' -X DELETE "$pool/$1/$2/$3")
  case $code in
    204|404) ;;
    *) echo "registry.sh: deleting $1 $2 $3 answered HTTP $code" >&2; return 1 ;;
  esac
}
