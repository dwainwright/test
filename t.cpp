#include <stdio.h>
#include <vector>

bool debug = 0;

void b_main();

#define DEBUG(X) do { if (debug) { X; } } while(0);

class DebugFlag {
    bool enabled;

public:
    DebugFlag() : enabled(false) { }
    inline bool isEnabled() { return false; }
};

DebugFlag debugFlag;

class A {
public:
    void thing() {
        printf("thing\n");
    }

    virtual void dump() {
        printf("dump\n");
    }

    void dumpf() {
        printf("dumpf\n");
    }
};

class B : public A {
public:
    virtual void dump() { 
        printf("dumpB\n");
    }
};

int main(int argc, char **argv) {
    A a;
    a.thing();
    if (argc > 12) {
        a.dumpf();
        DEBUG(a.dump());
    }

    if (debugFlag.isEnabled()) {
        printf("log\n");
    }

    char *p = 0;

    for (int i = 0; i < (1<<15); i++) {
        a.dump();
    }

    DEBUG
        (printf("mosters\n");
         printf("catherin\n");
        );
    b_main();
}
