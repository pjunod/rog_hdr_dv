#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Relay a real compositor, advertising its color manager last at startup.

Only the first registry-global order and delivery latency change. Protocol
messages and file descriptors are forwarded; capabilities/targets are never
invented. Use isolated, task-owned sockets, not a desktop session socket.
"""
import argparse
import array
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import threading
import time


def receive(peer):
    data, ancillary, flags, _ = peer.recvmsg(65536, socket.CMSG_SPACE(512))
    if flags & socket.MSG_CTRUNC:
        raise RuntimeError("truncated descriptor control data")
    fds = []
    for level, kind, payload in ancillary:
        if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
            values = array.array("i")
            values.frombytes(payload[:len(payload) - len(payload) % values.itemsize])
            fds.extend(values)
    return data, fds


def send(peer, data, fds):
    try:
        control = [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array("i", fds))] if fds else []
        count = peer.sendmsg([data], control)
        if count == 0:
            raise BrokenPipeError("closed relay")
        peer.sendall(data[count:])
    finally:
        for fd in fds:
            os.close(fd)
        fds.clear()


def messages(buffer):
    while len(buffer) >= 8:
        obj, word = struct.unpack_from("=II", buffer)
        size, opcode = word >> 16, word & 65535
        if size < 8 or size % 4:
            raise RuntimeError("invalid Wayland frame")
        if len(buffer) < size:
            return
        message = bytes(buffer[:size])
        del buffer[:size]
        yield obj, opcode, message


def interface(message):
    length = struct.unpack_from("=I", message, 12)[0]
    return message[16:16 + length - 1].decode("ascii"), (length + 3) // 4 * 4


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--listen", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command or args.listen.exists() or args.listen == args.upstream:
        parser.error("supply a command and a fresh, distinct task-owned socket")
    stats = {"client_order": [], "advertised_globals": [], "manager_delayed_ms": 0, "errors": []}
    state = {"registry": None, "manager": None, "compositor": None}
    listener = socket.socket(socket.AF_UNIX)
    listener.bind(str(args.listen))
    os.chmod(args.listen, 0o600)
    listener.listen(1)
    listener.settimeout(10)
    peers = []

    def bridge():
        pending_fds = []
        try:
            client, _ = listener.accept()
            upstream = socket.socket(socket.AF_UNIX)
            upstream.connect(str(args.upstream))
            peers.extend([client, upstream])

            def requests():
                buffer = bytearray()
                try:
                    while True:
                        data, fds = receive(client)
                        if not data:
                            for fd in fds:
                                os.close(fd)
                            break
                        buffer.extend(data)
                        for obj, opcode, message in messages(buffer):
                            if obj == 1 and opcode == 1:
                                state["registry"] = struct.unpack_from("=I", message, 8)[0]
                            elif obj == 1 and opcode == 0:
                                stats["client_order"].append("sync")
                            elif obj == state["registry"] and opcode == 0:
                                name, padded = interface(message)
                                new_id = struct.unpack_from("=I", message, 20 + padded)[0]
                                stats["client_order"].append("bind:" + name)
                                if name == "wp_color_manager_v1":
                                    state["manager"] = new_id
                                if name == "wl_compositor":
                                    state["compositor"] = new_id
                            elif obj == state["compositor"] and opcode == 0:
                                stats["client_order"].append("create_surface")
                        send(upstream, data, fds)
                except (BrokenPipeError, ConnectionResetError, OSError):
                    pass
                finally:
                    try:
                        upstream.shutdown(socket.SHUT_WR)
                    except OSError:
                        pass

            thread = threading.Thread(target=requests, daemon=True)
            thread.start()
            buffer = bytearray()
            held = None
            delayed = False
            initial_globals = True
            while True:
                data, fds = receive(upstream)
                pending_fds.extend(fds)
                if not data:
                    break
                buffer.extend(data)
                for obj, opcode, message in messages(buffer):
                    if initial_globals and obj == state["registry"] and opcode == 0:
                        name, _ = interface(message)
                        if name == "wp_color_manager_v1":
                            held = message
                            continue
                        stats["advertised_globals"].append(name)
                    elif initial_globals and held is not None:
                        send(client, held, pending_fds)
                        stats["advertised_globals"].append("wp_color_manager_v1")
                        initial_globals = False
                        held = None
                    if obj == state["manager"] and not delayed:
                        # Earlier globals' sync replies have already been sent.
                        # A real post-bind sync must keep GTK waiting for this burst.
                        time.sleep(0.05)
                        stats["manager_delayed_ms"] = 50
                        delayed = True
                    send(client, message, pending_fds)
            thread.join(timeout=2)
        except Exception as error:
            stats["errors"].append(repr(error))
        finally:
            for fd in pending_fds:
                os.close(fd)

    worker = threading.Thread(target=bridge, daemon=True)
    worker.start()
    try:
        result = subprocess.run(command, env=os.environ | {"WAYLAND_DISPLAY": str(args.listen)}, timeout=15)
        stats["child_exit"] = result.returncode
    except Exception as error:
        stats["errors"].append(repr(error))
    finally:
        listener.close()
        for peer in peers:
            try:
                peer.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        worker.join(timeout=3)
        for peer in peers:
            peer.close()
        args.listen.unlink(missing_ok=True)
    order = stats["client_order"]
    bound = order.index("bind:wp_color_manager_v1") if "bind:wp_color_manager_v1" in order else len(order)
    surface = order.index("create_surface") if "create_surface" in order else len(order)
    stats["post_manager_sync_before_surface"] = "sync" in order[bound + 1:surface]
    stats["manager_advertised_last"] = stats["advertised_globals"][-1:] == ["wp_color_manager_v1"]
    stats["pass"] = (stats.get("child_exit") == 0 and stats["post_manager_sync_before_surface"]
                     and stats["manager_advertised_last"] and stats["manager_delayed_ms"] == 50
                     and not stats["errors"])
    args.receipt.write_text(json.dumps(stats, indent=2) + "\n")
    print(json.dumps(stats, indent=2))
    return 0 if stats["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
