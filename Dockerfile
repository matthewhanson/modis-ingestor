FROM modispds:base

WORKDIR /build

COPY ./ /build/

RUN \
    pip install .