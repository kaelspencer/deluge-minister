cmake_minimum_required(VERSION 3.7.2)
project (cpp-playground)

# set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++17 -stdlib=libc++ -nostdinc++ -fcoroutines-ts")
SET(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -stdlib=libc++")

add_compile_options(-std=c++17)
# add_compile_options(-stdlib=libc++)
add_compile_options(-nostdinc++)
add_compile_options(-fcoroutines-ts)

INCLUDE_DIRECTORIES(/home/kael/code/OpenSource/llvm/projects/libcxx/include/)

add_executable(consumer main.cpp)
add_executable(producer producer.cpp)
