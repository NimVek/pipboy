### Format of DemoMode.bin

```C
struct  String {
    uint32_t length;
    char str[length];
};

struct Value {
    uint8_t type;
    uint32_t id;
    switch (type) {
        case 0: // Primitive
            uint8_t primitive;
            switch (primitive) {
                case 0:
                    sint32_t integer;
                    break;
                case 1:
                    uint32_t integer;
                    break;
                case 2:
                    sint64_t integer;
                    break;
                case 3:
                    float32_t floating_point;
                    break;
                case 4:
                    float64_t floating_point;
                    break;
                case 5:
                    uint8_t boolean;
                    break;
                case 6:
                    String string;
                    break;
            }
        case 1: // Array
            uint32_t count;
            for ( i = 0; i < count; i++) {
                uint32_t index;
                Value v;
            }
            break;
        case 2: // Object
            uint32_t count;
            for ( i = 0; i < count; i++) {
                String key;
                Value v;
            }
            break;
    }
};
```
