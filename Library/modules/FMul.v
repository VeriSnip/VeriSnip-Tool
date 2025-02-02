/* -Floating-point multiplication module, respecting IEEE 754 standard.
    The module receives two 32-bit floating-point numbers and returns the result of their multiplication.
    The module handles special cases such as NaN, Infinity, and Zero.
*/
`include "timescale.vs"

module FMul (
    input [31:0] a,
    input [31:0] b,
    output reg [31:0] out
);

  reg a_sign, b_sign;
  reg [7:0] a_exponent, b_exponent;
  reg [22:0] a_mantissa, b_mantissa;
  reg [23:0] a_man, b_man;

  reg sign;
  reg [7:0] out_exponent;
  reg [22:0] mantissa;

  reg [47:0] product;
  reg [47:0] product_shifted;
  reg shift;

  reg a_is_nan, a_is_inf, a_is_zero;
  reg b_is_nan, b_is_inf, b_is_zero;

  reg nan, infinity, zero;
  reg [8:0] stored_exponent;

  always @(*) begin
    a_sign = a[31];
    b_sign = b[31];
    a_exponent = a[30:23];
    b_exponent = b[30:23];
    a_mantissa = a[22:0];
    b_mantissa = b[22:0];

    // Check for special cases
    a_is_nan = (a_exponent == 8'hFF) && (a_mantissa != 23'd0);
    b_is_nan = (b_exponent == 8'hFF) && (b_mantissa != 23'd0);
    a_is_inf = (a_exponent == 8'hFF) && (a_mantissa == 23'd0);
    b_is_inf = (b_exponent == 8'hFF) && (b_mantissa == 23'd0);
    a_is_zero = (a_exponent == 8'h00) && (a_mantissa == 23'd0);
    b_is_zero = (b_exponent == 8'h00) && (b_mantissa == 23'd0);

    nan = 1'b0;
    infinity = 1'b0;
    zero = 1'b0;

    // Handle NaN, Infinity, and Zero cases
    if (a_is_nan || b_is_nan) begin
      nan = 1'b1;
    end else if ((a_is_inf && b_is_zero) || (b_is_inf && a_is_zero)) begin
      nan = 1'b1;
    end else if (a_is_inf || b_is_inf) begin
      infinity = 1'b1;
    end else if (a_is_zero || b_is_zero) begin
      zero = 1'b0;
      // Check if both are zero to handle sign (negative zero)
      if (a_is_zero && b_is_zero) begin
        zero = 1'b1;
      end
    end

    if (nan) begin
      out = {1'b0, 8'hFF, 23'h1};  // NaN
    end else if (infinity) begin
      out = {a_sign ^ b_sign, 8'hFF, 23'd0};  // Infinity
    end else if (zero) begin
      out = {a_sign ^ b_sign, 8'h00, 23'd0};  // Zero
    end else begin
      // Normal multiplication
      a_man   = {1'b1, a_mantissa};
      b_man   = {1'b1, b_mantissa};
      product = a_man * b_man;

      // Normalize product
      if (product[47]) begin
        product_shifted = product >> 1;
        shift = 1'b1;
      end else begin
        product_shifted = product;
        shift = 1'b0;
      end

      // Calculate exponent
      stored_exponent = {1'b0, a_exponent} + {1'b0, b_exponent} - 9'd127 + {8'b0, shift};

      // Handle exponent overflow/underflow
      if (stored_exponent[8] || stored_exponent < 9'd0) begin
        out_exponent = 8'h00;  // Underflow
      end else if (stored_exponent > 9'd255) begin
        out_exponent = 8'hFF;  // Overflow
      end else begin
        out_exponent = stored_exponent[7:0];
      end

      // Extract mantissa
      if (shift) begin
        mantissa = product_shifted[46:24];
      end else begin
        mantissa = product_shifted[45:23];
      end

      // Final result assembly
      if (out_exponent == 8'hFF) begin
        out = {a_sign ^ b_sign, 8'hFF, 23'd0};  // Overflow to infinity
      end else if (out_exponent == 8'h00) begin
        out = {a_sign ^ b_sign, 8'h00, 23'd0};  // Underflow to zero
      end else begin
        out = {a_sign ^ b_sign, out_exponent, mantissa};
      end
    end
  end

endmodule
