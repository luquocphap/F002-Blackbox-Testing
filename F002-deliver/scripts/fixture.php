<?php
/** F002 CLI fixtures. Mutations use Moodle APIs; database access is read-only. */
if (PHP_SAPI !== 'cli') {
    http_response_code(403);
    exit('CLI only');
}
if (!defined('CLI_SCRIPT')) {
    define('CLI_SCRIPT', true);
}

function f002_bootstrap(): string {
    global $CFG, $DB;
    $root = getenv('F002_MOODLE_ROOT') ?: '/var/www/site/moodle';
    require $root . '/config.php';
    require_once $CFG->dirroot . '/course/lib.php';
    require_once $CFG->dirroot . '/user/lib.php';
    require_once $CFG->libdir . '/enrollib.php';
    require_once $CFG->libdir . '/gradelib.php';
    \core\session\manager::set_user(get_admin());
    return make_writable_directory($CFG->dataroot . '/f002-fixtures');
}

/** Shared by all entry points: no two fixture commands can mutate concurrently. */
function f002_lock(string $path) {
    $lock = fopen($path, 'c');
    if (!$lock || !flock($lock, LOCK_EX | LOCK_NB)) {
        if ($lock) {
            fclose($lock);
        }
        throw new RuntimeException('Another fixture command holds lock: ' . $path);
    }
    return $lock;
}

function f002_load(string $file, string $tc): ?array {
    if (!is_file($file)) {
        return null;
    }
    $state = json_decode(file_get_contents($file), true, 512, JSON_THROW_ON_ERROR);
    if (!is_array($state) || ($state['tc'] ?? '') !== $tc
            || !is_string($state['token'] ?? null)
            || !preg_match('/^[a-f0-9]{32}$/D', $state['token'])) {
        throw new RuntimeException('Invalid ownership manifest; refusing mutation');
    }
    if (array_key_exists('schema', $state) && $state['schema'] !== 2) {
        throw new RuntimeException('Unsupported manifest schema; refusing mutation');
    }
    if (($state['schema'] ?? null) === 2
            && !in_array($state['phase'] ?? null, ['building', 'ready', 'cleaned'], true)) {
        throw new RuntimeException('Invalid manifest lifecycle phase');
    }
    if (array_key_exists('courseid', $state) && (!is_int($state['courseid']) || $state['courseid'] <= 0)) {
        throw new RuntimeException('Invalid manifest course ID');
    }
    if (array_key_exists('users', $state)) {
        if (!is_array($state['users'])) {
            throw new RuntimeException('Invalid manifest users');
        }
        foreach ($state['users'] as $suffix => $id) {
            if (!in_array($suffix, ['u1', 'u2', 'u3'], true) || !is_int($id) || $id <= 0) {
                throw new RuntimeException('Invalid manifest user ID');
            }
        }
        if (count(array_unique($state['users'])) !== count($state['users'])) {
            throw new RuntimeException('Duplicate user IDs in manifest');
        }
    }
    return array_intersect_key($state, array_flip([
        'schema', 'tc', 'token', 'phase', 'courseid', 'users',
        'prepared_at', 'instanceid', 'roleid', 'gradeitemid',
    ]));
}

function f002_key(array $state): string {
    return 'f002_' . substr($state['tc'], -3) . '_' . $state['token'];
}

/** Do not continue mutations/claim READY in a transaction left open by a failed API. */
function f002_check_transaction(): void {
    global $DB;
    if ($DB->is_transaction_started()) {
        throw new RuntimeException('Open Moodle transaction; refusing further fixture work in this process');
    }
}

