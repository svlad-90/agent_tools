# C++ code workflow

These rules apply to C and C++ code under the workspace root.

Assembly files follow the local kernel style: use a tab between the
instruction mnemonic and operands (for example `mov	x1, x0`), matching
the surrounding `.S` files.

When explaining C/C++ or assembly changes, follow the workspace guidance in
`AGENTS.md` for introducing low-level systems concepts in plain language before
naming exact symbols or APIs.

1. Use `agent_tools/tools/cpp_light_code_map` as the first C/C++ orientation
   tool when the build environment, compile database, generated headers, or
   container setup is not yet established. This includes early task scoping,
   first-pass file reading, rough symbol discovery, quick local fixes, and
   guarded structural edits that do not require type information.

   ```sh
   python -m agent_tools.tools.cpp_light_code_map diagnose path/to/file.c --json
   python -m agent_tools.tools.cpp_light_code_map outline path/to/file.c --compact
   python -m agent_tools.tools.cpp_light_code_map symbols path/to/file.c --kind function
   python -m agent_tools.tools.cpp_light_code_map refs path/to/file.c --name identifier --scope function_name --json
   ```

   `cpp_light_code_map` is tree-sitter based. It is intentionally
   structural-only: it does not validate types, include resolution, generated
   headers, compiler macros, ABI details, or compilation. Treat its spans,
   hashes, calls, refs, locals, complexity, and rename/body edit support as a
   fast working map, not as proof that the program is correct.
2. Move to `agent_tools/tools/cpp_code_map` once the build environment is
   selected and reasonably stable: the source checkout is known, the container
   or toolchain is chosen, generated headers exist, and the translation unit has
   or should have a valid `compile_commands.json` entry. From that point,
   `cpp_code_map` is the required precision tool for exact symbol maps,
   symbol-level analysis, guarded C/C++ edits, review comments, and
   diagram/audit work.
3. Run commands from the workspace root with:

   ```sh
   python -m agent_tools.tools.cpp_light_code_map <command> ...
   python -m agent_tools.tools.cpp_code_map <command> ...
   ```

4. Prefer passing the build directory or compile database explicitly once using
   `cpp_code_map`:

   ```sh
   python -m agent_tools.tools.cpp_code_map map path/to/file.cpp \
     --compile-db path/to/build
   ```

5. Run `cpp_code_map` in the project's real build environment. If the project
   is built in Docker or another container, run the tool inside that same
   image or through the PAF `environments` domain container alias so compiler
   paths, generated headers, sysroots, and module paths match the build. A
   host-side copy of `compile_commands.json` with container paths is not a
   complete substitute for the build environment.

6. For a task that is mainly about C or C++ code, start with
   `cpp_light_code_map diagnose` and `outline` if the build context is still
   fluid. Before precise implementation, review, or semantic source analysis,
   establish a working `cpp_code_map` context. This means `map` must succeed for
   at least one relevant translation unit using the real build directory or
   compile database needed by the task. If that context is missing, generate or
   locate the proper `compile_commands.json` in the build environment first.
   Do not treat repeated `cpp_code_map` failures as a harmless warning once the
   task depends on exact C/C++ understanding.

7. Before reading or changing an existing C or C++ source file during early
   orientation or an unsettled environment phase, inspect its structure with
   `cpp_light_code_map`:

   ```sh
   python -m agent_tools.tools.cpp_light_code_map diagnose path/to/file.cpp --json
   python -m agent_tools.tools.cpp_light_code_map outline path/to/file.cpp --compact
   ```

   Once the build context is stable, inspect the same file with `cpp_code_map`:

   ```sh
   python -m agent_tools.tools.cpp_code_map map path/to/file.cpp \
     --compile-db path/to/build
   ```

8. Before changing an existing class, function, method, or C function in the
   stable build phase, resolve its exact span and current hash with
   `cpp_code_map`:

   ```sh
   python -m agent_tools.tools.cpp_code_map symbol-get path/to/file.cpp \
     --symbol Qualified::Name --compile-db path/to/build
   ```

   For quick structural edits before the build context is established, use
   `cpp_light_code_map symbol-get` plus `--check-only` edit commands first, and
   record that the edit has only structural validation until the normal build or
   `cpp_code_map` path runs.

9. After C or C++ edits, use the project's normal build, test, or runtime
   validation path as the authoritative check. Use `cpp_code_map parse-check`
   when it gives useful fast feedback in the same build environment, but do
   not treat it as a substitute for the build.

   ```sh
   python -m agent_tools.tools.cpp_code_map parse-check path/to/file.cpp \
     --compile-db path/to/build
   ```

10. If no `compile_commands.json` is available and the task has moved beyond
   first-pass orientation or quick structural fixes, generate one first. For CMake
   projects, prefer:

   ```sh
   cmake -S . -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
   ```

11. If `cpp_code_map` cannot process a file because libclang, the build
   environment, or a compile database is missing, keep using
   `cpp_light_code_map` only for orientation and quick structural work while
   fixing the environment context. Report the limitation explicitly before doing
   precise C/C++ implementation or review work, and promote the task back to
   `cpp_code_map` as soon as the build environment is formalized and stable.
