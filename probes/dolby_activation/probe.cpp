// Bounded contract discovery only. No registration, negotiation or playback.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <activation.h>
#include <roapi.h>
#include <winstring.h>
#include <mfapi.h>
#include <mferror.h>
#include <mftransform.h>
#include <cstdio>
#include <cstring>
#include <cwchar>
#include <vector>

namespace {
constexpr DWORD kStreamLimit = 16;
constexpr DWORD kTypeLimit = 64;
constexpr wchar_t kClass[] = L"DolbyVisionPlugin.RendererEffect";

const char* hr_name(HRESULT hr) {
    switch (hr) {
    case S_OK: return "S_OK";
    case S_FALSE: return "S_FALSE";
    case E_NOTIMPL: return "E_NOTIMPL";
    case E_NOINTERFACE: return "E_NOINTERFACE";
    case E_INVALIDARG: return "E_INVALIDARG";
    case E_POINTER: return "E_POINTER";
    case E_ACCESSDENIED: return "E_ACCESSDENIED";
    case REGDB_E_CLASSNOTREG: return "REGDB_E_CLASSNOTREG";
    case CLASS_E_CLASSNOTAVAILABLE: return "CLASS_E_CLASSNOTAVAILABLE";
    case RPC_E_CHANGED_MODE: return "RPC_E_CHANGED_MODE";
    case MF_E_NO_MORE_TYPES: return "MF_E_NO_MORE_TYPES";
    case MF_E_TRANSFORM_TYPE_NOT_SET: return "MF_E_TRANSFORM_TYPE_NOT_SET";
    case MF_E_INVALIDSTREAMNUMBER: return "MF_E_INVALIDSTREAMNUMBER";
    default: return "unmapped_hresult";
    }
}

void begin(const char* step) {
    std::printf("{\"event\":\"begin\",\"step\":\"%s\"}\n", step);
    std::fflush(stdout);
}

bool report(const char* step, HRESULT hr, const char* disposition = nullptr) {
    std::printf("{\"event\":\"result\",\"step\":\"%s\","
                "\"hresult\":\"0x%08lX\",\"hresult_name\":\"%s\","
                "\"disposition\":\"%s\"}\n", step,
                static_cast<unsigned long>(static_cast<DWORD>(hr)),
                hr_name(hr), disposition ? disposition :
                (SUCCEEDED(hr) ? "continue" : "stop_missing_contract"));
    std::fflush(stdout);
    return SUCCEEDED(hr);
}

HRESULT loader_error() {
    const DWORD error = GetLastError();
    return error ? HRESULT_FROM_WIN32(error) : E_FAIL;
}

template<class T> bool resolve(HMODULE module, const char* name, T& function) {
    begin(name);
    const FARPROC address = GetProcAddress(module, name);
    if (!address) return report(name, loader_error());
    static_assert(sizeof(function) == sizeof(address), "ABI pointer size");
    std::memcpy(&function, &address, sizeof(function));
    return report(name, S_OK);
}

template<class T> struct Interface {
    T* value = nullptr;
    ~Interface() { if (value) value->Release(); }
    Interface() = default;
    Interface(const Interface&) = delete;
    Interface& operator=(const Interface&) = delete;
};

struct Runtime {
    HMODULE combase = nullptr, mfplat = nullptr, plugin = nullptr;
    bool com_started = false, ro_started = false, mf_started = false;
    decltype(&RoInitialize) ro_initialize = nullptr;
    decltype(&RoUninitialize) ro_uninitialize = nullptr;
    decltype(&WindowsCreateString) create_string = nullptr;
    decltype(&WindowsDeleteString) delete_string = nullptr;
    decltype(&MFStartup) mf_startup = nullptr;
    decltype(&MFShutdown) mf_shutdown = nullptr;