function f002_create(string $file, array &$state): void {
    global $CFG, $DB;
    $tc = $state['tc'];
    $key = f002_key($state);
    $n = (int)substr($tc, -3);
    $plugin = enrol_get_plugin('manual');
    if (!$plugin || !enrol_is_enabled('manual')) {
        throw new RuntimeException('Manual enrolment plugin is not enabled');
    }
    $role = $DB->get_record('role', ['shortname' => 'student'], '*', MUST_EXIST);
    $category = $DB->get_record('course_categories', ['id' => 1], '*', MUST_EXIST);
    $now = time();
    $course = create_course((object)[
        'category' => $category->id, 'fullname' => 'F002 ' . $tc . ' ' . $state['token'],
        'shortname' => $key, 'idnumber' => $key, 'summary' => $key,
        'summaryformat' => FORMAT_PLAIN, 'visible' => 1, 'format' => 'topics',
        'startdate' => strtotime('yesterday 00:00 UTC'), 'enddate' => 0,
    ]);
    $state['courseid'] = (int)$course->id;
    f002_save($file, $state);
    $users = [];
    foreach (['u1', 'u2', 'u3'] as $suffix) {
        $username = $key . '_' . $suffix;
        $users[$suffix] = (int)user_create_user((object)[
            'username' => $username, 'auth' => 'manual', 'password' => 'F002!Local2026x',
            'firstname' => 'F002', 'lastname' => $tc . ' ' . $suffix . ' ' . $state['token'],
            'email' => $username . '@example.invalid', 'confirmed' => 1,
            'mnethostid' => $CFG->mnet_localhost_id, 'idnumber' => $username,
            'description' => $key, 'descriptionformat' => FORMAT_PLAIN,
            'timezone' => 'UTC', 'lang' => 'en',
        ]);
        $state['users'] = $users;
        f002_save($file, $state);
    }
    foreach (enrol_get_instances($course->id, false) as $instance) {
        $p = enrol_get_plugin($instance->enrol);
        if (!$p) {
            throw new RuntimeException('Cannot remove default enrolment method');
        }
        $p->delete_instance($instance);
    }
    $instanceid = $plugin->add_instance($course, [
        'status' => ENROL_INSTANCE_ENABLED, 'roleid' => $role->id,
        'enrolperiod' => 0, 'expirynotify' => 0, 'customint1' => 0,
    ]);
    $instance = $DB->get_record('enrol', ['id' => $instanceid], '*', MUST_EXIST);
    if (in_array($n, [4, 16, 17, 19, 25], true)) {
        $end = $n === 19 ? $now - 3600 : $now + 7 * DAYSECS;
        $plugin->enrol_user($instance, $users['u1'], $role->id, $now - 2 * DAYSECS,
            $end, $n === 17 ? ENROL_USER_SUSPENDED : ENROL_USER_ACTIVE);
    }
    if ($n === 26) {
        if (!empty($CFG->disablegradehistory)) {
            throw new RuntimeException('BLOCKED: grade history disabled; do not change global config');
        }
        $item = new grade_item([
            'courseid' => $course->id, 'itemtype' => 'manual',
            'itemname' => 'F002 Recovery 73', 'idnumber' => $key . '_grade',
            'gradetype' => GRADE_TYPE_VALUE, 'grademin' => 0, 'grademax' => 100,
        ], false);
        if (!$item->insert('f002-fixture')) {
            throw new RuntimeException('Cannot create grade item');
        }
        $state['gradeitemid'] = (int)$item->id;
        f002_save($file, $state);
        // u1 recovery ON; u2 identical history recovery OFF; u3 has no history.
        foreach (['u1', 'u2'] as $suffix) {
            $plugin->enrol_user($instance, $users[$suffix], $role->id);
            $item->update_final_grade($users[$suffix], 73, 'f002-fixture');
            $plugin->unenrol_user($instance, $users[$suffix]);
            $grade = grade_grade::fetch(['itemid' => $item->id, 'userid' => $users[$suffix]]);
            if ($grade) {
                $grade->delete('f002-fixture');
            }
            if (!$DB->record_exists('grade_grades_history', [
                'itemid' => $item->id, 'userid' => $users[$suffix], 'finalgrade' => 73,
            ])) {
                throw new RuntimeException('Grade history fixture did not retain 73');
            }
        }
    }
    $state['prepared_at'] = $now;
    $state['instanceid'] = (int)$instanceid;
    $state['roleid'] = (int)$role->id;
    $state['phase'] = 'ready';
    f002_save($file, $state);
}

