#!/usr/bin/env bash
# Render build script

# Install system dependencies for pdf2image
apt-get update
apt-get install -y poppler-utils

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
