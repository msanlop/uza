#include "chunk.h"

#include <CUnit/CUnit.h>
#include <CUnit/Basic.h>

void test_test(void) {
    CU_ASSERT(1 == 1);
}

int main() {
    CU_initialize_registry();

    CU_pSuite suite = CU_add_suite("Suite1", 0, 0);
    CU_add_test(suite, "test1", test_test);

    CU_basic_set_mode(CU_BRM_VERBOSE);
    CU_basic_run_tests();

    int fails = CU_get_number_of_failures();
    CU_cleanup_registry();

    return fails;
}
