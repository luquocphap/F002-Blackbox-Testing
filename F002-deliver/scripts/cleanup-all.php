<?php
// Delete only resources identified by F002 ownership manifests.
require __DIR__ . '/fixture.php';
f002_suite_main('cleanup', $argv);
