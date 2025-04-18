/* Toaster Oven Controller
 * 
 * I/O:
 *    Fast and slow relay enable pins
 *    Analog amplifier pin
 *    Serial comms with Python host
 * 
 * Comms Protocol:
 *    Byte 0: Command ID
 *    Bytes 1-4: Optional command-specific info
 *    Last byte: '\n'
 * 
 */

/* Rev2 Protocol Changes
 * Gain, calibrated temp, and hysteresis all begin with default values.
 * removed 'a' (automatic) command, replaced with profile command
 * added 'h' (hysteresis) command, to set the board's hysteresis
 *    e.g. b'h[hystereis: 4B float]' -> sets the controller's hysteresis in degrees C
 * added 'p' (profile) command, divided into 3 subcommands
 *    Profile commands will be ignored if a profile is currently running.
 *    To interrupt a running profile, send an 'o' (off) command.
 *    'pa' (profile add)
 *      e.g. b'pa[time_ms: 4B int][temp_degc: 4B float]' -> add a temperature control point at the given time in ms
 *      IMPORTANT: points should be added in ascending order of time.
 *      A point at an earlier time should not be added after a point at a later time.
 *    'pc' (profile clear)
 *      e.g. b'pc' -> clears all points in the current profile.
 *    'pr' (profile run)
 *      begins controlling the toaster according to the previously set points.
 * changed 'r' (report) command to return temperature in milli-degrees C.
*/

// Define I/O Pins
#define THERM_IN A0
#define SLOW_RELAY_EN 3
#define FAST_RELAY_EN 20

// Define array sizes
#define IO_BUF_SIZE 100
#define MAX_PROFILE_POINTS 40

// Define required watchdog timer interval.
// After this time, the oven will automatically shut off.
#define WATCHDOG_TIMER_S 1

// Define reasonable defaults for user-set values
#define DEFAULT_GAIN -150.0
#define DEFAULT_TEMP_DEGC 20.0
#define DEFAULT_HYSTERESIS_DEGC 3.0

// Profile point struct, containing a time and temperature
typedef struct ProfilePoint {
  unsigned long time_after_start_ms;
  float target_temp_degc;
} ProfilePoint;

// Profile struct, containing an array of points, 
// the index of the current point, the max number of points,
// the profile's start time, and whether the profile is running
typedef struct Profile {
  ProfilePoint points[MAX_PROFILE_POINTS];
  int current_index;
  int max_index;
  unsigned long start_time_ms;
  bool running;
} Profile;


// Program variables
char io_buf[IO_BUF_SIZE];
unsigned long watchdog_last_update_time_ms;
unsigned long current_time_ms;
float current_temperature_degc;
float desired_temperature_degc;

Profile the_profile = {0};

// User-set variables
float calibrated_voltage_v;
float calibrated_temperature_degc;
float amplifier_gain;  // Degrees C / V
float hysteresis_degc;

void disable_profile() {
  the_profile.running = false;
  the_profile.current_index = -1;
}

void reset_profile() {
  the_profile.max_index = 0;
  the_profile.start_time_ms = -1;
  disable_profile();
}

void turn_oven_off() {
  digitalWrite(FAST_RELAY_EN, LOW);
  delay(500);
  digitalWrite(SLOW_RELAY_EN, LOW);
  disable_profile();
}

float adc_to_voltage(long adc_in) {
  return ((float) adc_in * 5.0) / 1023.0;
}

float read_adc() {
  return adc_to_voltage(analogRead(THERM_IN));
}

float voltage_to_temperature(float voltage_reading_v){
  float difference_v = voltage_reading_v - calibrated_voltage_v;
  return calibrated_temperature_degc + difference_v * amplifier_gain;
}

void setup() {
  // Set up serial & pins
  Serial.begin(38400);
  pinMode(SLOW_RELAY_EN, OUTPUT);
  pinMode(FAST_RELAY_EN, OUTPUT);

  // Initialize watchdog timer
  watchdog_last_update_time_ms = millis();

  // Initialize hysteresis
  hysteresis_degc = DEFAULT_HYSTERESIS_DEGC;

  // Initialize calibrated temperature to 20 by default
  calibrated_voltage_v = read_adc();
  calibrated_temperature_degc = DEFAULT_TEMP_DEGC;
  desired_temperature_degc = DEFAULT_TEMP_DEGC;

  // Start with oven off
  turn_oven_off();

  // Set up profile
  reset_profile();
}

