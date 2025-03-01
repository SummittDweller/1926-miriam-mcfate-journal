Jekyll::Hooks.register :site, :post_write do |site|
  system("pagefind --site '_site'")
end
