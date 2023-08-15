/* -Register module
    Updates data on the posedge of the clk_i or the arst_i signal.
*/
`include "timescale.vs"

module MyReg #(
    parameter integer DATA_W  = 21,
    parameter integer RST_VAL = {DATA_W{1'b0}}
) (
    `include "clk_en_rst_i.vs"
    input  wire              en_i,
    input  wire              rst_i,
    input  wire [DATA_W-1:0] data_i,
    output reg  [DATA_W-1:0] data_o
);
  wire data_e;

  assign data_e = en_i & cke_i;

  always @(posedge clk_i, posedge arst_i) begin
    if (arst_i) begin
      data_o <= RST_VAL;
    end else if (rst_i) begin
      data_o <= RST_VAL;
    end else if (data_e) begin
      data_o <= data_i;
    end else begin
      data_o <= data_o;
    end
  end
endmodule
