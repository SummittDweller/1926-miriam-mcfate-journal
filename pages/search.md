---
layout: default
title: Pagefind Search
permalink: /search/
---
   
<link href="/pagefind/pagefind-ui.css" rel="stylesheet">
<script src="/pagefind/pagefind-ui.js"></script>
   
<div id="search"></div>
<p style="text-align: center; font-size: 0.7em">Powered by <a target="_blank" href="https://pagefind.app/">Pagefind</a></p>
   
<script>
    window.addEventListener('DOMContentLoaded', (event) => {
        new PagefindUI({ element: "#search", showSubResults: true });
    });
</script>
