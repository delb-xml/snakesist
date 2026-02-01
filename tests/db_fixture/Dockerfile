ARG EXIST_VERSION
FROM alpine AS xar-creator
COPY xar-contents/* /tmp/
RUN apk add zip \
 && cd /tmp && zip -0 -r fixture-data.xar *

FROM existdb/existdb:$EXIST_VERSION
COPY --from=xar-creator /tmp/fixture-data.xar /exist/autodeploy/
