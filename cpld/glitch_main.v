module data_model (
	input rx,
	input clk,
	input trigger,
	input [7:0]rx_byte,
	output glitch,
	output delayed_trigger,
	// for debugging
	output reg [2:0] idx,
	output triggered,
	output reg [20:0] counter,
   output reg trigger_state
);

localparam 
	   DELAY_SIZE = 3,
	   DURATION_SIZE = 1,
	   TRIGGER_SIZE = 2;

reg [DELAY_SIZE * 7 - 1:0] config_delay;
reg [DURATION_SIZE * 7 - 1:0] config_duration;
reg [TRIGGER_SIZE * 7 - 1:0] config_trigger_count;

reg config_power = 1'b0;  // the default power state, in STATE_GLITCH outputs the opposite
reg config_enabled;
reg config_trigger_reenable;  // automatically reenable the trigger after finishing a glitch
reg config_override_trigger;  // don't wait for the trigger to hit, instead go to STATE_DELAY immediately
reg config_triggered_stay_active;

localparam
	STATE_RESET=2'd0,
	STATE_WAIT_TRIGGER=2'd1,
	STATE_DELAY=2'd2,
	STATE_GLITCH=2'd3;

reg [1:0]state;
reg [1:0]state_next;
reg triggered_once;
wire enabled;
	
always @(*) begin
  state_next = state;
  case(state)
	STATE_RESET:
		if (config_override_trigger)
			state_next = STATE_DELAY;
		else if (enabled)
			state_next = STATE_WAIT_TRIGGER;
	STATE_WAIT_TRIGGER: 
	   if (counter[TRIGGER_SIZE * 7 - 1:0] == config_trigger_count)
		  state_next = STATE_DELAY;
   STATE_DELAY:
	   if (counter[DELAY_SIZE * 7 - 1:0] == config_delay)
			state_next = STATE_GLITCH;
	STATE_GLITCH:
	   if (counter[DURATION_SIZE * 7 - 1:0] == config_duration)
			state_next = STATE_RESET;
	default: state_next = STATE_RESET;
  endcase
end

always @ (posedge rx) begin
  if (rx_byte[7]) begin
    idx <= 0;
  end else begin
  		 case (idx)
		    // If you change DELAY_SIZE | DURATION_SIZE | TRIGGER_SIZE => update this!
			 3'd0: config_delay[6:0] <= rx_byte[6:0];
			 3'd1: config_delay[13:7] <= rx_byte[6:0];
			 3'd2: config_delay[20:14] <= rx_byte[6:0];
			 3'd3: config_duration[6:0] <= rx_byte[6:0];
			 3'd4: config_trigger_count[6:0] <= rx_byte[6:0];
			 3'd5: config_trigger_count[13:7] <= rx_byte[6:0];
		 endcase
    idx <= idx + 1;
  end
end

reg sync_trigger,safe_trigger;

always @(posedge clk)
begin
    sync_trigger <= trigger;
    safe_trigger <= sync_trigger;
end

assign glitch = state == STATE_GLITCH ? !config_power : config_power;
assign triggered = state_next >= STATE_DELAY;
assign delayed_trigger = triggered_once || (config_triggered_stay_active && triggered_once);
assign enabled = (triggered_once && config_trigger_reenable) || (!triggered_once && config_enabled);

always @ (posedge clk)
begin

  if (safe_trigger != trigger_state) begin
    trigger_state <= !trigger_state;
	 if (state_next == STATE_WAIT_TRIGGER)
		counter <= counter + 1;
  end

  if (state != state_next || state_next == STATE_RESET)
	 counter <= 0;
  else if (state == STATE_DELAY || state == STATE_GLITCH) begin
    counter <= counter + 1;
  end
  
  if (triggered)
    triggered_once <= 1;

  state <= state_next;

  if (rx && rx_byte[7]) begin
	 state <= STATE_RESET;

    config_power <= rx_byte[0];
    config_enabled <= rx_byte[1];
    config_trigger_reenable <= rx_byte[2];
    config_override_trigger <= rx_byte[3];
	 config_triggered_stay_active <= rx_byte[4];

	 triggered_once <= 0;
  end
end

endmodule
