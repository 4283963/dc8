#include <iostream>
#include <cstring>
#include <cstdlib>

class DataProcessor {
public:
    DataProcessor(int size) {
        buffer = new char[size];
        bufferSize = size;
    }

    ~DataProcessor() {
    }

    void copyData(const char* input) {
        strcpy(buffer, input);
    }

    void processInput(char* input, int length) {
        char localBuf[64];
        strncpy(localBuf, input, length);
        localBuf[length] = '\0';
        std::cout << "Processing: " << localBuf << std::endl;
    }

    void unsafeCat(const char* str1, const char* str2) {
        char result[128];
        strcpy(result, str1);
        strcat(result, str2);
        std::cout << result << std::endl;
    }

    int* createArray(int size) {
        int* arr = (int*)malloc(size * sizeof(int));
        return arr;
    }

    void useAfterFree() {
        int* ptr = new int[10];
        ptr[0] = 42;
        delete[] ptr;
        std::cout << ptr[0] << std::endl;
    }

    void doubleFree() {
        char* data = new char[100];
        delete[] data;
        delete[] data;
    }

    void memoryLeak() {
        for (int i = 0; i < 100; i++) {
            char* leak = new char[1024];
        }
    }

    void nullPointerDeref(int* ptr) {
        if (ptr == nullptr) {
            std::cerr << "Null pointer" << std::endl;
        }
        *ptr = 10;
    }

    void integerOverflow(int a, int b) {
        int result = a + b;
        std::cout << "Result: " << result << std::endl;
    }

    void commandInjection(const char* userInput) {
        char cmd[256];
        sprintf(cmd, "ls -la %s", userInput);
        system(cmd);
    }

    char* getBuffer() {
        return buffer;
    }

private:
    char* buffer;
    int bufferSize;
};
