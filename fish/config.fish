# Do not show any greeting
set --universal --erase fish_greeting

if status is-interactive
  # Commands to run in interactive sessions can go here
end

if isatty
  set -x GPG_TTY (tty)
end

fish_add_path $HOME/bin
fish_add_path $HOME/.dotfiles/bin
fish_add_path $HOME/.local/bin/

if test -d /usr/local/opt/coreutils/libexec/gnubin
  fish_add_path /usr/local/opt/coreutils/libexec/gnubin
end

if test -d /usr/local/opt/gnu-tar/libexec/gnubin
  fish_add_path /usr/local/opt/gnu-tar/libexec/gnubin
end

if test -d /usr/local/opt/gnu-sed/libexec/gnubin
  fish_add_path /usr/local/opt/gnu-sed/libexec/gnubin
end

if test -d /usr/local/opt/curl/bin
  fish_add_path jusr/local/opt/curl/bin
end

# /opt/homebrew/bin /usr/local/bin /usr/bin /bin /opt/homebrew/sbin /usr/local/sbin /usr/sbin /sbin

set -x LS_COLORS "rs=0:di=00;01:ln=00:mh=00:pi=00:so=00:do=00:bd=00;01:cd=00;01:or=00;07:mi=00;07:su=00:sg=00:ca=00:tw=00:ow=00:st=00:ex=00:*.tar=00:*.tgz=00:*.arc=00:*.arj=00:*.taz=00:*.lha=00:*.lz4=00:*.lzh=00:*.lzma=00:*.tlz=00:*.txz=00:*.tzo=00:*.t7z=00:*.zip=00:*.z=00:*.dz=00:*.gz=00:*.lrz=00:*.lz=00:*.lzo=00:*.xz=00:*.zst=00:*.tzst=00:*.bz2=00:*.bz=00:*.tbz=00:*.tbz2=00:*.tz=00:*.deb=00:*.rpm=00:*.jar=00:*.war=00:*.ear=00:*.sar=00:*.rar=00:*.alz=00:*.ace=00:*.zoo=00:*.cpio=00:*.7z=00:*.rz=00:*.cab=00:*.wim=00:*.swm=00:*.dwm=00:*.esd=00:*.jpg=00:*.jpeg=00:*.mjpg=00:*.mjpeg=00:*.gif=00:*.bmp=00:*.pbm=00:*.pgm=00:*.ppm=00:*.tga=00:*.xbm=00:*.xpm=00:*.tif=00:*.tiff=00:*.png=00:*.svg=00:*.svgz=00:*.mng=00:*.pcx=00:*.mov=00:*.mpg=00:*.mpeg=00:*.m2v=00:*.mkv=00:*.webm=00:*.ogm=00:*.mp4=00:*.m4v=00:*.mp4v=00:*.vob=00:*.qt=00:*.nuv=00:*.wmv=00:*.asf=00:*.rm=00:*.rmvb=00:*.flc=00:*.avi=00:*.fli=00:*.flv=00:*.gl=00:*.dl=00:*.xcf=00:*.xwd=00:*.yuv=00:*.cgm=00:*.emf=00:*.ogv=00:*.ogx=00:*.aac=00:*.au=00:*.flac=00:*.m4a=00:*.mid=00:*.midi=00:*.mka=00:*.mp3=00:*.mpc=00:*.ogg=00:*.ra=00:*.wav=00:*.oga=00:*.opus=00:*.spx=00:*.xspf=00:"
set -x GREP_COLOR "7"
set -x GREP_COLORS "mt=$GREP_COLOR"
set -x FZF_DEFAULT_OPTS "--color bw"
set -x _ZO_FZF_OPTS "--color bw"

alias ls="ls --group-directories-first --color=auto"

if test -d $HOME/.neovim-dist/bin
  fish_add_path $HOME/.neovim-dist/bin
end

if test -d $HOME/.local/share/pnpm
  set -gx PNPM_HOME "$HOME/.local/share/pnpm"
  fish_add_path $PNPM_HOME
end

if type -q tmux
  alias tmux="~/.dotfiles/scripts/tmux/_tmux"
end

if type -q nvim
  alias vi=nvim
  alias vim=nvim

  set -x EDITOR nvim
  set -x VISUAL nvim
end

function fish_user_key_bindings
  fish_default_key_bindings -M insert
  fish_vi_key_bindings --no-erase insert
  bind -M insert \cC 'echo; commandline ""; commandline -f repaint'
  bind v edit_command_buffer
end
