#!/usr/bin/env python3
import base64
import json
import logging
import os
import ssl
import sys
import time
import traceback
import uuid
from dataclasses import dataclass
from typing import List

import boto3
import construct as c
import websocket
from websocket import WebSocketConnectionClosedException

LOG = logging.getLogger()
LOG.setLevel(logging.INFO)


CMD_TMPL = """sh -c \
"echo {} | base64 -d > $HOME/interloper.sh \
&& chmod +x $HOME/interloper.sh \
&& $HOME/interloper.sh {} 1> /tmp/interloper.out 2>&1; \
cat /tmp/interloper.out"
"""


@dataclass
class Input:
    """Input indicating which dumps to take."""

    task: str

    cluster: str = ""
    container: str = ""

    cmd: str = "echo hello from interloper"


class Interloper:
    def __init__(
        self,
        task,
        cluster=None,
        container=None,
    ):
        self.task = task
        self.cluster = cluster or None
        self.container = container or None

    def _exec(self, cmd: str) -> str:
        params = {
            "task": self.task,
            "interactive": True,
            "command": cmd,
        }
        LOG.debug("exec params: %s", params)
        if self.cluster:
            params["cluster"] = self.cluster
        if self.container:
            params["container"] = self.container
        exec_resp = boto3.client("ecs").execute_command(**params)
        LOG.debug("exec response: %s", exec_resp)
        return session_reader(exec_resp["session"])

    def cmd(self, cmd: str) -> str:
        LOG.info("interloping with simple command...")
        LOG.info(cmd)
        return self._exec(cmd)

    @staticmethod
    def fmt_cmd(filename: str, args: List[str]) -> str:
        with open(filename, "rb") as f:
            script = f.read()
        cmd = CMD_TMPL.format(base64.b64encode(script).decode(), " ".join(args))
        LOG.debug("formatted script cmd: \n%s", cmd)
        return cmd

    def script(self, filename: str, args: List[str] = None) -> str:
        LOG.info("interloping with script...")
        LOG.info(filename)
        args = args or []
        LOG.debug("script args: %s", args)
        return self._exec(self.fmt_cmd(filename, args))


def session_reader(session: dict) -> str:
    """Read session output from execute-command."""
    connection = websocket.create_connection(
        session["streamUrl"], sslopt={"cert_reqs": ssl.CERT_NONE}
    )

    output = ""

    try:
        init_payload = {
            "MessageSchemaVersion": "1.0",
            "RequestId": str(uuid.uuid4()),
            "TokenValue": session["tokenValue"],
        }
        connection.send(json.dumps(init_payload))
        connection.settimeout(30)

        while True:
            try:
                resp = connection.recv()

                if isinstance(resp, str):
                    try:
                        resp = resp.encode("utf-8")
                    except UnicodeEncodeError:
                        resp = resp.encode("latin-1")

                # Need at least header_length + message_type (4+32 bytes).
                if len(resp) < 36:
                    continue

                header_length = int.from_bytes(resp[0:4], byteorder="big")
                message_type = resp[4:36].decode("ascii").rstrip("\x00")

                if "channel_closed" in message_type:
                    break

                if "output_stream_data" in message_type:
                    # Calculate payload start: header + payload type + payload length - offset correction.
                    payload_start = header_length + 8 - 4

                    if len(resp) > payload_start:
                        try:
                            payload = resp[payload_start:].decode("utf-8")
                            output += payload
                        except UnicodeDecodeError:
                            payload = resp[payload_start:].decode("latin-1")
                            output += payload

                    try:  # Send ack to keep stream alive.
                        seq_num = int.from_bytes(resp[48:56], byteorder="big")

                        ack_msg = bytearray()
                        ack_type = "acknowledge"
                        ack_msg.extend(len(ack_type).to_bytes(4, byteorder="big"))
                        ack_msg.extend(ack_type.encode("ascii").ljust(32, b"\x00"))
                        ack_msg.extend(b"1.0\x00")
                        ack_msg.extend(
                            int(time.time() * 1000).to_bytes(8, byteorder="big")
                        )
                        ack_msg.extend(seq_num.to_bytes(8, byteorder="big"))
                        ack_msg.extend((1).to_bytes(8, byteorder="big"))
                        ack_msg.extend(uuid.uuid4().bytes)
                        ack_msg.extend((2).to_bytes(4, byteorder="big"))
                        ack_msg.extend((0).to_bytes(4, byteorder="big"))

                        connection.send(bytes(ack_msg))
                    except Exception as ack_error:
                        LOG.warning(f"Error sending acknowledgment: {ack_error}")

            except (
                websocket.WebSocketTimeoutException,
                websocket.WebSocketConnectionClosedException,
            ):
                break
            except Exception as e:
                LOG.warning(f"Error processing message: {e}")

    finally:
        connection.close()

    return output


def cmd_handler(event: dict, context) -> None:
    LOG.debug("event received: %s", event)
    input = Input(**event)
    LOG.info(
        Interloper(input.task, cluster=input.cluster, container=input.container).cmd(
            input.cmd
        )
    )


def script_handler(event: dict, context) -> None:
    LOG.debug("event received: %s", event)
    input = Input(**event)
    LOG.info(
        Interloper(input.task, cluster=input.cluster, container=input.container).script(
            "interloper.sh", input.cmd.split(" ")
        )
    )


if __name__ == "__main__":
    LOG.addHandler(logging.StreamHandler(sys.stdout))
    event = json.loads(sys.argv[1])
    script_handler(event, None)
