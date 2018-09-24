#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <unistd.h>
#include <experimental/string_view>
#include <chrono>
#include <experimental/coroutine>
#include "coroutine_types.h"
#include <future>
#include "Logger.h"

class NamedPipeReader
{
public:
    NamedPipeReader(std::experimental::string_view pipePath) :
        m_pipePath(pipePath),
        m_logger(LogLevel::Debug)
    {};

    virtual ~NamedPipeReader()
    {
        if (m_pipeFileDescriptor != 0)
        {
            ::close(m_pipeFileDescriptor);
        }
    }

    void StartPolling()
    {
        ReopenFile();

        while (true)
        {
            pollfd pfd = {};
            pfd.fd = m_pipeFileDescriptor;
            pfd.events = POLLIN;
            pfd.revents = 0;

            // This method will block for the timeout duration or until something is written to the pipe.
            int pollResult = ::poll(&pfd, 1, m_pollTimeoutMS);

            // A return value of 0 means a timeout, just loop.
            if (pollResult == -1)
            {
                perror("Something went wrong with poll");
                ReopenFile();
            }
            else if (pollResult > 0)
            {
                if (pfd.revents & POLLIN)
                {
                    // Something was written to the pipe.
                    m_logger.Log(LogLevel::Normal, "Poll result: %d, POLLIN received", pollResult);

                    ReadAndPrintPipe();
                }
                else if (pfd.revents & POLLHUP)
                {
                    m_logger.Log(LogLevel::Normal, "Poll result: %d, POLLHUP received, reopening file", pollResult);
                    ReopenFile();
                }
                else
                {
                    m_logger.Log(LogLevel::Normal, "Poll result: %d, revents: %d", pollResult, pfd.revents);
                }
            }
        }
    }

private:
    void ReopenFile()
    {
        if (m_pipeFileDescriptor != 0)
        {
            ::close(m_pipeFileDescriptor);
        }

        // This combination of flags for open will not block.
        m_pipeFileDescriptor = ::open(m_pipePath.c_str(), O_RDONLY | O_NONBLOCK);
        m_logger.Log(LogLevel::Normal, "Opened file");
    }

    void ReadAndPrintPipe()
    {
        char buf[1024] = {};
        int result = ::read(m_pipeFileDescriptor, buf, sizeof(buf));

        if (result == -1 && errno == EAGAIN)
        {
            // We need to go back to poll().
            m_logger.Log(LogLevel::Normal, "Received EAGAIN from read");
            return;
        }

        if (result < 0)
        {
            perror("read");
        }
        else if (result == 0)
        {
            m_logger.Log(LogLevel::Normal, "read returned 0, closing and reopening file");
            ReopenFile();
        }
        else
        {
            m_logger.Log(LogLevel::Normal, buf);
        }
    }

    std::string m_pipePath;
    int m_pipeFileDescriptor = 0;
    int m_pollTimeoutMS = 5000;
    Logger m_logger;
};

generator<int> f()
{
    for (int i = 0; i < 5; i++)
    {
        co_yield i;
        sleep(3);
    }
}

std::future<int> g()
{
    co_return 23;
}

// https://stackoverflow.com/questions/15055065/o-rdwr-on-named-pipes-with-poll
int main()
{
    int v = co_await g();
    printf("%d", v);
    fflush(stdout);

    for (auto i : f())
    {
        printf("%d", i);
        fflush(stdout);
    }
x
    // https://linux.die.net/man/3/mkfifo
    mkfifo("foo.pipe", 0777);

    NamedPipeReader reader{"foo.pipe"};
    reader.StartPolling();

    return 0;
}
