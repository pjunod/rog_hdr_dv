#!/usr/bin/env python3
"""Read-only Linux display evidence. No capability or calibration verdict."""

import argparse
import ast
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import selectors
import shlex
import stat
import subprocess
import time

SCHEMA_VERSION = 1
OUTPUT_LIMIT = 65536
FILE_LIMIT = 65536
MAX_DEVICES = 32
PACKAGES = (
    "mutter*", "libmutter*", "gnome-shell", "libdisplay-info*", "colord",
    "mpv", "ffmpeg", "libplacebo*", "nvidia-driver-*", "libnvidia-gl-*",
    "libegl-mesa0", "libgl1-mesa-dri", "mesa-*", "linux-image-*",
)


def problem(reason, status="error"):
    return {"status": status, "reason": reason}


def response_fields(value, count):
    """GVariant tuples/arrays parse as lists; dictionaries never stand in."""
    if not isinstance(value, list) or len(value) != count:
        raise ValueError("unexpected response fields")
    return value


def run_command(argv, timeout):
    """Bound both time and output; never invoke a shell or return stderr."""
    try:
        proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        return problem("command_missing", "unavailable")
    except PermissionError:
        return problem("permission_denied")
    except OSError:
        return problem("command_start_failed")
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    deadline = time.monotonic() + timeout
    failure = None
    with selectors.DefaultSelector() as selector:
        selector.register(proc.stdout, selectors.EVENT_READ, "stdout")
        selector.register(proc.stderr, selectors.EVENT_READ, "stderr")
        try:
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    failure = "timeout"
                    break
                for key, _ in selector.select(remaining):
                    chunk = os.read(key.fileobj.fileno(), 8192)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    buffers[key.data].extend(chunk)
                    if sum(map(len, buffers.values())) > OUTPUT_LIMIT:
                        failure = "output_limit"
                        break
                if failure:
                    break
            if failure:
                proc.kill()
            try:
                proc.wait(timeout=max(0.01, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                failure = "timeout"
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
            proc.stdout.close()
            proc.stderr.close()
    if failure:
        return problem(failure)
    # dpkg may return 1 for unmatched patterns; its valid rows remain useful.
    return {"status": "ok", "returncode": proc.returncode,
            "stdout": buffers["stdout"].decode("utf-8", errors="replace")}


class VariantParser:
    """Parse the bounded, non-executable gdbus GVariant text subset we use."""

    token = re.compile(r"\s*(?:(?P<string>'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\")|"
                       r"(?P<number>[-+]?(?:\d+\.\d*(?:[eE][-+]?\d+)?|\d+))|"
                       r"(?P<word>@[^\s,<>]+|[A-Za-z_][A-Za-z_0-9]*)|"
                       r"(?P<punct>[()\[\]{}<>,:]))")
    types = {"uint16", "uint32", "uint64", "int16", "int32", "int64",
             "byte", "double", "objectpath", "signature"}

    def __init__(self, text):
        self.tokens = []
        position = 0
        while position < len(text):
            if not text[position:].strip():
                break
            match = self.token.match(text, position)
            if not match:
                raise ValueError("invalid token")
            self.tokens.append((match.lastgroup, match.group(match.lastgroup)))
            position = match.end()
        self.position = 0

    def take(self):
        if self.position >= len(self.tokens):
            raise ValueError("incomplete value")
        token = self.tokens[self.position]
        self.position += 1
        return token

    def peek(self):
        return self.tokens[self.position][1] if self.position < len(self.tokens) else None

    def value(self, depth=0):
        if depth > 32:
            raise ValueError("nested value")
        kind, token = self.take()
        if kind == "string":
            return ast.literal_eval(token)
        if kind == "number":
            value = float(token) if any(c in token for c in ".eE") else int(token)
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError("nonfinite number")
            return value
        if kind == "word":
            if token in self.types or token.startswith("@"):
                return self.value(depth + 1)
            if token in ("true", "false"):
                return token == "true"
            raise ValueError("unsupported word")
        if token == "<":
            value = self.value(depth + 1)
            if self.take()[1] != ">":
                raise ValueError("unclosed variant")
            return value
        if token not in ("(", "[", "{"):
            raise ValueError("unsupported value")
        close = {"(": ")", "[": "]", "{": "}"}[token]
        result = {} if token == "{" else []
        while self.peek() != close:
            value = self.value(depth + 1)
            if token == "{":
                if not isinstance(value, str) or self.take()[1] != ":":
                    raise ValueError("invalid dictionary key")
                result[value] = self.value(depth + 1)
            else:
                result.append(value)
            if self.peek() == ",":
                self.take()
            elif self.peek() != close:
                raise ValueError("missing separator")
        self.take()
        return result

    def parse(self):
        value = self.value()
        if self.position != len(self.tokens):
            raise ValueError("trailing input")
        return value


class Inspector:
    def __init__(self, sysfs="/sys", os_release="/etc/os-release",
                 runner=run_command, environment=None, timeout=5.0):
        self.sysfs = Path(sysfs)
        self.os_release = Path(os_release)
        self.runner = runner
        self.environment = os.environ if environment is None else environment
        self.timeout = timeout

    def redact(self, text):
        text = re.sub(r"(?:/home/|/Users/)[^\s/]+(?:/[^\s]*)?", "[private-path]", text)
        text = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[address]", text)
        text = re.sub(r"\b(?:[0-9a-fA-F]{0,4}:){2,}[0-9a-fA-F:]{0,4}\b", "[address]", text)
        text = re.sub(r"[^\s@]+@[^\s]+", "[identity]", text)
        for key in ("HOME", "USER", "LOGNAME", "HOSTNAME"):
            value = self.environment.get(key)
            if value:
                text = re.sub(r"(?<![A-Za-z0-9])" + re.escape(value) +
                              r"(?![A-Za-z0-9])", "[private]", text)
        return text[:1024]

    def read(self, path, binary=False):
        try:
            descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
            with os.fdopen(descriptor, "rb") as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                    return problem("not_regular_file")
                data = stream.read(FILE_LIMIT + 1)
            if len(data) > FILE_LIMIT:
                return problem("file_limit")
            return {"status": "ok", "value": data if binary else data.decode("utf-8").strip()}
        except FileNotFoundError:
            return problem("file_missing", "unavailable")
        except PermissionError:
            return problem("permission_denied")
        except (OSError, UnicodeError):
            return problem("file_read_failed")

    def scalar(self, path, pattern=None, integer=False):
        result = self.read(path)
        if result["status"] != "ok":
            return result
        value = result["value"]
        if integer:
            if not re.fullmatch(r"\d{1,20}", value):
                return problem("invalid_integer")
            value = int(value)
        elif pattern and not re.fullmatch(pattern, value):
            return problem("unexpected_value")
        else:
            value = self.redact(value)
        return {"status": "ok", "value": value}

    def inventory(self, path, pattern):
        try:
            names = sorted(p for p in path.iterdir() if re.fullmatch(pattern, p.name))
            if len(names) > MAX_DEVICES:
                return problem("inventory_limit")
            return {"status": "ok", "items": names}
        except FileNotFoundError:
            return problem("directory_missing", "unavailable")
        except PermissionError:
            return problem("permission_denied")
        except OSError:
            return problem("directory_read_failed")

    def operating_system(self):
        result = self.read(self.os_release)
        if result["status"] != "ok":
            return result
        fields = {}
        allowed = {"ID", "ID_LIKE", "NAME", "PRETTY_NAME", "VERSION_ID", "VERSION_CODENAME", "BUILD_ID"}
        try:
            for line in result["value"].splitlines():
                key, separator, value = line.partition("=")
                if separator and key in allowed:
                    parts = shlex.split(value, comments=True)
                    if len(parts) != 1:
                        raise ValueError("invalid os-release field")
                    fields[key] = self.redact(parts[0])
        except ValueError:
            return problem("invalid_os_release")
        return {"status": "ok", "fields": fields}

    def gpus(self):
        result = self.inventory(self.sysfs / "class/drm", r"card\d+")
        if result["status"] != "ok":
            return result
        items = []
        for path in result["items"]:
            try:
                driver_name = (path / "device/driver").resolve(strict=True).name
                driver = ({"status": "ok", "value": self.redact(driver_name)}
                          if re.fullmatch(r"[A-Za-z0-9_-]+", driver_name)
                          else problem("unexpected_driver_name"))
            except FileNotFoundError:
                driver = problem("driver_missing", "unavailable")
            except PermissionError:
                driver = problem("permission_denied")
            except OSError:
                driver = problem("driver_read_failed")
            items.append({"card": self.redact(path.name), "vendor": self.scalar(path / "device/vendor", r"0x[0-9a-fA-F]{4}"),
                          "device": self.scalar(path / "device/device", r"0x[0-9a-fA-F]{4}"), "driver": driver})
        return {"status": "ok", "items": items}

    def connectors(self):
        result = self.inventory(self.sysfs / "class/drm", r"card\d+-[A-Za-z0-9-]+")
        if result["status"] != "ok":
            return result
        items = []
        for path in result["items"]:
            edid = self.read(path / "edid", binary=True)
            if edid["status"] == "ok":
                data = edid.pop("value")
                edid.update(length_bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
            modes = self.read(path / "modes")
            if modes["status"] == "ok":
                values = modes.pop("value").splitlines()
                modes = ({"status": "ok", "values": values}
                         if all(re.fullmatch(r"\d{1,5}x\d{1,5}(?:[ip])?", v) for v in values)
                         else problem("unexpected_mode_format"))
            items.append({"connector": self.redact(path.name),
                          "connection": self.scalar(path / "status", r"connected|disconnected|unknown"),
                          "enabled": self.scalar(path / "enabled", r"enabled|disabled"),
                          "modes": modes, "edid": edid})
        return {"status": "ok", "items": items}

    def backlights(self):
        result = self.inventory(self.sysfs / "class/backlight", r"[A-Za-z0-9_-]+")
        if result["status"] != "ok":
            return result
        return {"status": "ok", "items": [
            {"interface": self.redact(path.name),
             "type": self.scalar(path / "type", r"raw|platform|firmware"),
             **{name: self.scalar(path / name, integer=True)
                for name in ("brightness", "actual_brightness", "max_brightness")}}
            for path in result["items"]]}

    def command(self, argv):
        result = self.runner(argv, self.timeout)
        if result["status"] != "ok":
            return {key: result[key] for key in ("status", "reason")}
        if result["returncode"]:
            return {"status": "error", "reason": "command_failed", "returncode": result["returncode"]}
        return result

    def dbus(self, bus, destination, path, method, *args):
        result = self.command(["gdbus", "call", "--" + bus, "--dest", destination,
                               "--object-path", path, "--method", method, *args])
        if result["status"] != "ok":
            return result
        try:
            return {"status": "ok", "value": VariantParser(result["stdout"]).parse()}
        except (ValueError, SyntaxError, RecursionError):
            return problem("unparsed_dbus_response")

    def gnome(self):
        if not self.environment.get("DBUS_SESSION_BUS_ADDRESS"):
            return problem("current_session_bus_not_in_environment", "unavailable")
        result = self.dbus("session", "org.gnome.Mutter.DisplayConfig",
                           "/org/gnome/Mutter/DisplayConfig", "org.gnome.Mutter.DisplayConfig.GetCurrentState")
        if result["status"] != "ok":
            return result
        try:
            state = response_fields(result["value"], 4)
            if not (type(state[0]) is int and isinstance(state[1], list)
                    and isinstance(state[2], list) and isinstance(state[3], dict)):
                raise ValueError("unexpected state fields")
            monitors = []
            for monitor in state[1]:
                spec, modes, properties = response_fields(monitor, 3)
                spec = response_fields(spec, 4)
                if not (all(isinstance(value, str) for value in spec) and isinstance(modes, list)
                        and isinstance(properties, dict)):
                    raise ValueError("unexpected monitor fields")
                connector = spec[0]
                if not re.fullmatch(r"[A-Za-z]+[A-Za-z0-9-]*-\d+", connector):
                    connector = "[private-connector]"
                current = []
                for mode in modes:
                    _, width, height, rate, scale, _, flags = response_fields(mode, 7)
                    if not isinstance(flags, dict):
                        raise ValueError("unexpected mode properties")
                    if flags.get("is-current") is True:
                        if not all(type(v) in (int, float) for v in (width, height, rate, scale)):
                            raise ValueError("unexpected numeric mode")
                        current.append({"width": width, "height": height, "refresh_hz": rate,
                                        "preferred_scale": scale})
                colour = {key: value for key, value in properties.items()
                          if key in ("color-mode", "supported-color-modes")}
                for key, value in colour.items():
                    values = value if key == "supported-color-modes" else [value]
                    if not isinstance(values, list) or not all(type(v) is int for v in values):
                        raise ValueError("unexpected colour mode")
                monitors.append({"connector": connector, "current_modes": current,
                                 "colour_properties": colour})
            return {"status": "ok", "monitors": monitors,
                    "colour_mode_meanings": {"0": "default", "1": "bt2100", "2": "sdr_native"}}
        except (ValueError, TypeError, IndexError, AttributeError):
            return problem("unexpected_display_state_shape")

    def packages(self):
        result = self.runner(["dpkg-query", "-W", "-f=${binary:Package}\t${Version}\t${db:Status-Abbrev}\n", *PACKAGES], self.timeout)
        if result["status"] != "ok":
            return {key: result[key] for key in ("status", "reason")}
        items = []
        for line in result["stdout"].splitlines():
            fields = line.split("\t")
            if len(fields) == 3 and fields[2].startswith("ii"):
                name, version, _ = fields
                if re.fullmatch(r"[a-z0-9.+:-]+", name) and re.fullmatch(r"[A-Za-z0-9.+:~_-]+", version):
                    items.append({"package": name, "version": self.redact(version)})
        if result["returncode"] and not items:
            return {"status": "error", "reason": "command_failed", "returncode": result["returncode"]}
        return {"status": "ok", "items": items, "query_returncode": result["returncode"],
                "unmatched_patterns_possible": result["returncode"] != 0}

    def profile_hash(self, filename):
        if not isinstance(filename, str) or not filename.startswith("/"):
            return problem("profile_filename_unavailable", "unavailable")
        digest = hashlib.sha256()
        count = 0
        try:
            descriptor = os.open(filename, os.O_RDONLY | os.O_NONBLOCK)
            with os.fdopen(descriptor, "rb") as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                    return problem("not_regular_profile_file")
                while True:
                    chunk = stream.read(65536)
                    if not chunk:
                        break
                    count += len(chunk)
                    if count > 16 * 1024 * 1024:
                        return problem("profile_size_limit")
                    digest.update(chunk)
        except FileNotFoundError:
            return problem("profile_file_missing", "unavailable")
        except PermissionError:
            return problem("permission_denied")
        except OSError:
            return problem("profile_read_failed")
        return {"status": "ok", "length_bytes": count, "sha256": digest.hexdigest()}

    def colord(self):
        dest = "org.freedesktop.ColorManager"
        result = self.dbus("system", dest, "/org/freedesktop/ColorManager",
                           dest + ".GetDevicesByKind", "display")
        if result["status"] != "ok":
            return result
        devices = []
        try:
            paths, = response_fields(result["value"], 1)
            if not isinstance(paths, list) or len(paths) > MAX_DEVICES:
                raise ValueError("invalid devices")
            for index, path in enumerate(paths):
                if not isinstance(path, str) or not path.startswith("/org/freedesktop/ColorManager/devices/"):
                    raise ValueError("invalid device path")
                profiles = self.dbus("system", dest, path, "org.freedesktop.DBus.Properties.Get",
                                     dest + ".Device", "Profiles")
                device = {"display_index": index, "profiles": []}
                if profiles["status"] != "ok":
                    device["profiles"] = profiles
                else:
                    profile_paths, = response_fields(profiles["value"], 1)
                    if not isinstance(profile_paths, list) or len(profile_paths) > MAX_DEVICES:
                        raise ValueError("invalid profiles")
                    for profile_path in profile_paths:
                        if not isinstance(profile_path, str) or not profile_path.startswith("/org/freedesktop/ColorManager/profiles/"):
                            raise ValueError("invalid profile path")
                        title = self.dbus("system", dest, profile_path, "org.freedesktop.DBus.Properties.Get", dest + ".Profile", "Title")
                        filename = self.dbus("system", dest, profile_path, "org.freedesktop.DBus.Properties.Get", dest + ".Profile", "Filename")
                        if title["status"] == "ok":
                            value, = response_fields(title["value"], 1)
                            if not isinstance(value, str):
                                raise ValueError("invalid title")
                            title = {"status": "ok", "sha256": hashlib.sha256(value.encode()).hexdigest()}
                        if filename["status"] == "ok":
                            value, = response_fields(filename["value"], 1)
                            if not isinstance(value, str):
                                raise ValueError("invalid filename")
                            file_hash = self.profile_hash(value)
                        else:
                            file_hash = filename
                        device["profiles"].append({"name_hash": title, "file": file_hash})
                devices.append(device)
        except (ValueError, TypeError, IndexError):
            return problem("unexpected_colord_response_shape")
        return {"status": "ok", "displays": devices,
                "association": "colord display index; no connector identity captured"}

    def collect(self, system=None, kernel=None):
        system = platform.system() if system is None else system
        report = {"schema_version": SCHEMA_VERSION, "platform": system,
                  "read_only": True, "capability_verdict": "not_evaluated"}
        if system != "Linux":
            report.update(status="unsupported_platform", reason="linux_required")
            return report
        report.update(status="ok", kernel_release=self.redact(platform.release() if kernel is None else kernel),
                      os_release=self.operating_system(), gpus=self.gpus(),
                      drm_connectors=self.connectors(), backlights=self.backlights(),
                      packages=self.packages(), gnome=self.gnome(), colord=self.colord())
        return report


def write_report(path, text):
    # Refuse replacement, symlinks and shared pre-existing files. chmod is never
    # applied to an existing user file. Parent directories must already exist.
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(text)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Create a new private (0600) JSON report; refuses existing files")
    parser.add_argument("--timeout", type=float, default=5.0, help="Per-command timeout in seconds (0.1–30; default 5)")
    args = parser.parse_args(argv)
    if not 0.1 <= args.timeout <= 30:
        parser.error("--timeout must be between 0.1 and 30 seconds")
    report = Inspector(timeout=args.timeout).collect()
    text = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        try:
            write_report(args.output, text)
        except OSError:
            parser.exit(1, "Could not create report: destination must be new and writable.\n")
    else:
        print(text, end="")
    return 0 if report["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
