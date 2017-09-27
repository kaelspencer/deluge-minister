#include <stdio.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
#include <fcntl.h>
#include <stdlib.h>
#include <errno.h>
#include <aio.h>
#include <poll.h>

void async_read(sigval val)
{
    puts("callback");
    struct aiocb *ptr = (struct aiocb *)val.sival_ptr;
    printf("read=%s", (char *)ptr->aio_buf);
}

void read_fd(int fd)
{
    char buf[100] = {};
    (void)read(fd, buf, sizeof(buf));
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

    // while (true)
    // {
    //     char buf[1024] = {};
    //     int result = read(fd, buf, sizeof(buf));

    //     while (result <= 0)
    //     {
    //         puts("sleeping...");
    //         sleep(1);
    //         result = read(fd, buf, sizeof(buf));
    //     }

    //     puts(buf);
    // }



    // struct aiocb cb = {};
    // char sbuf[100];
    // int ret;

    // // bzero(&cb, sizeof(cb));
    // // memset(&cb, sizeof(cb));

    // cb.aio_fildes = fd;
    // cb.aio_buf = sbuf;
    // cb.aio_nbytes = 100;
    // cb.aio_offset = 0;

    // cb.aio_sigevent.sigev_value.sival_ptr = &cb;
    // cb.aio_sigevent.sigev_notify = SIGEV_THREAD;
    // cb.aio_sigevent.sigev_notify_function = async_read;
    // cb.aio_sigevent.sigev_notify_attributes = NULL;
    // cb.aio_sigevent.sigev_signo = SIGUSR1;

    // ret = aio_read(&cb);

    // if (ret == -1) {
    //     perror("aio_read");
    //     exit(1);
    // }

    // puts("sleeping");

    // while (1) {
    //     sleep(3);
    // }


    return 0;
}
