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

  `include "reg_data.vs" // en rst

endmodule
