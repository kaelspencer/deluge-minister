#include <stdio.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>

int main()
{
    auto handle = open("foo.pipe", O_WRONLY | O_NONBLOCK);

    char buf[] = "Hello from producer";
    write(handle, buf, sizeof(buf));
    close(handle);
    return 0;
}
