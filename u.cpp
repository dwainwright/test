#include <stdio.h>

class B {
public:
    void thing() {
        printf("cat\n");
    }

    void dump() {
        printf("b dump\n");
    }
};

int i = 0;

void b_main() {
    B b;
    b.thing();
    if (i)
        b.dump();
}
