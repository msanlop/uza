set(SOURCES
    main.c
    chunk.c
    vm.c
    debug.c
    serializer.c
    object.c
    value.c
    memory.c
)

add_library(vm SHARED ${SOURCES})
target_include_directories(vm PUBLIC ${CMAKE_SOURCE_DIR}/include)
install(TARGETS vm)
