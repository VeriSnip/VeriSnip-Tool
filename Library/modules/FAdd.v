module fadd (
    input [31:0] a,
    input [31:0] b,
    output reg [31:0] out
);

  reg a_sign, b_sign;
  reg [7:0] a_exponent, b_exponent;
  reg [22:0] a_mantissa, b_mantissa;
  reg [23:0] a_man, b_man;

  reg sign;
  reg [7:0] exponent;
  reg [23:0] mantissa;

  reg [7:0] exp_diff;
  reg [23:0] man_large, man_small;
  reg [7:0] exp_large, exp_small;
  reg sign_large, sign_small;

  reg [24:0] sum;
  reg [23:0] sub_result;
  reg [ 4:0] leading_zeros;

  reg a_is_nan, a_is_inf, a_is_zero;
  reg b_is_nan, b_is_inf, b_is_zero;
  reg nan, infinity, zero;

  integer i;

  always @(*) begin
    // Extract components
    {a_sign, a_exponent, a_mantissa} = a;
    {b_sign, b_exponent, b_mantissa} = b;

    // Handle denormals as zero
    a_man = (a_exponent != 0) ? {1'b1, a_mantissa} : 24'd0;
    b_man = (b_exponent != 0) ? {1'b1, b_mantissa} : 24'd0;

    // Special case detection
    a_is_nan = (a_exponent == 8'hFF) && (a_mantissa != 0);
    b_is_nan = (b_exponent == 8'hFF) && (b_mantissa != 0);
    a_is_inf = (a_exponent == 8'hFF) && (a_mantissa == 0);
    b_is_inf = (b_exponent == 8'hFF) && (b_mantissa == 0);
    a_is_zero = (a_exponent == 0) && (a_mantissa == 0);
    b_is_zero = (b_exponent == 0) && (b_mantissa == 0);

    // Default outputs
    nan = 0;
    infinity = 0;
    zero = 0;
    sign = 0;
    exponent = 0;
    mantissa = 0;

    // Handle special cases
    if (a_is_nan || b_is_nan) begin
      nan = 1;
    end else if (a_is_inf || b_is_inf) begin
      if (a_is_inf && b_is_inf) begin
        infinity = (a_sign == b_sign) ? 1 : (nan = 1);
      end else begin
        infinity = 1;
        sign = a_is_inf ? a_sign : b_sign;
      end
    end else if (a_is_zero && b_is_zero) begin
      zero = 1;
      sign = a_sign & b_sign;  // -0 + -0 = -0
    end else if (a_is_zero) begin
      {sign, exponent, mantissa} = {b_sign, b_exponent, b_mantissa};
    end else if (b_is_zero) begin
      {sign, exponent, mantissa} = {a_sign, a_exponent, a_mantissa};
    end else begin
      // Determine larger exponent
      if (a_exponent > b_exponent || (a_exponent == b_exponent && a_man > b_man)) begin
        {exp_large, exp_small}   = {a_exponent, b_exponent};
        {man_large, man_small}   = {a_man, b_man};
        {sign_large, sign_small} = {a_sign, b_sign};
      end else begin
        {exp_large, exp_small}   = {b_exponent, a_exponent};
        {man_large, man_small}   = {b_man, a_man};
        {sign_large, sign_small} = {b_sign, a_sign};
      end

      exp_diff  = exp_large - exp_small;
      man_small = exp_diff < 24 ? (man_small >> exp_diff) : 0;

      // Perform addition/subtraction
      if (sign_large == sign_small) begin
        sum  = man_large + man_small;
        sign = sign_large;

        // Normalize
        if (sum[24]) begin
          sum = sum >> 1;
          exponent = exp_large + 1;
        end else begin
          exponent = exp_large;
        end
        mantissa = sum[23:1];
      end else begin
        sub_result = man_large - man_small;
        sign = man_large > man_small ? sign_large : sign_small;

        // Count leading zeros
        leading_zeros = 24;
        for (i = 23; i >= 0; i = i - 1) begin
          if (sub_result[i]) begin
            leading_zeros = 23 - i;
            break;
          end
        end

        // Normalize
        if (sub_result == 0) begin
          zero = 1;
        end else begin
          mantissa = sub_result << leading_zeros;
          exponent = exp_large - leading_zeros;

          if (exponent[7] || exponent < 8'h01) begin  // Underflow
            zero = 1;
          end else begin
            mantissa = mantissa[22:0];
          end
        end
      end
    end

    // Final output assembly
    if (nan) begin
      out = {1'b0, 8'hFF, 23'h1};
    end else if (infinity) begin
      out = {sign, 8'hFF, 23'h0};
    end else if (zero) begin
      out = {sign, 8'h0, 23'h0};
    end else if (exponent > 8'hFE) begin  // Overflow
      out = {sign, 8'hFF, 23'h0};
    end else begin
      out = {sign, exponent, mantissa};
    end
  end

endmodule
