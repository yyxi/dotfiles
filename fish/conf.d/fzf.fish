set -x FZF_DEFAULT_OPTS "--color bw"
set -gx FZF_DEFAULT_COMMAND  'rg --files --color never --hidden --glob \'!.git\''

bind \cr __fzf_history_widget
bind -M insert \cr __fzf_history_widget
