#include "vm.h"
#include <stdio.h>
#include "debug.h"
#include <string.h>
#include <signal.h>

bool stop_interpreting = false;

#if defined(_WIN32) || defined(WIN32)
#include <windows.h>

// Handler for Ctrl+C events
BOOL CtrlHandler(DWORD fdwCtrlType) {
    if (fdwCtrlType == CTRL_C_EVENT) {
        stop_interpreting = true;
        return TRUE;
    }
    return FALSE;
}
#else
static void sigint_handler(int sig) {
    (void) sig;
    stop_interpreting = true;
}
#endif

#if defined(_WIN32) || defined(WIN32)
__declspec(dllexport)
#endif
int run_vm(int byte_count, char* code) {
    program_bytes_t program = {byte_count, code};

#if defined(_WIN32) || defined(WIN32)
    if (!SetConsoleCtrlHandler(CtrlHandler, TRUE)) {
        fprintf(stderr, "Error setting control handler.\n");
    }
#else
    signal(SIGINT, sigint_handler);
#endif

    vm_init(&program);

#ifdef DEBUG_DUMP_VM
    debug_vm_dump();
    int res = interpret();
    debug_vm_dump();
#else
    int res = interpret();
#endif
    vm_free();
    // fflush(stdout);
    // fflush(stderr);
    return res;
}
