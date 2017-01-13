FROM debian:latest

WORKDIR /build
COPY requirements.txt /build/requirements.txt
COPY requirements-dev.txt /build/requirements-dev.txt

RUN apt-get update; \
    apt-get install -y python-setuptools python-numpy python-dev libgdal-dev python-gdal swig git g++; \
    easy_install pip; pip install wheel;

RUN \
    pip install -r requirements.txt; \
    pip install -r requirements-dev.txt;