void loop() {
  // Update adc reading & current time
  long adc_reading = analogRead(THERM_IN);
  float adc_voltage_v = adc_to_voltage(adc_reading);
  long adc_voltage_mv = (long)(1000.0*adc_voltage_v);
  current_temperature_degc = voltage_to_temperature(adc_voltage_v);
  long current_temperature_mdegc = (long)(1000.0*current_temperature_degc);
  current_time_ms = millis();
  long desired_temperature_mdegc;
  byte relay;
  byte state;
  char* temp_io;

  // Check for comms
  if (Serial.available()) {
    Serial.readBytesUntil('\n', io_buf, IO_BUF_SIZE);
    // Process input
    bool io_buf_repopulated = false;
    {
      switch (io_buf[0]) {
        case 'k':  // Keep-alive signal, do nothing
          break;
        case 'o':  // Off signal, turn oven off
          turn_oven_off();
          break;
        case 'g':  // Set amplifier gain
          amplifier_gain = *(float*)&io_buf[1];
          break;
        case 'h':  // Set hysteresis
          hysteresis_degc = *(float*)&io_buf[1];
          break;
        case 'c':  // Calibrate temperature, expect ~20°C
          calibrated_voltage_v = adc_voltage_v;
          temp_io = io_buf+1;
          calibrated_temperature_degc = *(float*)temp_io;
          break;
        case 'r':  // Report reading, temperature, & profile status to host
          desired_temperature_mdegc = (long) desired_temperature_degc * 1000;
          sprintf(io_buf, "%ld,%ld,%ld,%d,%ld\n", adc_reading, adc_voltage_mv, current_temperature_mdegc, the_profile.current_index, desired_temperature_mdegc);
          io_buf_repopulated = true;
          break;
        case 'm':  // Manual relay control
          disable_profile();  // End running profile if there is one
          relay = *(byte*)&io_buf[1];
          state = *(byte*)&io_buf[2];
          if (relay == 1) digitalWrite(SLOW_RELAY_EN, state == 1 ? LOW : HIGH);
          else digitalWrite(FAST_RELAY_EN, state == 1 ? LOW : HIGH);
          break;
        case 'p':  // Profile control, read second character
          if (the_profile.running) break;  // Disallow modifying the profile while it is running
          switch (io_buf[1]) {
            case 'a':  // Add a point to the profile
              if (the_profile.max_index == MAX_PROFILE_POINTS) break;  // Don't add points beyond max
              temp_io = io_buf+2;
//              the_profile.points[the_profile.max_index].time_after_start_ms = ((ProfilePoint*)temp_io)->time_after_start_ms;
              the_profile.points[the_profile.max_index++] = *(ProfilePoint*)temp_io;
              Serial.println(the_profile.points[the_profile.max_index-1].time_after_start_ms);
              break;
            case 'c':  // Clear the profile
              reset_profile();
              break;
            case 'r':  // Run the profile
              digitalWrite(SLOW_RELAY_EN, HIGH);
              the_profile.current_index = 0;
              the_profile.start_time_ms = current_time_ms;
              the_profile.running = true;
              Serial.println("STARTING");
              break;
          }
          break;
      }
    }

    // Comms received, reset watchdog
    watchdog_last_update_time_ms = current_time_ms;

    // Send ack back to host
    if (!io_buf_repopulated) {
      sprintf(io_buf, "ok\n");
    }
    Serial.print(io_buf);
    Serial.flush();
  }

  // Check watchdog
  if (current_time_ms - watchdog_last_update_time_ms >= 1000 * WATCHDOG_TIMER_S) {
    // Watchdog expired, open relays to turn off toaster
    turn_oven_off();
  } else if (the_profile.running) {
    unsigned long time_since_start_ms = current_time_ms - the_profile.start_time_ms;

    if (time_since_start_ms >= the_profile.points[the_profile.current_index].time_after_start_ms) {
      the_profile.current_index += 1;
    }

    if (the_profile.current_index >= the_profile.max_index) {
      // End of the profile, cool down as fast as possible and stop the profile from running.
      desired_temperature_degc = 20;
      digitalWrite(FAST_RELAY_EN, LOW);
      disable_profile();
    } else {
      // Continue controlling the profile
      float prev_temp_degc;
      unsigned long prev_time_ms;

      if (the_profile.current_index == 0) {
        prev_temp_degc = 20.0;
        prev_time_ms = 0;
      } else {
        ProfilePoint prev_point = the_profile.points[the_profile.current_index-1];
        prev_temp_degc = prev_point.target_temp_degc;
        prev_time_ms = prev_point.time_after_start_ms;
      }

      ProfilePoint target_point = the_profile.points[the_profile.current_index];
      unsigned long next_time_ms = target_point.time_after_start_ms;
      float next_temp_degc = target_point.target_temp_degc;
      float t = (float)(time_since_start_ms - prev_time_ms) / (float)(next_time_ms - prev_time_ms);
      desired_temperature_degc = next_temp_degc * t + prev_temp_degc * (1 - t);  // Lerp temperature

      if (current_temperature_degc > desired_temperature_degc + hysteresis_degc) {
        digitalWrite(FAST_RELAY_EN, LOW);
      } else if (current_temperature_degc < desired_temperature_degc - hysteresis_degc) {
        digitalWrite(FAST_RELAY_EN, HIGH);
      }
    }
  }

  delay(1);
}
