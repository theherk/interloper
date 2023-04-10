# interloper

Tool to run ecs execute command in Python and in AWS Lambda. Of course, locally you can do this via the session manager plugin, but it you want to do it in lambda, it is a bit more complex.

## Features

- Run simple commands or full scripts.
- Pass arguments into those scripts.
- Get output back in python.

## Limitations

Here are some of the current limitations.

- Script output is truncated if very long.
- Testing shell is present, but still must be completed.
    + Still needs started really.
    + Need to mock away the websocket bits.
- This documentation.

# Installation

    pip install interloper

# Usage

For starters, one must [enable ECS exec](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-exec.html#ecs-exec-enabling-and-using).

## Locally

    ./interloper.py [event]

## Lambda

You can import and use the provided handlers for simple operations.

### cmd_handler

``` python
from interloper import cmd_handler
```

... Actually, that should be sufficient. Just set the handler to `main.cmd_handler` or whatever your module is called in place of main.

### script_handler

``` python
from interloper import script_handler
```

Then create an interloper.sh that suits your needs.

### Custom Handler and Script

Consider needing to generate heap dumps and thread dumps from java containers. You could do so with the following.

#### dumper.sh

``` sh
#!/usr/bin/env sh

cleanup () {
    rm -rf /tmp/dumps
    mkdir -p /tmp/dumps
}

verify_awscli () {
    if which aws >/dev/null
    then
        echo "awscli found; proceeding"
        return 0
    else
        echo "awscli not found; can't proceed"
        return 1
    fi
}

verify_jattach () {
    if which jattach >/dev/null
    then
        echo "jattach found; proceeding"
        return 0
    else
        echo "jattach not installed; installing"
        if which apk >/dev/null
        then
            apk add --no-cache jattach --repository http://dl-cdn.alpinelinux.org/alpine/edge/community/
            return 0
        else
            echo "apk not found; can't proceed"
            return 1
        fi
    fi
}

cleanup

case "$1" in
    heap)
        if verify_jattach; then jattach $(pgrep java) dumpheap /tmp/dumps/heap.hprof; fi
        if verify_awscli; then aws s3 cp /tmp/dumps/heap.hprof s3://"$2"; fi
        ;;
    threads)
        if verify_jattach; then jattach $(pgrep java) threaddump > /tmp/dumps/threads; fi
        if verify_awscli; then aws s3 cp /tmp/dumps/threads s3://"$2"; fi
        ;;
    *)
        echo "usage: $0 {heap|threads} {key}"
esac
```

#### handler

``` python
import logging
import time

import interloper


LOG = logging.getLogger()
LOG.setLevel(logging.INFO)


def lambda_handler(event: dict, context) -> None:
    LOG.debug("event received: %s", event)
    input = interloper.Input(**event)
    key = "{}/{}/{}-{}".format(input.cluster, input.task, input.cmd, int(time.time()))
    if input.cmd == "heap":
        key += ".hprof"
    output = interloper.Interloper(
        input.task, cluster=input.cluster, container=input.container
    ).script("dumper.sh", [input.cmd, key])
    LOG.info(output)
```