function f002_save(string $file, array $state): void {
    $temp = $file . '.tmp';
    $oldmask = umask(0077);
    try {
        if (file_put_contents($temp, json_encode($state, JSON_THROW_ON_ERROR)) === false
                || !rename($temp, $file)) {
            throw new RuntimeException('Cannot persist ownership state');
        }
    } finally {
        umask($oldmask);
    }
    if (!chmod($file, 0600)) {
        throw new RuntimeException('Cannot restrict manifest permissions');
    }
}

/** Resolve by both marker and persisted ID, checking ALL guards before deleting anything. */
function f002_owned_resources(string $key, array $state): array {
    global $DB;
    $course = $DB->get_record('course', ['idnumber' => $key]);
    $byid = empty($state['courseid']) ? false : $DB->get_record('course', ['id' => $state['courseid']]);
    if ($byid && (!$course || (int)$byid->id !== (int)$course->id)) {
        throw new RuntimeException('Manifest course ID/marker mismatch; refusing deletion');
    }
    if ($course && ($course->shortname !== $key || $course->summary !== $key
            || $course->idnumber !== $key || (int)$course->id === (int)SITEID
            || (!empty($state['courseid']) && (int)$state['courseid'] !== (int)$course->id))) {
        throw new RuntimeException('Course ownership mismatch; refusing deletion');
    }
    $users = [];
    foreach (['u1', 'u2', 'u3'] as $suffix) {
        $name = $key . '_' . $suffix;
        $user = $DB->get_record('user', ['username' => $name, 'deleted' => 0]);
        $id = $state['users'][$suffix] ?? null;
        $byid = $id ? $DB->get_record('user', ['id' => $id, 'deleted' => 0]) : false;
        if ($byid && (!$user || (int)$byid->id !== (int)$user->id)) {
            throw new RuntimeException('Manifest user ID/marker mismatch; refusing deletion');
        }
        if ($user) {
            if ($user->idnumber !== $name || $user->description !== $key || is_siteadmin($user)
                    || ($id && (int)$id !== (int)$user->id)) {
                throw new RuntimeException('User ownership mismatch; refusing deletion');
            }
            $users[$suffix] = $user;
        }
    }
    return ['course' => $course, 'users' => $users];
}

function f002_cleanup(string $key, array $state): void {
    $resources = f002_owned_resources($key, $state);
    if ($resources['course'] && !delete_course($resources['course'], false)) {
        throw new RuntimeException('Course deletion failed; manifest retained');
    }
    foreach ($resources['users'] as $user) {
        if (!user_delete_user($user)) {
            throw new RuntimeException('User deletion failed; manifest retained');
        }
    }
    f002_check_transaction();
    $remaining = f002_owned_resources($key, $state);
    if ($remaining['course'] || $remaining['users']) {
        throw new RuntimeException('Live owned resources remain; manifest retained');
    }
}

function f002_require(bool $condition, string $message): void {
    if (!$condition) {
        throw new RuntimeException($message);
    }
}

