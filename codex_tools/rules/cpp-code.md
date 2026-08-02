# C++ code workflow

These rules apply to C and C++ code under the workspace root.

Assembly files follow the local kernel style: use a tab between the
instruction mnemonic and operands (for example `mov	x1, x0`), matching
the surrounding `.S` files.

When explaining C/C++ or assembly changes, follow the workspace guidance in
`AGENTS.md` for introducing low-level systems concepts in plain language before
naming exact symbols or APIs.

1. Use `codex_tools/tools/cpp_code_map` when exact C or C++ structure matters:
   before non-trivial reading, symbol-level analysis, edits, review comments,
   or diagram/audit work. It is a precision tool for understanding and scoped
   editing; it is not the normal build-validation mechanism.
2. Run commands from the workspace root with:

   ```sh
   python -m codex_tools.tools.cpp_code_map <command> ...
   ```

3. Prefer passing the build directory or compile database explicitly:

   ```sh
   python -m codex_tools.tools.cpp_code_map map path/to/file.cpp \
     --compile-db path/to/build
   ```

4. Run `cpp_code_map` in the project's real build environment. If the project
   is built in Docker or another container, run the tool inside that same
   image or through the PAF `environments` domain container alias so compiler
   paths, generated headers, sysroots, and module paths match the build. A
   host-side copy of `compile_commands.json` with container paths is not a
   complete substitute for the build environment.

5. For a task that is mainly about C or C++ code, establish a working
   `cpp_code_map` context before continuing with implementation, review, or
   precise source analysis. This means `map` must succeed for at least one
   relevant translation unit using the real build directory or compile database
   needed by the task. If that context is missing, generate or locate the
   proper `compile_commands.json` in the build environment first. Do not
   continue by treating repeated `cpp_code_map` failures as a harmless warning.

6. Before reading or changing an existing C or C++ source file, inspect its
   structure:

   ```sh
   python -m codex_tools.tools.cpp_code_map map path/to/file.cpp \
     --compile-db path/to/build
   ```

7. Before changing an existing class, function, method, or C function, resolve
   its exact span and current hash:

   ```sh
   python -m codex_tools.tools.cpp_code_map symbol-get path/to/file.cpp \
     --symbol Qualified::Name --compile-db path/to/build
   ```

8. After C or C++ edits, use the project's normal build, test, or runtime
   validation path as the authoritative check. Use `cpp_code_map parse-check`
   when it gives useful fast feedback in the same build environment, but do
   not treat it as a substitute for the build.

   ```sh
   python -m codex_tools.tools.cpp_code_map parse-check path/to/file.cpp \
     --compile-db path/to/build
   ```

9. If no `compile_commands.json` is available, generate one first. For CMake
   projects, prefer:

   ```sh
   cmake -S . -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
   ```

10. If `cpp_code_map` cannot process a file because libclang, the build
   environment, or a compile database is missing, report the limitation
   explicitly and fix the environment context before doing precise C/C++
   implementation or review work. Use a fallback only for simple textual
   inspection, non-C/C++ surrounding files, or when the user explicitly asks to
   bypass this rule after the limitation has been reported.
