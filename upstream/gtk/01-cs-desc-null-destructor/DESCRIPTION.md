# wayland: Accept absent image descriptions when freeing color state

`GdkWaylandColor.cs_to_desc` maps a color state to `NULL` on purpose when the compositor rejected a
standard image description (`cs_image_desc_failed`) or the state cannot be described (a non-CICP
color state, or an unsupported primaries or transfer function). The table is created with
`wp_image_description_v1_destroy` as its value destructor, which dereferences the proxy. Disposing
a `GdkWaylandDisplay` after any such entry therefore calls `wl_proxy_get_version (NULL)` and
crashes in `gdk_wayland_color_free()`. The destructor also runs when an insert replaces an
existing value: if a synchronous `gdk_wayland_color_get_image_description ()` lookup and the
asynchronous prepare both fail for the same color state, the second `cs_image_desc_failed` insert
replaces `NULL` and calls `wp_image_description_v1_destroy (NULL)` with no disposal involved.

## Reproduction

1. Run against a compositor with `wp_color_manager_v1` that fails a standard image description
   (`failed` event), or request a color state the compositor does not support so that the
   unsupported-primaries/transfer path stores `NULL`.
2. Let GDK look up that color state's description (for example by preparing a surface with it).
3. Dispose the display. Backtrace under gdb (abridged, from GTK 4.24.1):
   `gdk_wayland_color_free` -> `g_hash_table_unref` -> `wp_image_description_v1_destroy (NULL)`
   -> `wl_proxy_get_version (NULL)`.

## Fix

Add a small `cs_desc_destroy ()` that ignores `NULL` and otherwise calls
`wp_image_description_v1_destroy ()`, and use it as the table's value destructor. Descriptions the
compositor accepted are still destroyed as before.

## Evidence and limits

- The patch applies to `main` at `2c32595f20d987869e9122e9be901aaf2191f844` (`git apply --check`).
- The crash was found on 2026-11-14 on GTK 4.24.1 by a regression fixture that makes the
  compositor reject a color description and then tears the display down; it was confirmed with gdb.
  `main` has the same table construction and `NULL` insertions, but it was not built or run here.
- No upstream test is included yet. The fixture that found it fakes the compositor over a socket
  pair and is part of a downstream test series; a standalone reproducer for `main` still has to be
  written (see the pre-submit gate in the kit README).
- Not run: a full GTK build of this patch, GTK's test suite or CI.

## AI assistance

Prepared with AI coding assistants (Anthropic Claude via Claude Code). Before submission the
submitter must build, reproduce and verify this personally, and must state what was verified here.
