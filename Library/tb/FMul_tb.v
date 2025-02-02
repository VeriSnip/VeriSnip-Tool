module FMul_Tb;
  reg [31:0] a, b;
  wire [31:0] out;

  fmul uut (
      .a  (a),
      .b  (b),
      .out(out)
  );

  initial begin
    $display("Starting Testbench...");

    // Test 1: Basic multiplication (2.0 * 3.0 = 6.0)
    a = 32'h40000000;  // 2.0
    b = 32'h40400000;  // 3.0
    #1;
    if (out !== 32'h40C00000) $display("Test 1 Failed: Got %h", out);
    else $display("Test 1 Passed");

    // Test 2: Negative multiplication (-2.0 * 3.0 = -6.0)
    a = 32'hC0000000;  // -2.0
    b = 32'h40400000;  // 3.0
    #1;
    if (out !== 32'hC0C00000) $display("Test 2 Failed: Got %h", out);
    else $display("Test 2 Passed");

    // Test 3: Zero handling (0 * 5.0 = 0)
    a = 32'h00000000;  // 0.0
    b = 32'h40A00000;  // 5.0
    #1;
    if (out !== 32'h00000000) $display("Test 3 Failed: Got %h", out);
    else $display("Test 3 Passed");

    // Test 4: Negative zero (-0 * -0 = 0)
    a = 32'h80000000;  // -0.0
    b = 32'h80000000;  // -0.0
    #1;
    if (out !== 32'h00000000) $display("Test 4 Failed: Got %h", out);
    else $display("Test 4 Passed");

    // Test 5: Infinity handling (Inf * 5.0 = Inf)
    a = 32'h7F800000;  // +Inf
    b = 32'h40A00000;  // 5.0
    #1;
    if (!(out[30:23] === 8'hFF && out[22:0] === 23'h0)) $display("Test 5 Failed: Got %h", out);
    else $display("Test 5 Passed");

    // Test 6: NaN propagation (NaN * 1.0 = NaN)
    a = 32'h7FFFFFFF;  // NaN
    b = 32'h3F800000;  // 1.0
    #1;
    if (!(out[30:23] === 8'hFF && out[22:0] !== 23'h0)) $display("Test 6 Failed: Got %h", out);
    else $display("Test 6 Passed");

    // Test 7: Inf * Zero = NaN
    a = 32'h7F800000;  // +Inf
    b = 32'h00000000;  // 0.0
    #1;
    if (!(out[30:23] === 8'hFF && out[22:0] !== 23'h0)) $display("Test 7 Failed: Got %h", out);
    else $display("Test 7 Passed");

    // Test 8: Overflow to Infinity
    a = 32'h7F7FFFFF;  // Max normal number
    b = 32'h7F7FFFFF;  // Max normal number
    #1;
    if (out !== 32'h7F800000) $display("Test 8 Failed: Got %h", out);
    else $display("Test 8 Passed");

    $display("All Tests Completed");
    $finish;
  end
endmodule
