FROM python:3.11-slim

RUN useradd -m -s /bin/bash sandbox
USER sandbox
WORKDIR /home/sandbox
