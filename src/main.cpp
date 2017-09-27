#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <unistd.h>

void read_fd(int fd)
{
    char buf[1024] = {};
    int result = read(fd, buf, sizeof(buf));

    if (result == -1 && errno == EAGAIN)
    {
        // We need to go back to poll().
        puts("Received EAGAIN from read");
        return;
    }

    puts(buf);
}

// https://stackoverflow.com/questions/15055065/o-rdwr-on-named-pipes-with-poll
int main()
{
    // https://linux.die.net/man/3/mkfifo
    mkfifo("foo.pipe", 0777);
    auto fd = open("foo.pipe", O_RDONLY | O_NONBLOCK);
    puts("Opened file");

    while (true)
    {
        pollfd pfd = {};
        pfd.fd = fd;
        pfd.events = POLLIN;
        pfd.revents = 0;

        int pollResult = poll(&pfd, 1, 5000);
        printf("Poll result: %d\n", pollResult);
        fflush(stdout);

        if (pollResult > 0)
        {
            read_fd(pfd.fd);
        }
        else if (pollResult == 0)
        {
            continue;
        }
        else
        {
            perror("poll");
            exit(1);
        }
    }

    return 0;
}
