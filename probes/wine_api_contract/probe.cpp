// Export discovery only: never invoke the resolved function or an OEM DLL.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdio>

namespace {
constexpr wchar_t kApiSet[] = L"api-ms-win-core-file-fromapp-l1-1-0.dll";
constexpr char kExport[] = "CreateFileFromAppW";

void begin(const char* step) {
    std::printf("{\"event\":\"begin\",\"step\":\"%s\"}\n", step);
    std::fflush(stdout);
}

void result(const char* step, bool success, DWORD error) {
    // Preserve the exact Win32 value. Failure without a supplied code gets
    // E_FAIL as the derived HRESULT, not a fabricated Win32 error code.
    const HRESULT hr = success ? S_OK :
        (error ? HRESULT_FROM_WIN32(error) : E_FAIL);
    std::printf("{\"event\":\"result\",\"step\":\"%s\",\"success\":%s,"
                "\"win32_error\":%lu,\"hresult\":\"0x%08lX\"}\n",
                step, success ? "true" : "false", static_cast<unsigned long>(error),
                static_cast<unsigned long>(static_cast<DWORD>(hr)));
    std::fflush(stdout);
}

void summary(bool loaded, const char* export_exists, const char* cleanup) {
    std::printf("{\"event\":\"summary\",\"api_set_loaded\":%s,"
                "\"export_exists\":%s,\"cleanup_complete\":%s,"
                "\"export_called\":false,\"behavior_qualified\":false,"
                "\"full_dv_qualified\":false}\n",
                loaded ? "true" : "false", export_exists, cleanup);
    std::fflush(stdout);
}
} // namespace

int main(int argc, char**) {
    std::puts("{\"event\":\"scope\",\"schema\":1,"
              "\"api_set\":\"api-ms-win-core-file-fromapp-l1-1-0.dll\","
              "\"export\":\"CreateFileFromAppW\","
              "\"contract\":\"module_load_and_export_existence_only\"}");
    std::fflush(stdout);
    if (argc != 1) {
        result("no_arguments", false, ERROR_INVALID_PARAMETER);
        summary(false, "null", "null");
        return 1;
    }
    begin("LoadLibraryExW_system32_api_set");
    SetLastError(ERROR_SUCCESS);
    const HMODULE module = LoadLibraryExW(kApiSet, nullptr, LOAD_LIBRARY_SEARCH_SYSTEM32);
    const DWORD load_error = module ? ERROR_SUCCESS : GetLastError();
    result("LoadLibraryExW_system32_api_set", module != nullptr, load_error);
    if (!module) {
        summary(false, "null", "null");
        return 2;
    }
    begin("GetProcAddress_CreateFileFromAppW");
    SetLastError(ERROR_SUCCESS);
    const FARPROC address = GetProcAddress(module, kExport);
    const DWORD export_error = address ? ERROR_SUCCESS : GetLastError();
    result("GetProcAddress_CreateFileFromAppW", address != nullptr, export_error);
    // Deliberately no cast or invocation of address: a non-null export may be
    // a stub, forwarder, or unsupported implementation, not usable behavior.
    begin("FreeLibrary_api_set");
    SetLastError(ERROR_SUCCESS);
    const BOOL unloaded = FreeLibrary(module);
    const DWORD unload_error = unloaded ? ERROR_SUCCESS : GetLastError();
    result("FreeLibrary_api_set", unloaded != FALSE, unload_error);
    summary(true, address ? "true" : "false", unloaded ? "true" : "false");
    if (!address) return 3;
    return unloaded ? 0 : 4;
}
