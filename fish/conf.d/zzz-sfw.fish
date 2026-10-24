# Load after tool setup, including zz-pnpm.fish, before creating wrappers.
if type -q sfw
  if type -q npm
    alias npm="sfw npm"
  end

  if type -q pnpm
    alias pnpm="sfw pnpm"
  end

  if type -q cargo
    alias cargo="sfw cargo"
  end

  if type -q uv
    alias uv="sfw uv"
  end

  if type -q pip
    alias pip="sfw pip"
  end
end
