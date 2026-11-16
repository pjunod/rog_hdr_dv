#!/usr/bin/env python3
"""Capture selected synthetic IQ stimuli from an unlocked GNOME session.

Captures are private diagnostics. Y4M sources cannot declare all colour tags,
so mpv receives the explicit BT.2020/PQ/limited-range interpretation below.
Inherited from Claude's private IQ capture helper; adapted for portable inputs
and single-frame deterministic captures.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

TAGS = "--vf=format=colormatrix=bt.2020-ncl:colorlevels=limited:primaries=bt.2020:gamma=pq"
ZOOM8 = ["--video-unscaled=yes", "--video-zoom=3"]
VIDEO8 = (512, 368, 1536, 864)
SCENES = ["dither", "siting-c420mpeg2", "siting-c420jpeg", "siting-c420paldv",
          "scaling4k", *(f"cadence-{fps}" for fps in (24, 25, 30, 50, 60))]


def extract_y4m_frame(data: bytes, index: int) -> tuple[bytes, dict]:
    """Return a standalone one-frame Y4M file and parsed geometry/chroma metadata."""
    if index < 0:
        raise ValueError("frame index must be nonnegative")
    nl = data.find(b"\n")
    if nl < 0:
        raise ValueError("missing Y4M stream header")
    header = data[:nl + 1]
    if not header.startswith(b"YUV4MPEG2 "):
        raise ValueError("unsupported Y4M stream header")
    fields = header.decode("ascii", "strict").strip().split()
    values = {field[0]: field[1:] for field in fields[1:] if len(field) > 1}
    try:
        width, height, chroma = int(values["W"]), int(values["H"]), values["C"]
    except (KeyError, ValueError) as exc:
        raise ValueError("Y4M header needs width, height, and chroma") from exc
    if width <= 0 or height <= 0 or width % 2 or height % 2:
        raise ValueError("Y4M 4:2:0 dimensions must be positive and even")
    # Frame tags can alter dimensions/chroma interpretation. Reject rather than silently
    # extracting a payload under stream-level assumptions.
    pos, selected, selected_payload = nl + 1, None, None
    if chroma in ("420jpeg", "420mpeg2", "420paldv"):
        frame_size = width * height * 3 // 2
    elif chroma == "420p10":
        frame_size = width * height * 3
    else:
        raise ValueError(f"unsupported Y4M chroma format: {chroma}")
    for current in range(index + 1):
        end = data.find(b"\n", pos)
        if end < 0:
            raise ValueError("truncated Y4M frame header")
        frame_header = data[pos:end]
        if not frame_header.startswith(b"FRAME") or (frame_header != b"FRAME" and not frame_header.startswith(b"FRAME ")):
            raise ValueError("unsupported Y4M per-frame header")
        if frame_header != b"FRAME":
            raise ValueError("unsupported Y4M per-frame tags")
        payload_start = end + 1
        payload_end = payload_start + frame_size
        if payload_end > len(data):
            raise ValueError("truncated Y4M frame payload")
        if current == index:
            selected, selected_payload = frame_header, data[payload_start:payload_end]
        pos = payload_end
    return header + selected + b"\n" + selected_payload, {"width": width, "height": height, "chroma": chroma}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("out_dir", type=Path)
    p.add_argument("--stim-dir", required=True, type=Path)
    p.add_argument("--stim4k-dir", required=True, type=Path)
    p.add_argument("--pw-read", required=True, type=Path)
    p.add_argument("--pw-seq", required=True, type=Path)
    p.add_argument("--monitor", default="eDP-2")
    p.add_argument("--session-id", required=True, help="loginctl graphical session ID, or auto to discover the active seat session")
    p.add_argument("--scene", choices=SCENES, action="append", help="repeatable; default captures all")
    return p


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def unlocked(session_id: str) -> None:
    uid = os.getuid()
    if session_id == "auto":
        sessions = subprocess.run(["loginctl", "list-sessions", "--no-legend"],
                                  capture_output=True, text=True, check=True).stdout.splitlines()
        candidates = [line.split()[0] for line in sessions if len(line.split()) >= 5
                      and line.split()[1].isdigit() and int(line.split()[1]) == uid
                      and line.split()[3] == "seat0"]
    else:
        candidates = [session_id]
    for candidate in candidates:
        result = subprocess.run(["loginctl", "show-session", candidate, "--property=UID",
                                 "--property=Seat", "--property=Type", "--property=Class",
                                 "--property=Active", "--property=LockedHint"],
                                capture_output=True, text=True, check=True)
        props = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
        if (props.get("UID") == str(uid) and props.get("Seat") == "seat0"
                and props.get("Type") in ("wayland", "x11") and props.get("Class") == "user"
                and props.get("Active") == "yes" and props.get("LockedHint") == "no"):
            return
    raise RuntimeError("an active, unlocked graphical seat0 session for this user is required")


class ScreenCast:
    def __init__(self, monitor: str):
        import gi
        gi.require_version("Gio", "2.0")
        from gi.repository import Gio, GLib
        self.Gio, self.GLib = Gio, GLib
        self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self.name, self.root = "org.gnome.Mutter.ScreenCast", "/org/gnome/Mutter/ScreenCast"
        self.session = None
        self.subscription = None
        try:
            session, = self.call(self.root, "", "CreateSession", "(a{sv})", ({},))
            self.session = session
            self.stream, = self.call(session, ".Session", "RecordMonitor", "(sa{sv})",
                                     (monitor, {"cursor-mode": GLib.Variant("u", 0)}))
            self.nodes = []
            self.subscription = self.bus.signal_subscribe(
                self.name, self.name + ".Stream", "PipeWireStreamAdded", self.stream, None,
                Gio.DBusSignalFlags.NONE, lambda *a: self.nodes.append(a[5].unpack()[0]))
            self.call(session, ".Session", "Start")
            deadline = time.monotonic() + 3
            while not self.nodes and time.monotonic() < deadline:
                while GLib.MainContext.default().iteration(False):
                    pass
                time.sleep(.03)
            if not self.nodes:
                raise RuntimeError("no PipeWire node appeared")
            self.node = self.nodes[0]
        except Exception:
            self.close()
            raise

    def call(self, path, suffix, method, sig=None, args=()):
        return self.bus.call_sync(self.name, path, self.name + suffix, method,
                                  self.GLib.Variant(sig, args) if sig else None, None,
                                  self.Gio.DBusCallFlags.NONE, 3000, None).unpack()

    def close(self):
        if self.subscription is not None:
            try:
                self.bus.signal_unsubscribe(self.subscription)
            except Exception:
                pass
            self.subscription = None
        if self.session:
            try:
                self.call(self.session, ".Session", "Stop")
            finally:
                self.session = None


def capture_frame(out: Path, tool: Path, node: int, label: str) -> dict:
    dest = out / f"{label}.xr30"
    r = subprocess.run([str(tool), str(node), str(dest), "xr30"], capture_output=True,
                       text=True, timeout=20)
    return {"name": label, "exit_status": r.returncode, "stderr": r.stderr.strip(),
            "capture_sha256": sha256(dest) if dest.exists() else None}


def mpv_command(sock_path: Path, command: list) -> dict:
    """Send one mpv IPC command and read its matching response ID."""
    request_id = int(time.monotonic_ns() & 0x7fffffff)
    request = json.dumps({"command": command, "request_id": request_id}).encode() + b"\n"
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(3)
        client.connect(str(sock_path))
        client.sendall(request)
        stream = client.makefile("rb")
        while True:
            response = json.loads(stream.readline())
            if response.get("request_id") == request_id:
                if response.get("error") != "success":
                    raise RuntimeError(f"mpv IPC command failed: {response.get('error')}")
                return response


def run(args) -> int:
    out = args.out_dir
    if out.exists():
        raise FileExistsError(f"output directory already exists: {out}")
    if not out.parent.is_dir():
        raise FileNotFoundError(f"output parent must exist: {out.parent}")
    selected = args.scene or SCENES
    for tool in (args.pw_read, args.pw_seq):
        if not tool.is_file() or not os.access(tool, os.X_OK):
            raise FileNotFoundError(f"capture helper is not executable: {tool}")
    unlocked(args.session_id)
    out.mkdir()
    frame_dir = out / "source-frames"
    frame_dir.mkdir()
    log = {"record_version": 1, "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "capture_scope": "digital compositor capture; no optical or panel-cadence assertion",
           "arguments": {"stim_dir": args.stim_dir.name, "stim4k_dir": args.stim4k_dir.name,
                         "pw_read": args.pw_read.name, "pw_seq": args.pw_seq.name,
                         "monitor": args.monitor, "session_id": args.session_id, "scenes": selected},
           "helper_sha256": {str(p.name): sha256(p) for p in (args.pw_read, args.pw_seq)}, "scenes": []}
    cast = None
    children = []
    try:
        cast = ScreenCast(args.monitor)
        log["pipewire_node"] = cast.node
        for name in selected:
            if name.startswith("cadence-"):
                fps = int(name.split("-")[1])
                src = args.stim_dir / "cadence" / f"cadence_{fps}fps_p10.y4m"
                rec = {"scene": name, "source": src.name, "source_sha256": sha256(src),
                       "requested_frames": fps * 8, "fps": fps, "frames": []}
                cmd = ["mpv", "--fs", "--no-audio", "--pause", "--keep-open=always", "--osc=no",
                       "--osd-level=0", "--cursor-autohide=always", "--loop-file=no", TAGS,
                       *ZOOM8, str(src)]
                rec["mpv_args"] = [Path(v).name if v == str(src) else v for v in cmd]
                sock = out / f"{name}.sock"
                cmd.insert(-2, f"--input-ipc-server={sock}")
                rec["mpv_args"].insert(-2, f"--input-ipc-server={sock.name}")
                player = subprocess.Popen(cmd, stdout=(out / "mpv.log").open("a"), stderr=subprocess.STDOUT)
                children.append(player)
                deadline = time.monotonic() + 10
                while not sock.exists():
                    if player.poll() is not None or time.monotonic() >= deadline:
                        raise RuntimeError("mpv did not start for cadence capture")
                    time.sleep(.1)
                seq = subprocess.Popen([str(args.pw_seq), str(cast.node), str(out / name),
                                        str(fps * 8), str(VIDEO8[0]), str(VIDEO8[1]), str(VIDEO8[2]), "160"],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                children.append(seq)
                time.sleep(1)
                mpv_command(sock, ["set_property", "pause", False])
                try:
                    stdout, stderr = seq.communicate(timeout=35)
                except subprocess.TimeoutExpired:
                    seq.kill(); stdout, stderr = seq.communicate()
                rec.update({"sequence_exit_status": seq.returncode, "stderr": stderr.strip()})
                rec["sequence_output"] = stdout.strip()
                if player.poll() is not None:
                    rec["player_exit_status"] = player.returncode
                player.terminate()
                player.wait(timeout=10)
                children.remove(player)
                children.remove(seq)
                log["scenes"].append(rec)
                if rec["sequence_exit_status"] != 0 or rec.get("player_exit_status", 0) != 0:
                    raise RuntimeError(f"{name}: capture helper or player exited unsuccessfully")
                continue
            src, first, count, extra = source_spec(name, args)
            frames = []
            raw = src.read_bytes()
            rec = {"scene": name, "source": src.name, "source_sha256": sha256(src), "frames": frames}
            for i in range(first, first + count):
                one, geometry = extract_y4m_frame(raw, i)
                one_path = frame_dir / f"{name}-f{i}.y4m"
                one_path.write_bytes(one)
                rec.setdefault("extracted_sources", []).append({"file": one_path.name,
                    "sha256": sha256(one_path), **geometry})
                cmd = ["mpv", "--fs", "--no-audio", "--pause", "--keep-open=always", "--osc=no",
                       "--osd-level=0", "--cursor-autohide=always", "--loop-file=no", TAGS, *extra, str(one_path)]
                rec.setdefault("mpv_args", []).append([Path(v).name if v == str(one_path) else v for v in cmd])
                player = subprocess.Popen(cmd, stdout=(out / "mpv.log").open("a"), stderr=subprocess.STDOUT)
                children.append(player)
                time.sleep(3.5)
                if player.poll() is not None:
                    raise RuntimeError(f"{name}-f{i}: mpv exited before capture ({player.returncode})")
                result = capture_frame(out, args.pw_read, cast.node, f"{name}-f{i}")
                frames.append(result)
                if result["exit_status"] != 0 or not result["capture_sha256"]:
                    raise RuntimeError(f"{name}-f{i}: capture helper failed")
                player.terminate()
                player.wait(timeout=10)
                children.remove(player)
            log["scenes"].append(rec)
        return 0
    except Exception as exc:
        message = str(exc)
        for private_path in (out, args.stim_dir, args.stim4k_dir, args.pw_read, args.pw_seq):
            message = message.replace(str(private_path), private_path.name)
        log["error"] = f"{type(exc).__name__}: {message}"
        return 1
    finally:
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
                try: child.wait(timeout=10)
                except subprocess.TimeoutExpired: child.kill(); child.wait()
        if cast:
            try: cast.close()
            except Exception as exc: log["screencast_stop_error"] = str(exc)
        log["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        (out / "run.json").write_text(json.dumps(log, indent=2) + "\n")


def source_spec(name: str, args):
    if name == "dither":
        return args.stim_dir / "dither/dither_ramps_p10.y4m", 0, 2, ZOOM8
    if name.startswith("siting-"):
        tag = name.removeprefix("siting-")
        return args.stim_dir / f"chroma_siting/chroma_siting_{tag}_8bit.y4m", 0, 2, ZOOM8
    return args.stim4k_dir / "scaling/scaling_p10.y4m", 0, 3, []


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        return run(args)
    except Exception as exc:
        print(f"iq_run: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
