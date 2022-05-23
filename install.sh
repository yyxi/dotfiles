#!/usr/bin/env bash

if [ -n "$GITPOD_WORKSPACE_ID" ]; then
  sudo apt-add-repository ppa:fish-shell/release-3
  sudo apt update
  sudo apt install fish

  if [[ -d "${HOME}/.config/fish" ]]; then
    rm -rf "${HOME}/.config/fish"
  fi

  ./manage install
fi
