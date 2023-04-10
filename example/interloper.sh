#!/usr/bin/env sh
verify_apk() {
    if which apk >/dev/null; then
        return 0
    fi
    echo "apk not found; can't proceed"
    exit 1
}

verify_awscli() {
    if which aws >/dev/null; then
        echo "awscli found; proceeding"
        return 0
    fi
    # if verify_apk; then apk add --no-cache aws-cli --repository http://dl-cdn.alpinelinux.org/alpine/edge/community/; fi
    if verify_apk; then apk add --no-cache aws-cli; fi
}

cat /etc/hosts
if verify_awscli; then aws sts get-caller-identity; fi
