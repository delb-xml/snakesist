FROM alpine AS xar-creator
COPY xar-contents/* /tmp/
RUN apk update && apk add zip \
 && cd /tmp && zip -0 -r fixture-data.xar *

FROM existdb/existdb:4.7.1
COPY --from=xar-creator /tmp/fixture-data.xar /exist/autodeploy/
