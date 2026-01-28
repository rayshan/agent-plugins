# Style Guide (Shell)

Note: this is distilled from the Google Shell Style Guide located at https://google.github.io/styleguide/shellguide.html.

### I. Files & Interpreter

* **Interpreter:** Use Bash only. Start executables with `#!/bin/bash` and minimal flags. Use `set` to configure shell options.
* **Extensions:**
* **Executables:** No extension (preferred) or `.sh`.
* **Libraries:** Must use `.sh` and be not executable.


* **Security:** SUID/SGID forbidden.

### II. Formatting

* **Indent:** 2 spaces, **no tabs** (except `<<-` here-docs).
* **Line Length:** Max 80 chars. Split pipelines 1 segment per line (pipe on newline, 2-space indent).
* **Control Flow:**
* `; then` and `; do` on same line as keyword.
* `else`, `fi`, `done` on own lines.
* **Case:** Indent alternatives 2 spaces. Multi-line actions require split pattern/action/`;;`.



### III. Naming & Structure

* **Functions:** `lower_snake_case()`. Separate libraries with `::`. Include `main()` at bottom if script has other functions.
* **Invocation:** Last line of script must be `main "$@"`.


* **Variables:**
* **Local:** `lower_snake_case`. **Must** use `local` inside functions.
* **Critical:** Separate declaration and assignment to capture exit codes (e.g., `local x; x=$(cmd)`).
* **Constants/Env:** `UPPER_SNAKE_CASE`. Use `readonly` or `export`.


* **Files:** `lower_snake_case.sh`.

### IV. Syntax & Features

* **Quoting (Strict):**
* Always quote vars containing strings/command subs: `"${var}"`.
* Exception: Literal integers or internal integer vars (e.g., `$?`, `$#`).
* Use arrays for lists (avoids quoting issues): `"${array[@]}"`.


* **Tests:** Use `[[ ... ]]` (preferred) over `[ ... ]` or `test`.
* Use quotes on LHS `[[ "${var}" == "val" ]]`.
* Use `-z`/`-n` for empty checks.


* **Arithmetic:** Use `(( ... ))` or `$(( ... ))`. Do not use `let` or `expr`.
* **Loops:** Prefer `while read ... < <(cmd)` or `readarray` over `cmd | while` to avoid subshell variable loss.
* **Wildcards:** Use explicit paths (e.g., `rm ./*` instead of `rm *`) to prevent flag interpretation.
* **Forbidden:** `eval`, `alias`, backticks `` ``, `expr`.

### V. Documentation

* **File Header:** Top-level description required.
* **Function Comments:** Required for all non-trivial/library functions. Format: Description, Globals, Arguments, Outputs, Returns.
* **TODO:** `# TODO(username): description`.

### VI. Execution Best Practices

* **Arguments:** Always use long-form flags (e.g. `--output_dir` vs `-o`).
* **Output:** Error messages to `STDERR`.
* **Return Codes:** Check all return values (`if` or `$?`). Use `PIPESTATUS` for pipes.
* **Builtins:** Prefer builtins (e.g. bash parameter expansion, regex `=~`) over external `sed`/`awk`.