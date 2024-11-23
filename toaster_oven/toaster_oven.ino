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




#define THERM_IN A0
#define SLOW_RELAY_EN 3
#define FAST_RELAY_EN 20

#define READ_BUF_SIZE 100
#define WATCHDOG_TIMER_S 1
#define HSYTERESIS 2

typedef float Voltage;
typedef float Temperature;

bool increasing;
bool automatic;

// Program variables
char buf[READ_BUF_SIZE];
int transmission_size;
int watchdog_last_update_time;
int current_time;
Temperature current_temperature;

// User-set variables
Voltage calibrated_voltage;
Temperature calibrated_temperature;
float amplifier_gain;
Temperature desired_temperature;


void turn_oven_off() {
  digitalWrite(FAST_RELAY_EN, LOW);
  delay(500);
  digitalWrite(SLOW_RELAY_EN, LOW);
}

Voltage adc_to_voltage(int in) {
  return ((float) in * 5.0) / 1023.0;
}

Voltage read_adc() {
  return adc_to_voltage(analogRead(THERM_IN));
}

Temperature reading_to_temperature(Voltage reading){
  Voltage difference = reading - calibrated_voltage;
  return calibrated_temperature + difference * amplifier_gain;
}

void setup() {
  // Set up serial & pins
  Serial.begin(38400);
  pinMode(SLOW_RELAY_EN, OUTPUT);
  pinMode(FAST_RELAY_EN, OUTPUT);

  // Initialize watchdog timer
  watchdog_last_update_time = millis();

  // Initialize desired temperature
  desired_temperature = 0;

  // Initialize calibrated temperature to 20 by default
  calibrated_temperature = 20.0;

  // Start with oven off
  turn_oven_off();

  // Set up bools
  increasing = true;
  automatic = true;
}

void loop() {
  int adc;
  float voltage_f;
  int voltage;
  unsigned int temp;
  byte relay_idx;
  int state;
  int relay;
  
  if (Serial.available()) {
    transmission_size = Serial.readBytesUntil('\n', buf, READ_BUF_SIZE); // FIXME: Blocking!!
    // Process input
    {
      switch (buf[0]) {
        case 'k':  // Keep-alive signal, do nothing
          break;
        case 'o':  // Off signal, turn oven off
          turn_oven_off();
          break;
        case 't':  // Temperature signal, update desired temperature
          desired_temperature = *(float*)&buf[1];
          break;
        case 'g':  // Set amplifier gain
          amplifier_gain = *(float*)&buf[1];
          break;
        case 'c':  // Calibrate temperature, expect ~20°C
          calibrated_voltage = read_adc();
          calibrated_temperature = *(Temperature*)&buf[1];
          break;
        case 'r':  // Report temperature to host
          adc = analogRead(THERM_IN);
//          float voltage = adc_to_voltage(adc);
//          float temp = reading_to_temperature(voltage);
          voltage_f = (adc_to_voltage(adc));
          voltage = (int)(1000.0*voltage_f);
          temp = (unsigned int)(100.0*reading_to_temperature(voltage_f));

          sprintf(buf, "%d,%d,%u\n", adc, voltage, temp);
//          Serial.write((byte*) &adc, sizeof(int));
//          Serial.write((byte*) &voltage, sizeof(float));
//          Serial.write((byte*) &temp, sizeof(float));
//          Serial.print("\n");
          Serial.print(buf);
          Serial.flush();
          break;
        case 'm':  // Manual relay control
          automatic = false;
          relay_idx = *(byte*)&buf[1];
          state = (*(byte*)&buf[2] == 1) ? LOW : HIGH;
          relay = (relay_idx == 1) ? SLOW_RELAY_EN : FAST_RELAY_EN;
          
          digitalWrite(relay, state);
          digitalWrite(relay, state);
          break;
        case 'a':
          automatic = true;
          break;
      }
    }

    // Reset watchdog
    watchdog_last_update_time = millis();
  }

  // Check watchdog
  current_time = millis();
  current_temperature = reading_to_temperature(read_adc());
//  if (current_time - watchdog_last_update_time >= 1000 * WATCHDOG_TIMER_S) {
//    // Watchdog expired, open relays to turn off toaster
//    turn_oven_off();
//  } else {
  {
    if (automatic) { 
      // Watchdog not expired, adjust temperature if necessary. Simple P control.
      if (current_temperature < desired_temperature) {
        digitalWrite(FAST_RELAY_EN, HIGH);
      } else {
        digitalWrite(FAST_RELAY_EN, LOW);
      }
    }
  }

  delay(1);
}
