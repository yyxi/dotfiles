#!/usr/bin/env bash

if [ -n "$GITPOD_WORKSPACE_ID" ]; then
  sudo apt-add-repository -y ppa:fish-shell/release-3
  sudo apt install -y fish

  "${HOME}/.dotfiles/manage" install
fi
