#!/usr/bin/env bash

if [[ -d "${HOME}/.config/fish" ]]; then
  rm -rf "${HOME}/.config/fish"
fi

./manage install
