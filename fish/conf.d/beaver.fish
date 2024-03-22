status is-interactive || exit

# Priortiy 1 bold
# Priority 2 underline
# Priority 3
# Priority 4
# Priority 5

set -g fish_color_autosuggestion "707070"
set -g fish_color_comment "5C5C5C"
set -g fish_color_quote "F5F5F5"

set -g fish_color_cancel -r
set -g fish_color_command normal
set -g fish_color_cwd normal
set -g fish_color_cwd_root normal
set -g fish_color_end normal
set -g fish_color_error normal
set -g fish_color_escape normal
set -g fish_color_history_current normal
set -g fish_color_host normal
set -g fish_color_host_remote normal
set -g fish_color_normal normal
set -g fish_color_operator normal
set -g fish_color_param normal
set -g fish_color_redirection normal
set -g fish_color_search_match normal
set -g fish_color_selection normal
set -g fish_color_user normal
set -g fish_color_valid_path normal
set -g fish_pager_color_completion normal
set -g fish_pager_color_description normal
set -g fish_pager_color_prefix normal
set -g fish_pager_color_progress normal

function _beaver_pwd --on-variable PWD
  set --query fish_prompt_pwd_dir_length || set --local fish_prompt_pwd_dir_length 1
  set --global _beaver_pwd (
    string replace --ignore-case -- ~ \~ $PWD |
    string replace -- "/$root/" /:/ |
    string replace --regex --all -- "(\.?[^/]{"$fish_prompt_pwd_dir_length"})[^/]*/" \$1/ |
    string replace -- : "$root" |
    string replace --regex -- '([^/]+)$' "\x1b[1m\$1\x1b[22m" |
    string replace --regex --all -- '(?!^/$)/' "\x1b[2m/\x1b[22m"
  )
end

function _beaver_prompt --on-event fish_prompt
  set --query _beaver_pwd || _beaver_pwd

  if test -n "$SSH_TTY"
    set --global _beaver_hostname (prompt_login)" "
  else
    set --global _beaver_hostname ""
  end

  set --global _beaver_prompt "$_beaver_newline$_beaver_color_prompt$beaver_symbol_prompt"
end

function _beaver_uninstall --on-event beaver_uninstall
  set --names |
    string replace --filter --regex -- "^(_?beaver_)" "set --erase \$1" |
    source
  functions --erase (functions --all | string match --entire --regex "^_?beaver_")
end

set --global beaver_color_normal (set_color normal)

for color in beaver_color_{pwd,error,prompt}
  function $color --on-variable $color --inherit-variable color
    set --query $color && set --global _$color (set_color $$color)
  end && $color
end

set --query beaver_color_error || set --global beaver_color_error $fish_color_error
set --query beaver_symbol_prompt || set --global beaver_symbol_prompt '$'
