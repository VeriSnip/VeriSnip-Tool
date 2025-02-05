module FAdd_tb;
  reg [31:0] a, b;
  wire [31:0] out;

  FAdd uut (
      .a(a),
      .b(b),
      .out(out)
  );

  initial begin
    $display("Testing fadd:");

    // Test 1: 1.5 + 2.5 = 4.0
    a = 32'h3FC00000;  // 1.5
    b = 32'h40200000;  // 2.5
    #1 $display("%f + %f = %f (Exp: 4.0)", $bitstoreal(a), $bitstoreal(b), $bitstoreal(out));

    // Test 2: -1.0 + 1.0 = 0
    a = 32'hBF800000;  // -1.0
    b = 32'h3F800000;  // 1.0
    #1 $display("%f + %f = %f (Exp: 0.0)", $bitstoreal(a), $bitstoreal(b), $bitstoreal(out));

    // Test 3: Infinity + 5.0 = Infinity
    a = 32'h7F800000;  // +Inf
    b = 32'h40A00000;  // 5.0
    #1 $display("%f + %f = %f (Exp: Inf)", $bitstoreal(a), $bitstoreal(b), $bitstoreal(out));

    $finish;
  end
endmodule
