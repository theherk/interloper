#!/usr/bin/env python3
import base64
import json
import logging
import ssl
import sys
import uuid
from dataclasses import dataclass
from typing import List

import boto3
import construct as c
import websocket


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
    AgentMessageHeader = c.Struct(
        "HeaderLength" / c.Int32ub,
        "MessageType" / c.PaddedString(32, "ascii"),
    )

    AgentMessagePayload = c.Struct(
        "PayloadLength" / c.Int32ub,
        "Payload" / c.PaddedString(c.this.PayloadLength, "ascii"),
    )

    connection = websocket.create_connection(
        session["streamUrl"], sslopt={"cert_reqs": ssl.CERT_NONE}
    )
    try:
        init_payload = {
            "MessageSchemaVersion": "1.0",
            "RequestId": str(uuid.uuid4()),
            "TokenValue": session["tokenValue"],
        }
        connection.send(json.dumps(init_payload))
        while True:
            resp = connection.recv()
            message = AgentMessageHeader.parse(resp)
            if "channel_closed" in message.MessageType:
                raise Exception("Channel closed before command output was received")
            if "output_stream_data" in message.MessageType:
                break
    finally:
        connection.close()
    payload_message = AgentMessagePayload.parse(resp[message.HeaderLength :])
    return payload_message.Payload


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
