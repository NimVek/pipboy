### Format of DemoMode.bin

```C
struct  String {
    uint size;
    char str[size];
};

struct Entry {
    uint8_t type;
    uint32_t id;
    switch (type) {
        case 0: // Native
            uint8_t native;
            switch (native) {
                case 2:
                    float64_t floating_point;
                    break;
                case 4:
                    uint64_t integer;
                    break;
                case 5:
                    uint8_t boolean;
                    break;
                case 6:
                    String string;
                    break;
            }
        case 1: // List
            uint32_t count;
            for ( i = 0; i < count; i++) {
                uint32_t id;
                Entry e;
            }
            break;
        case 2: // Dictionary
            uint32_t count;
            for ( i = 0; i < count; i++) {
                String name;
                Entry e;
            }
            break;
    }
};
```
