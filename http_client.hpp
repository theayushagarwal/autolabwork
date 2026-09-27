#pragma once
#include <string>
#include <vector>
#include <stdexcept>
#include <algorithm>
#include <curl/curl.h>

namespace http {

inline size_t write_callback(void* contents, size_t size, size_t nmemb, void* userp) {
    size_t total = size * nmemb;
    static_cast<std::string*>(userp)->append(static_cast<char*>(contents), total);
    return total;
}

struct Response {
    long status_code = 0;
    std::string body;
};

// Thread-safe RAII helper for curl global init / cleanup
struct CurlGlobalInitializer {
    CurlGlobalInitializer() {
        curl_global_init(CURL_GLOBAL_DEFAULT);
    }
    ~CurlGlobalInitializer() {
        curl_global_cleanup();
    }
};

inline void ensure_curl_initialized() {
    static CurlGlobalInitializer s_initializer;
}

// Generic request supporting GET/POST/DELETE with a JSON body, custom headers, and configurable timeout.
inline Response request(const std::string& url,
                         const std::string& method,
                         const std::string& body = "",
                         const std::vector<std::string>& extra_headers = {},
                         long timeout_seconds = 60L) {
    ensure_curl_initialized();

    CURL* curl = curl_easy_init();
    if (!curl) {
        throw std::runtime_error("Failed to initialize curl");
    }

    Response resp;
    struct curl_slist* headers = nullptr;
    headers = curl_slist_append(headers, "Content-Type: application/json");
    headers = curl_slist_append(headers, "User-Agent: AutoCode/1.0");
    for (const auto& h : extra_headers) {
        headers = curl_slist_append(headers, h.c_str());
    }

    curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_callback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &resp.body);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, timeout_seconds);
    curl_easy_setopt(curl, CURLOPT_CONNECTTIMEOUT, std::max(1L, std::min(timeout_seconds, 2L)));

    if (method == "POST") {
        curl_easy_setopt(curl, CURLOPT_POSTFIELDS, body.c_str());
        curl_easy_setopt(curl, CURLOPT_POSTFIELDSIZE, static_cast<long>(body.size()));
    } else if (method == "DELETE") {
        curl_easy_setopt(curl, CURLOPT_CUSTOMREQUEST, "DELETE");
    }
    // GET is curl's default

    CURLcode res = curl_easy_perform(curl);
    if (res != CURLE_OK) {
        curl_slist_free_all(headers);
        curl_easy_cleanup(curl);
        throw std::runtime_error(std::string("curl request failed: ") + curl_easy_strerror(res));
    }

    curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &resp.status_code);

    curl_slist_free_all(headers);
    curl_easy_cleanup(curl);
    return resp;
}

inline Response post(const std::string& url, const std::string& json_body,
                      const std::vector<std::string>& extra_headers = {},
                      long timeout_seconds = 60L) {
    return request(url, "POST", json_body, extra_headers, timeout_seconds);
}

inline Response get(const std::string& url,
                     const std::vector<std::string>& extra_headers = {},
                     long timeout_seconds = 60L) {
    return request(url, "GET", "", extra_headers, timeout_seconds);
}

} // namespace http