/** Read-only baseline check. READY is a precondition result, never a business-test PASS. */
function f002_verify(array $state): void {
    global $CFG, $DB;
    f002_check_transaction();
    f002_require(($state['schema'] ?? null) === 2 && ($state['phase'] ?? '') === 'ready',
        'Incomplete/legacy manifest; data preserved. Run cleanup before setup');
    foreach (['prepared_at', 'courseid', 'instanceid', 'roleid'] as $field) {
        f002_require(isset($state[$field]) && is_int($state[$field]) && $state[$field] > 0,
            'Invalid manifest field: ' . $field);
    }
    $key = f002_key($state);
    $courseStart = strtotime('yesterday 00:00 UTC', $state['prepared_at']);
    $customStart = strtotime(gmdate('Y-m-d 12:00', $state['prepared_at'] + 2 * DAYSECS) . ' UTC');
    $resources = f002_owned_resources($key, $state);
    $course = $resources['course'];
    f002_require((bool)$course && count($resources['users']) === 3, 'Missing owned course/users');
    f002_require($course->fullname === 'F002 ' . $state['tc'] . ' ' . $state['token']
        && (int)$course->visible === 1 && (int)$course->startdate === $courseStart, 'Course baseline changed');
    f002_require(count($state['users'] ?? []) === 3, 'Missing user IDs in manifest');
    $role = $DB->get_record('role', ['shortname' => 'student'], '*', MUST_EXIST);
    f002_require((int)$role->id === $state['roleid'], 'Student role mapping changed');
    f002_require((bool)enrol_get_plugin('manual') && enrol_is_enabled('manual'), 'Manual plugin unavailable');
    $instances = enrol_get_instances($course->id, false);
    f002_require(count($instances) === 1, 'Course must have exactly one enrolment method');
    $instance = reset($instances);
    f002_require($instance->enrol === 'manual' && (int)$instance->status === ENROL_INSTANCE_ENABLED
        && (int)$instance->id === $state['instanceid'] && (int)$instance->roleid === (int)$role->id
        && (int)$instance->enrolperiod === 0, 'Manual enrolment baseline changed');
    $n = (int)substr($state['tc'], -3);
    $preenrolled = in_array($n, [4, 16, 17, 19, 25], true);
    $expectedcount = $preenrolled ? 1 : 0;
    f002_require($DB->count_records('user_enrolments', ['enrolid' => $instance->id]) === $expectedcount,
        'Participant baseline changed; existing test data preserved');
    $context = context_course::instance($course->id);
    f002_require($DB->count_records('role_assignments', ['contextid' => $context->id]) === $expectedcount,
        'Course role baseline changed');
    $now = time();
    foreach ($resources['users'] as $suffix => $user) {
        f002_require((int)$state['users'][$suffix] === (int)$user->id && $user->auth === 'manual'
            && (int)$user->confirmed === 1 && (int)$user->suspended === 0
            && $user->timezone === 'UTC' && $user->lang === 'en'
            && $user->email === $key . '_' . $suffix . '@example.invalid', 'User baseline changed: ' . $suffix);
        $expected = $preenrolled && $suffix === 'u1';
        // Includes every course/method, so another source of access cannot mask a failure.
        $enrolments = $DB->get_records('user_enrolments', ['userid' => $user->id]);
        $assignments = $DB->get_records('role_assignments', ['userid' => $user->id]);
        f002_require(count($enrolments) === ($expected ? 1 : 0)
            && count($assignments) === ($expected ? 1 : 0), 'User enrolment/role baseline changed: ' . $suffix);
        if ($expected) {
            $ue = reset($enrolments);
            $assignment = reset($assignments);
            $end = $n === 19 ? $state['prepared_at'] - 3600 : $state['prepared_at'] + 7 * DAYSECS;
            f002_require((int)$ue->enrolid === (int)$instance->id
                && (int)$ue->status === ($n === 17 ? ENROL_USER_SUSPENDED : ENROL_USER_ACTIVE)
                && (int)$ue->timestart === $state['prepared_at'] - 2 * DAYSECS
                && (int)$ue->timeend === $end, 'Pre-enrolled state/time changed');
            f002_require((int)$assignment->contextid === (int)$context->id
                && (int)$assignment->roleid === (int)$role->id
                // Manual enrolments use unprotected roles: role_assign defaults are '' and 0.
                && $assignment->component === ''
                && (int)$assignment->itemid === 0, 'Student role assignment changed');
            f002_require($n === 19 ? $end < $now : $end > $now + 300, 'Pre-enrolled time window is stale');
        }
    }
    if (in_array($n, [12, 13, 14, 18, 21, 24], true)) {
        f002_require($customStart > $now + 300, 'Custom start S is stale; explicit reset required');
    }
    if ($n === 27) {
        f002_require($courseStart === strtotime('yesterday 00:00 UTC'),
            'Course-start fixture is stale for the manual testcase');
    }
    if ($n === 26) {
        f002_require(empty($CFG->disablegradehistory), 'Grade history disabled');
        $item = $DB->get_record('grade_items', ['courseid' => $course->id, 'idnumber' => $key . '_grade']);
        f002_require((bool)$item && (int)$item->id === ($state['gradeitemid'] ?? null)
            && $item->itemtype === 'manual' && $item->itemname === 'F002 Recovery 73'
            && (int)$item->gradetype === GRADE_TYPE_VALUE && (float)$item->grademin === 0.0
            && (float)$item->grademax === 100.0, 'Recovery grade item missing/changed');
        foreach ($resources['users'] as $suffix => $user) {
            f002_require(!$DB->record_exists('grade_grades', ['itemid' => $item->id, 'userid' => $user->id]),
                'Recovery fixture has a current grade');
            $has73 = $DB->record_exists('grade_grades_history', [
                'itemid' => $item->id, 'userid' => $user->id, 'finalgrade' => 73,
            ]);
            f002_require($suffix === 'u3' ? !$DB->record_exists('grade_grades_history', [
                'itemid' => $item->id, 'userid' => $user->id,
            ]) : $has73, 'Recovery history/control baseline missing/changed');
        }
    }
}

