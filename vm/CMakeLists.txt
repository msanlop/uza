set(SOURCES
    main.c
    chunk.c
    vm.c
    debug.c
    serialize.c
    object.c
    value.c
    memory.c
    table.c
    native.c
)

add_library(vm SHARED ${SOURCES})
target_include_directories(vm PUBLIC ${CMAKE_SOURCE_DIR}/include)
install(TARGETS vm)
