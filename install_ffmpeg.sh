#!/bin/bash
mkdir -p bin
curl -sL https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz | tar -xJ --strip-components=1 -C bin
chmod +x bin/ffmpeg

