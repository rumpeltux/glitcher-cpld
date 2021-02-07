// Creates a follow clock of 115200 Hz
module clk_div (input in_clk , output reg out_clk);
reg       [7:0] counter = 0;

always @ (posedge in_clk)
begin
 if (counter == 8'd216)  // 50e6/115200/2 - 1
 begin
   out_clk <= !out_clk;
	counter <= 0;
 end else begin
	counter <= counter + 1; // increment counter
 end
end
endmodule// end of module clk_div
