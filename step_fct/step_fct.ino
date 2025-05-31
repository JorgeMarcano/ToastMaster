#define SPI_CS    8
#define SPI_MISO  12
#define SPI_CLK   13
#define OVEN_CTRL 2

#define SAMPLE_RATE_ms 250

//#define USE_LIB

#ifdef USE_LIB
#include <MAX6675.h>

MAX6675 tcouple(SPI_CS);
#endif

typedef unsigned long ulong;

ulong t0;
ulong curr_t;
ulong last_sample_t;
ulong last_switch_t;

int oven_state;

float get_temp() {
#ifdef USE_LIB
  return tcouple.readTempC();
#else
  
  digitalWrite(SPI_CLK, LOW);
  digitalWrite(SPI_CS, LOW);            // set the SS pin to LOW

  ulong data = 0;
  
  for(byte index = 0; index < 16; index++) {
    digitalWrite(SPI_CLK, HIGH);
    data = data << 1;
    data += (digitalRead(SPI_MISO) ? 1 : 0);
    digitalWrite(SPI_CLK, LOW);
  }

  digitalWrite(SPI_CS, HIGH);           // set the SS pin HIGH

  if (data & 0b100)
    return -1;

  if (data & 0x8000)
    return -2;

  return 0.25 * ((data >> 3) & 0x0FFF);
#endif
}

void setup() {
  pinMode(SPI_CS, OUTPUT); // set the SS pin as an output
  pinMode(OVEN_CTRL, OUTPUT);
  pinMode(SPI_CLK, OUTPUT);
  pinMode(SPI_MISO, INPUT);
  
  digitalWrite(SPI_CS, HIGH);
  digitalWrite(SPI_CLK, LOW);
  
  
  Serial.begin(115200);

  while(!Serial);
  Serial.println("Waiting...");
  while(Serial.read() != '\n');

  // TODO: GET a temp before turning on
  Serial.print(0);
  Serial.print(", ");
  Serial.println(get_temp());
  
  oven_state = 1;
  digitalWrite(OVEN_CTRL, HIGH);

  t0 = millis();
  last_t = t0;
}

#define STEP_DUTY_PERIOD_ms 500

void loop() {
  // put your main code here, to run repeatedly:
  curr_t = millis();
  if (curr_t - last_sample_t > SAMPLE_RATE_ms) {
    Serial.print((curr_t - t0)/1000.0);
    Serial.print(", ");
    Serial.println(get_temp());

    last_t += SAMPLE_RATE_ms;
  }

  if (curr_t - last_switch_t > STEP_DUTY_PERIOD_ms) {
    if (oven_state) digitalWrite(OVEN_CTRL, LOW);
    else digitalWrite(OVEN_CTRL, HIGH);
    oven_state = oven_state ? 0 : 1;

    last_switch_t += STEP_DUTY_PERIOD_ms;
  }
}
