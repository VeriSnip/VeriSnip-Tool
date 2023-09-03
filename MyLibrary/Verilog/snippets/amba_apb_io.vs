    // AMBA APB interface IOs
    input  wire                PCLK,
    input  wire                PRESETn,
    input  wire [  ADDR_W-1:0] PADDR,
    input  wire                PSELx,
    input  wire                PENABLE,
    input  wire                PWRITE,
    input  wire [  DATA_W-1:0] PWDATA,
    input  wire [DATA_W/8-1:0] PSTRB,
    output wire                PREADY,
    output wire [  DATA_W-1:0] PRDATA,
    output wire                PSLVERR,
`ifdef Wakeup_Signal
    input  wire                PWAKEUP,
`endif