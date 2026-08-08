#define _GNU_SOURCE

#include <errno.h>
#include <libgen.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

static void show_error(const char *message) {
    pid_t pid = fork();
    if (pid == 0) {
        execlp("zenity", "zenity", "--error", "--title=Workspace GUI", "--text", message, NULL);
        execlp("xmessage", "xmessage", "-title", "Workspace GUI", message, NULL);
        _exit(127);
    }
    if (pid > 0) {
        int status = 0;
        waitpid(pid, &status, 0);
    }
    fprintf(stderr, "%s\n", message);
}

static int workspace_dir(char *buffer, size_t size) {
    ssize_t length = readlink("/proc/self/exe", buffer, size - 1);
    if (length < 0 || (size_t)length >= size) {
        return -1;
    }
    buffer[length] = '\0';
    char *dir = dirname(buffer);
    if (dir == NULL) {
        return -1;
    }
    memmove(buffer, dir, strlen(dir) + 1);
    return 0;
}

static void set_pythonpath(const char *workspace) {
    const char *old_value = getenv("PYTHONPATH");
    if (old_value == NULL || old_value[0] == '\0') {
        setenv("PYTHONPATH", workspace, 1);
        return;
    }

    size_t needed = strlen(workspace) + 1 + strlen(old_value) + 1;
    char *value = malloc(needed);
    if (value == NULL) {
        return;
    }
    snprintf(value, needed, "%s:%s", workspace, old_value);
    setenv("PYTHONPATH", value, 1);
    free(value);
}

static int run_python(const char *python, int argc, char **argv) {
    char **args = calloc((size_t)argc + 4, sizeof(char *));
    if (args == NULL) {
        return 127;
    }
    args[0] = (char *)python;
    args[1] = "-m";
    args[2] = "codex_tools.tools.workspace_gui";
    for (int index = 1; index < argc; ++index) {
        args[index + 2] = argv[index];
    }
    execvp(python, args);
    free(args);
    return errno == ENOENT ? 127 : 126;
}

int main(int argc, char **argv) {
    char workspace[PATH_MAX];
    if (workspace_dir(workspace, sizeof(workspace)) != 0) {
        show_error("Could not resolve the workspace-gui location.");
        return 1;
    }
    if (chdir(workspace) != 0) {
        show_error("Could not change to the workspace directory.");
        return 1;
    }
    set_pythonpath(workspace);

    int status = run_python("python3", argc, argv);
    if (status == 127) {
        status = run_python("python", argc, argv);
    }
    show_error("Workspace GUI could not start: python3/python was not found.");
    return status;
}