/** Run the two supported commands; terminal output is not an execution report. */
function f002_suite_main(string $action, array $argv): void {
    if (count($argv) !== 1 || !in_array($action, ['setup', 'cleanup'], true)) {
        fwrite(STDERR, "Usage: php {$action}-all.php (no arguments)\n");
        exit(2);
    }
    $suiteLock = null;
    $completed = 0;
    $ready = [];
    try {
        $dir = f002_bootstrap();
        $suiteLock = f002_lock($dir . '/suite.lock');
        for ($n = 1; $n <= 28; $n++) {
            $tc = sprintf('TC-002-%03d', $n);
            $caseLock = null;
            try {
                // Retain per-case locks to coordinate with existing fixture commands.
                $caseLock = f002_lock($dir . '/' . $tc . '.lock');
                f002_check_transaction();
                $file = $dir . '/' . $tc . '.json';
                $state = f002_load($file, $tc);
                if ($action === 'cleanup') {
                    if ($state !== null) {
                        f002_cleanup(f002_key($state), $state);
                        // Remove ownership only after all owned resources are gone.
                        if (!unlink($file)) {
                            throw new RuntimeException('Cannot remove ownership manifest');
                        }
                    }
                    $completed++;
                    continue;
                }
                if ($state === null || ($state['phase'] ?? '') === 'cleaned') {
                    if ($state !== null) {
                        $resources = f002_owned_resources(f002_key($state), $state);
                        if ($resources['course'] || $resources['users']) {
                            throw new RuntimeException('Cleaned manifest has live resources; run cleanup first');
                        }
                    }
                    // Persist token before creating resources so partial setup is cleanable.
                    $state = ['schema' => 2, 'tc' => $tc, 'token' => bin2hex(random_bytes(16)), 'phase' => 'building'];
                    f002_save($file, $state);
                    f002_create($file, $state);
                }
                // Existing fixtures are never silently reset or duplicated.
                $ready[$tc] = $state;
            } catch (Throwable $e) {
                fwrite(STDERR, "{$tc}: {$e->getMessage()}\n");
            } finally {
                if ($caseLock) {
                    fclose($caseLock);
                }
            }
        }
        if ($action === 'setup') {
            // Validate all baselines after creation, including time-sensitive fixtures.
            foreach ($ready as $tc => $state) {
                $caseLock = null;
                try {
                    $caseLock = f002_lock($dir . '/' . $tc . '.lock');
                    f002_verify($state);
                    $key = f002_key($state);
                    $start = gmdate('Y-m-d 12:00', $state['prepared_at'] + 2 * DAYSECS);
                    echo "{$tc}: course=F002 {$tc} {$state['token']}; courseid={$state['courseid']}; username_prefix={$key}; "
                        . "S={$start} UTC; prepared_at={$state['prepared_at']}\n";
                    $completed++;
                } catch (Throwable $e) {
                    fwrite(STDERR, "{$tc}: {$e->getMessage()}\n");
                } finally {
                    if ($caseLock) {
                        fclose($caseLock);
                    }
                }
            }
        }
    } catch (Throwable $e) {
        fwrite(STDERR, "TC-002-001..TC-002-028: " . ucfirst($action)
            . " unavailable before processing fixtures: {$e->getMessage()}\n");
    } finally {
        if ($suiteLock) {
            fclose($suiteLock);
        }
    }
    $label = ucfirst($action);
    if ($completed === 28) {
        echo "{$label} completed: 28/28 test cases.\n";
        exit(0);
    }
    fwrite(STDERR, "{$label} failed: {$completed}/28 test cases completed.\n");
    exit(1);
}
