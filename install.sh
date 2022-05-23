#!/usr/bin/env bash

if [ -n "$GITPOD_WORKSPACE_ID" ]; then
  sudo apt-add-repository -y ppa:fish-shell/release-3
  sudo apt install -y fish

  if [[ -d "${HOME}/.config/fish" ]]; then
    rm -rf "${HOME}/.config/fish"
  fi

  "${HOME}/.dotfiles/manage" install
fi
