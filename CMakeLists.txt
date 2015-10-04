project(tmp2)
add_executable(tmp2 t.cpp u.cpp)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O0 -std=c++11 -fno-omit-frame-pointer -g -fno-exceptions -ftest-coverage -fprofile-arcs")
