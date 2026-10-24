if type -q walk
  function ll
    cd (walk $argv);
  end
end
