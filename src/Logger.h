#ifndef LOGGER_H
#define LOGGER_H

#include <stdio.h>
#include <chrono>
#include <sstream>
#include "OpenSourceLibraries/date.h"

enum class LogLevel
{
    Normal = 0,
    Info,
    Verbose,
    Debug
};

class Logger
{
public:
    Logger(LogLevel) {};
    virtual ~Logger() {}

    template<typename... TArgs>
    inline void Log(LogLevel level, const char* str, TArgs&&... args)
    {
        auto now = std::chrono::system_clock::now();
        // auto in_time_t = std::chrono::system_clock::to_time_t(now);

        auto today = date::floor<date::days>(now);

        std::stringstream ss;
        // ss << today << ' ' << date::make_time(now - today) << " UTC";
        ss << date::make_time(now - today);
        auto strtime = ss.str();
        // puts(strtime.c_str());

        char buf[300] = {};
        std::strncpy(buf, strtime.c_str(), sizeof(buf));
        snprintf(buf + strlen(buf), sizeof(buf) - strlen(buf), str, std::forward<TArgs>(args)..., nullptr);
        puts(buf);
    }
};

#endif
