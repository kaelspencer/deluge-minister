#include <iostream>
#include "AppArguments.h"

using namespace std;

void foo();

int main(int argc, char* argv[])
{
    AppArguments args;
    args.Parse(argc, argv);

    shared_ptr<int> spA = make_shared<int>(5);
    shared_ptr<AppArguments> spArgs{spA, &args};

    foo();

    cout << "boo" << endl;
    return 0;
}

void foo()
{
    // A heap allocated array. When iterating things will be in a contiguous block of memory (+cache hits)
    // This can be the list of graph nodes.
    unique_ptr<array<int, 4>> spArray = make_unique<array<int, 4>>();

    for (auto& bucket : *spArray.get())
    {
        cout << bucket << " ";
    }
}
