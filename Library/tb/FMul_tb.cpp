#include "VFMul.h"
#include "verilated.h"
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include "verilated_vcd_c.h"

typedef union {
  float f;
  uint32_t u;
} FloatUnion;

typedef struct {
  VFMul *dut;
  FloatUnion a;
  FloatUnion b;
  FloatUnion result;
  int passed;
} FMulTest;

void FMul_reset(FMulTest *test) {
  test->dut->a = 0;
  test->dut->b = 0;
  test->dut->eval();
}

void FMul_run_test(FMulTest *test, float a_val, float b_val) {
  test->a.f = a_val;
  test->b.f = b_val;
  test->dut->a = test->a.u;
  test->dut->b = test->b.u;
  test->dut->eval();
  test->result.u = test->dut->out;
}

int is_nan(float f) {
  uint32_t u = *((uint32_t *)&f);
  return ((u >> 23) & 0xFF) == 0xFF && (u & 0x007FFFFF);
}

int check_result(FMulTest *test, const char *test_name, float expected) {
  int success = 0;
  const float eps = 1e-6;

  if (isnan(expected)) {
    success = is_nan(test->result.f);
  } else if (isinf(expected)) {
    success =
        isinf(test->result.f) && (signbit(test->result.f) == signbit(expected));
  } else {
    success = fabsf(test->result.f - expected) < eps &&
              (signbit(test->result.f) == signbit(expected));
  }

  if (!success) {
    test->passed = 0;
    printf("[%s] FAILED: %.9g * %.9g = %.9g (expected %.9g)\n", test_name,
           test->a.f, test->b.f, test->result.f, expected);
  } else {
    printf("[%s] Passed\n", test_name);
  }

  return success;
}

int main(int argc, char **argv) {
  Verilated::commandArgs(argc, argv);
  Verilated::traceEverOn(true);
  FMulTest test;

  test.dut = new VFMul;
  test.passed = 1;

  VerilatedVcdC *tfp = NULL;
  tfp = new VerilatedVcdC;
  test.dut->trace(tfp, 1);
  tfp->open("Verilator/FMul_tb.vcd");

  // Basic multiplication
  FMul_run_test(&test, 2.0f, 3.0f);
  check_result(&test, "Basic Multiplication", 6.0f);

  // 2nd Basic multiplication
  FMul_run_test(&test, 0.1f, 3.0f);
  check_result(&test, "2nd Basic Multiplication", 0.3f);

  // Sign handling
  FMul_run_test(&test, -2.0f, 3.0f);
  check_result(&test, "Negative Result", -6.0f);

  // Zero handling
  FMul_run_test(&test, -0.0f, -5.0f);
  check_result(&test, "Zero Multiplication", 0.0f);

  // Signed zero
  FMul_run_test(&test, -0.0f, 0.0f);
  check_result(&test, "Signed Zero", -0.0f);

  // Infinity handling
  FMul_run_test(&test, INFINITY, 5.0f);
  check_result(&test, "Infinity Multiply", INFINITY);

  // NaN propagation
  FMul_run_test(&test, NAN, 5.0f);
  check_result(&test, "NaN Propagation", NAN);

  // Inf * Zero = NaN
  FMul_run_test(&test, INFINITY, 0.0f);
  check_result(&test, "Infinity Zero", NAN);

  // Overflow
  FMul_run_test(&test, 1e38f, 1e38f);
  check_result(&test, "Overflow", INFINITY);

  // Underflow
  FMul_run_test(&test, 1e-45f, 1e-45f);
  check_result(&test, "Underflow", 0.0f);

  // Denormal handling
  FMul_run_test(&test, 1e-40f, 1e-40f); // Treated as zero
  check_result(&test, "Denormal Inputs", 0.0f);

  // One Denormal handling
  FMul_run_test(&test, 1e-40f, 1e38f); // Treated as zero
  check_result(&test, "Denormal Inputs", 0.01f);

  // Precision test
  FMul_run_test(&test, 1.0000001f, 1.0000001f);
  check_result(&test, "Precision", 1.0000002f);

  printf("\nTest Summary: %s\n",
         test.passed ? "ALL PASSED" : "FAILURES OCCURRED");

  test.dut->final();

  tfp->close();

  delete test.dut;

  return test.passed ? EXIT_SUCCESS : EXIT_FAILURE;
}