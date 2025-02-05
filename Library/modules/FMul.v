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

  reg out_sign;
  reg [7:0] out_exponent;
  reg [22:0] out_mantissa;

  reg [47:0] product;
  reg [47:0] product_normalised;
  reg product_round;
  reg normalised;
  reg overflow;
  reg underflow;

  reg a_is_nan, a_is_den, a_is_inf, a_is_zero;
  reg b_is_nan, b_is_den, b_is_inf, b_is_zero;

  reg nan, infinity, zero;
  reg [8:0] stored_exponent;

  always_comb begin
    a_sign = a[31];
    b_sign = b[31];
    a_exponent = a[30:23];
    b_exponent = b[30:23];
    a_mantissa = a[22:0];
    b_mantissa = b[22:0];

    // Check for special cases
    a_is_nan = (a_exponent == 8'hFF) && (a_mantissa != 23'd0);
    b_is_nan = (b_exponent == 8'hFF) && (b_mantissa != 23'd0);
    a_is_den = (a_exponent == 8'h00) && (a_mantissa != 23'd0);
    b_is_den = (b_exponent == 8'h00) && (b_mantissa != 23'd0);
    a_is_inf = (a_exponent == 8'hFF) && (a_mantissa == 23'd0);
    b_is_inf = (b_exponent == 8'hFF) && (b_mantissa == 23'd0);
    a_is_zero = (a_exponent == 8'h00) && (a_mantissa == 23'd0);
    b_is_zero = (b_exponent == 8'h00) && (b_mantissa == 23'd0);

    // Handle NaN, Infinity, and Zero cases
    nan = a_is_nan | b_is_nan | (a_is_inf & b_is_zero) | (b_is_inf & a_is_zero);
    infinity = ~nan & (a_is_inf | b_is_inf);
    zero = ~nan & (a_is_zero | b_is_zero);

    out_sign = a_sign ^ b_sign;
    if (nan) begin
      out = {1'b0, 8'hFF, 23'h1};  // NaN
    end else if (infinity) begin
      out = {out_sign, 8'hFF, 23'd0};  // Infinity
    end else if (zero) begin
      out = {out_sign, 8'h00, 23'd0};  // Zero
    end else begin
      // Normal multiplication
      a_man   = {~a_is_den, a_mantissa};
      b_man   = {~b_is_den, b_mantissa};
      product = a_man * b_man;

      // Normalize product
      normalised = product[47];
      if (normalised) begin
        product_normalised = product;
      end else begin
        product_normalised = product << 1;
      end
      product_round = |product_normalised[22:0];
      out_mantissa = product_normalised[46:24] + (product_normalised[23] & product_round);

      // Calculate exponent
      stored_exponent = {1'b0, a_exponent} + {1'b0, b_exponent} - 9'd127 + {8'b0, normalised};
      out_exponent = stored_exponent[7:0];

      overflow = ((stored_exponent[8] & !stored_exponent[7]) & !zero);
      underflow = ((stored_exponent[8] & stored_exponent[7]) & !zero);
      // Final result assembly
      if (overflow) begin
        out = {out_sign, 8'hFF, 23'd0};  // Overflow to infinity
      end else if (underflow) begin
        out = {out_sign, 8'h00, 23'd0};  // Underflow to zero
      end else begin
        out = {out_sign, out_exponent, out_mantissa};
      end
    end
  end

endmodule
