cmake_minimum_required(VERSION 3.10)

project(project VERSION 0.0.1)
set(CMAKE_C_STANDARD 99)

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/bin)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/lib) # it's just a headache otherwise

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
    message("Setting default CMAKE_BUILD_TYPE=" ${CMAKE_BUILD_TYPE})
endif()

if(CMAKE_BUILD_TYPE STREQUAL "Debug")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -fsanitize=undefined -g")
elseif(CMAKE_BUILD_TYPE STREQUAL "Release")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -O3")
endif()


add_subdirectory(include)
add_subdirectory(vm)