    bool close() {
        // run() has released all interfaces/HSTRING. Drain MF before unloading
        // the plugin, because outstanding MF work may still refer to its code.
        bool clean = true;
        if (mf_started) {
            begin("MFShutdown");
            clean = report("MFShutdown", mf_shutdown());
        }
        if (plugin) {
            begin("unload_plugin");
            const bool unloaded = report("unload_plugin",
                FreeLibrary(plugin) ? S_OK : loader_error());
            clean = unloaded && clean;
        }
        if (ro_started) ro_uninitialize();
        if (com_started) CoUninitialize();
        if (mfplat) FreeLibrary(mfplat);
        if (combase) FreeLibrary(combase);
        return clean;
    }
};

struct String {
    Runtime& runtime;
    HSTRING value = nullptr;
    ~String() { if (value) runtime.delete_string(value); }
};

void guid(char (&buffer)[37], const GUID& value) {
    std::snprintf(buffer, sizeof(buffer),
        "%08lX-%04X-%04X-%02X%02X-%02X%02X%02X%02X%02X%02X",
        static_cast<unsigned long>(value.Data1), value.Data2, value.Data3,
        value.Data4[0], value.Data4[1], value.Data4[2], value.Data4[3],
        value.Data4[4], value.Data4[5], value.Data4[6], value.Data4[7]);
}

bool enumerate(IMFTransform* transform, DWORD stream, bool input) {
    const char* step = input ? "GetInputAvailableType" : "GetOutputAvailableType";
    for (DWORD index = 0; index < kTypeLimit; ++index) {
        Interface<IMFMediaType> type;
        begin(step);
        const HRESULT hr = input ?
            transform->GetInputAvailableType(stream, index, &type.value) :
            transform->GetOutputAvailableType(stream, index, &type.value);
        if (hr == MF_E_NO_MORE_TYPES) {
            report(step, hr, "enumeration_complete");
            return true;
        }
        if (!report(step, hr)) return false;
        if (!type.value) return report("media_type_nonnull", E_POINTER);
        GUID major{}, subtype{};
        if (!report("MF_MT_MAJOR_TYPE", type.value->GetGUID(MF_MT_MAJOR_TYPE, &major)))
            return false;
        if (!report("MF_MT_SUBTYPE", type.value->GetGUID(MF_MT_SUBTYPE, &subtype)))
            return false;
        char major_text[37], subtype_text[37];
        guid(major_text, major);
        guid(subtype_text, subtype);
        std::printf("{\"event\":\"media_type\",\"direction\":\"%s\","
                    "\"stream_id\":%lu,\"type_index\":%lu,"
                    "\"major_guid\":\"%s\",\"subtype_guid\":\"%s\"}\n",
                    input ? "input" : "output", static_cast<unsigned long>(stream),
                    static_cast<unsigned long>(index), major_text, subtype_text);
        std::fflush(stdout);
    }
    report(step, HRESULT_FROM_WIN32(ERROR_MORE_DATA), "stop_type_limit");
    return false;
}

bool run(Runtime& runtime, int argc, wchar_t** argv) {
    // Full Windows paths only: prevent implicit DLL name/search-path selection.
    const bool drive_path = argc == 2 && std::wcslen(argv[1]) >= 3 &&
        ((argv[1][0] >= L'A' && argv[1][0] <= L'Z') ||
         (argv[1][0] >= L'a' && argv[1][0] <= L'z')) &&
        argv[1][1] == L':' && argv[1][2] == L'\\';
    const bool unc_path = argc == 2 && std::wcslen(argv[1]) >= 3 &&
        argv[1][0] == L'\\' && argv[1][1] == L'\\';
    if (!drive_path && !unc_path) return report("absolute_dll_argument", E_INVALIDARG);
    begin("CoInitializeEx_MTA");
    if (!report("CoInitializeEx_MTA", CoInitializeEx(nullptr, COINIT_MULTITHREADED)))
        return false;
    runtime.com_started = true;
    begin("load_combase_system32");
    runtime.combase = LoadLibraryExW(L"combase.dll", nullptr, LOAD_LIBRARY_SEARCH_SYSTEM32);
    if (!report("load_combase_system32", runtime.combase ? S_OK : loader_error()))
        return false;
    if (!resolve(runtime.combase, "RoInitialize", runtime.ro_initialize) ||
        !resolve(runtime.combase, "RoUninitialize", runtime.ro_uninitialize) ||
        !resolve(runtime.combase, "WindowsCreateString", runtime.create_string) ||
        !resolve(runtime.combase, "WindowsDeleteString", runtime.delete_string)) return false;
    begin("RoInitialize_MTA");
    if (!report("RoInitialize_MTA", runtime.ro_initialize(RO_INIT_MULTITHREADED)))
        return false;
    runtime.ro_started = true;
    begin("load_mfplat_system32");
    runtime.mfplat = LoadLibraryExW(L"mfplat.dll", nullptr, LOAD_LIBRARY_SEARCH_SYSTEM32);
    if (!report("load_mfplat_system32", runtime.mfplat ? S_OK : loader_error()))
        return false;
    if (!resolve(runtime.mfplat, "MFStartup", runtime.mf_startup) ||
        !resolve(runtime.mfplat, "MFShutdown", runtime.mf_shutdown)) return false;
    begin("MFStartup_NOSOCKET");
    if (!report("MFStartup_NOSOCKET", runtime.mf_startup(MF_VERSION, MFSTARTUP_NOSOCKET)))
        return false;
    runtime.mf_started = true;
    begin("load_exact_plugin");
    runtime.plugin = LoadLibraryExW(argv[1], nullptr,
        LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_SYSTEM32);
    if (!report("load_exact_plugin", runtime.plugin ? S_OK : loader_error()))
        return false;
    using GetFactory = HRESULT (WINAPI*)(HSTRING, IActivationFactory**);
    GetFactory get_factory = nullptr;
    if (!resolve(runtime.plugin, "DllGetActivationFactory", get_factory)) return false;
    String class_id{runtime};
    begin("WindowsCreateString_class");
    if (!report("WindowsCreateString_class", runtime.create_string(kClass,
        static_cast<UINT32>(std::wcslen(kClass)), &class_id.value))) return false;
    Interface<IActivationFactory> factory;
    begin("DllGetActivationFactory_class");
    if (!report("DllGetActivationFactory_class", get_factory(class_id.value, &factory.value)))
        return false;
    if (!factory.value) return report("activation_factory_nonnull", E_POINTER);
    Interface<IInspectable> instance;
    begin("ActivateInstance");
    if (!report("ActivateInstance", factory.value->ActivateInstance(&instance.value)))
        return false;
    if (!instance.value) return report("instance_nonnull", E_POINTER);
    Interface<IMFTransform> transform;
    begin("QueryInterface_IMFTransform");
    if (!report("QueryInterface_IMFTransform", instance.value->QueryInterface(
        IID_IMFTransform, reinterpret_cast<void**>(&transform.value)))) return false;
    if (!transform.value) return report("transform_nonnull", E_POINTER);
    DWORD inputs = 0, outputs = 0;
    begin("GetStreamCount");
    if (!report("GetStreamCount", transform.value->GetStreamCount(&inputs, &outputs)))
        return false;
    std::printf("{\"event\":\"stream_count\",\"inputs\":%lu,\"outputs\":%lu}\n",
        static_cast<unsigned long>(inputs), static_cast<unsigned long>(outputs));
    if (inputs > kStreamLimit || outputs > kStreamLimit) {
        report("stream_count_bound", HRESULT_FROM_WIN32(ERROR_MORE_DATA), "stop_stream_limit");
        return false;
    }
    std::vector<DWORD> input_ids(inputs), output_ids(outputs);
    begin("GetStreamIDs");
    const HRESULT ids = transform.value->GetStreamIDs(inputs, input_ids.data(),
        outputs, output_ids.data());
    if (ids == E_NOTIMPL) {
        report("GetStreamIDs", ids, "documented_consecutive_ids");
        for (DWORD i = 0; i < inputs; ++i) input_ids[i] = i;
        for (DWORD i = 0; i < outputs; ++i) output_ids[i] = i;
    } else if (!report("GetStreamIDs", ids)) return false;
    for (DWORD stream : input_ids) if (!enumerate(transform.value, stream, true)) return false;
    for (DWORD stream : output_ids) if (!enumerate(transform.value, stream, false)) return false;
    return true;
}
} // namespace

int wmain(int argc, wchar_t** argv) {
    std::puts("{\"event\":\"scope\",\"schema\":1,\"class\":"
              "\"DolbyVisionPlugin.RendererEffect\",\"qualification\":"
              "\"activation_and_unconfigured_types_only\",\"full_dv_qualified\":false}");
    std::fflush(stdout);
    Runtime runtime;
    const bool complete = run(runtime, argc, argv);
    const bool clean = runtime.close();
    std::printf("{\"event\":\"summary\",\"contract_discovery_complete\":%s,"
                "\"cleanup_complete\":%s,\"full_dv_qualified\":false}\n",
                complete ? "true" : "false", clean ? "true" : "false");
    return complete && clean ? 0 : 2;
}
