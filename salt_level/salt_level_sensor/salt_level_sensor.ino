#include <ArduinoBearSSL.h>
#include <ArduinoECCX08.h>
#include <ArduinoMqttClient.h>
#include <ArduinoJson.h>
#include <WiFiNINA.h>
#include <NewPing.h>

#include "arduino_secrets.h"

const char ssid[]        = SECRET_SSID;
const char pass[]        = SECRET_PASS;
const char broker[]      = SECRET_BROKER;
const char* certificate  = SECRET_CERTIFICATE;

WiFiClient    wifiClient;            // Used for the TCP socket connection
BearSSLClient sslClient(wifiClient); // Used for SSL/TLS connection, integrates with ECC508
MqttClient    mqttClient(sslClient);

const long RUNNING_BLINK_INTERVAL = 10000;
const long RUNNING_BLINK_DURATION = 100;
const long WIFI_CONNECTING_INTERVAL = 1000;
const long MQTT_CONNECTING_INTERVAL = 1000;
const long WIFI_PRINT_INTERVAL = 5000;
const long MQTT_PRINT_INTERVAL = 5000;

#define RUNNING_PIN 5
#define WIFI_PIN 4
#define MQTT_PIN 6

#define SENSOR_ONE_ECHO_PIN 0
#define SENSOR_ONE_TRIGGER_PIN 1

#define SENSOR_TWO_TRIGGER_PIN 2
#define SENSOR_TWO_ECHO_PIN 3

#define SENSOR_THREE_TRIGGER_PIN 8
#define SENSOR_THREE_ECHO_PIN 7

#define SENSOR_FOUR_TRIGGER_PIN 10
#define SENSOR_FOUR_ECHO_PIN 9

int builtInLEDState = LOW;
int wifiLEDState = LOW;
int mqttLEDState = LOW;

unsigned long lastRunningBlinkMillis = 0;
unsigned long lastRunningBlunkDurationMillis = 0;
unsigned long lastSensorMillis = 0;
const char waterSoftenerId[] = "softener_one";

const int SENSING_INTERVAL = 1000 * 60 * 60 * 24; // one day

#define SENSOR_COUNT 4
#define MAX_DISTANCE 100
#define SENSOR_SAMPLE_COUNT 8

NewPing sonar[SENSOR_COUNT] = {
  NewPing(SENSOR_ONE_TRIGGER_PIN, SENSOR_ONE_ECHO_PIN, MAX_DISTANCE),
  NewPing(SENSOR_TWO_TRIGGER_PIN, SENSOR_TWO_ECHO_PIN, MAX_DISTANCE),
  NewPing(SENSOR_THREE_TRIGGER_PIN, SENSOR_THREE_ECHO_PIN, MAX_DISTANCE),
  NewPing(SENSOR_FOUR_TRIGGER_PIN, SENSOR_FOUR_ECHO_PIN, MAX_DISTANCE)
};

void setup() {
  Serial.begin(9600);

  initializePins();

  if (!ECCX08.begin()) {
    Serial.println("No ECCX08 present!");
    while (1);
  }

  // Set a callback to get the current time
  // used to validate the servers certificate
  ArduinoBearSSL.onGetTime(getTime);

  // Set the ECCX08 slot to use for the private key
  // and the accompanying public certificate for it
  sslClient.setEccSlot(0, certificate);
  digitalWrite(RUNNING_PIN, HIGH);
  connectWiFi();
  connectMQTT();
}

void loop() {
  unsigned long currentMillis = millis();

  if (builtInLEDState == HIGH) {
    if (currentMillis - lastRunningBlunkDurationMillis > RUNNING_BLINK_DURATION) {
      builtInLEDState = LOW;
      digitalWrite(RUNNING_PIN, builtInLEDState);
    }
  } else if (currentMillis - lastRunningBlinkMillis > RUNNING_BLINK_INTERVAL) {
    lastRunningBlinkMillis = currentMillis;
    lastRunningBlunkDurationMillis = currentMillis;
    builtInLEDState = HIGH;
    digitalWrite(RUNNING_PIN, builtInLEDState);
  }
  if (currentMillis - lastSensorMillis > SENSING_INTERVAL) {
    lastSensorMillis = currentMillis;

    if (WiFi.status() != WL_CONNECTED) {
      connectWiFi();
    }

    if (!mqttClient.connected()) {
      connectMQTT();
    }

    gatherSensorDataAndPublish();
  }
}

void initializePins() {
  int numOutputPins = 4;
  int outputPins[numOutputPins] = {RUNNING_PIN, WIFI_PIN, MQTT_PIN};
  for (int i = 0; i < numOutputPins; i += 1) {
    pinMode(outputPins[i], OUTPUT);
  }

  int state = HIGH;
  for (int i = 0; i < 5; i += 1) {
    for (int j = 0; j < numOutputPins; j += 1) {
      digitalWrite(outputPins[j], state);
    }
    state = state == HIGH ? LOW : HIGH;
    delay(250);
  }
  int current = RUNNING_PIN;
  for (int i = 0; i < numOutputPins * 5; i += 1) {
    for (int j = 0; j < numOutputPins; j += 1) {
      int pinState = j == i % numOutputPins;
      digitalWrite(outputPins[j], pinState);
    }
    delay(250);
  }

  for (int i = 0; i < numOutputPins; i += 1) {
    digitalWrite(outputPins[i], LOW);
  }
}

unsigned long getTime() {
  // get the current time from the WiFi module
  return WiFi.getTime();
}

int getSensorData(int sensorId) {
  int sum = 0;
  Serial.print("Sensor ");
  Serial.print(sensorId);
  Serial.print(": [");
  for (int i = 0; i < SENSOR_SAMPLE_COUNT; i += 1) {
    int distance = sonar[sensorId].ping_cm();
    delay(1000);
    Serial.print(distance);
    Serial.print(", ");
    sum += distance;
  }
  Serial.println("]");
  Serial.print(sum / SENSOR_SAMPLE_COUNT);
  Serial.println("cm (average)");

  int average = (int)(sum / SENSOR_SAMPLE_COUNT);

  return average;
}

void connectWiFi() {
  digitalWrite(WIFI_PIN, HIGH);
  Serial.print("Attempting to connect to SSID: ");
  Serial.print(ssid);
  Serial.print(" ");

  unsigned long currentWifiMillis = millis();
  unsigned long lastWifiMillis = currentWifiMillis;
  while (WiFi.begin(ssid, pass) != WL_CONNECTED) {
    if (currentWifiMillis - lastWifiMillis > WIFI_CONNECTING_INTERVAL) {
      wifiLEDState = wifiLEDState == LOW ? HIGH : LOW;
      digitalWrite(WIFI_PIN, wifiLEDState);
    }
    if (currentWifiMillis - lastWifiMillis > WIFI_PRINT_INTERVAL) {
      Serial.print(".");
    }
  }
  Serial.println();

  Serial.println("You're connected to the network");
  Serial.println();
  digitalWrite(WIFI_PIN, LOW);
}

void connectMQTT() {
  digitalWrite(MQTT_PIN, HIGH);
  Serial.print("Attempting to MQTT broker: ");
  Serial.print(broker);
  Serial.println(" ");

  unsigned long currentMqttMillis = millis();
  unsigned long lastMqttMillis = currentMqttMillis;
  while (!mqttClient.connect(broker, 8883)) {
    // failed, retry
    if (currentMqttMillis - lastMqttMillis > MQTT_CONNECTING_INTERVAL) {
      mqttLEDState = mqttLEDState == LOW ? HIGH : LOW;
      digitalWrite(MQTT_PIN, mqttLEDState);
    }
    if (currentMqttMillis - lastMqttMillis > MQTT_PRINT_INTERVAL) {
      Serial.print(".");
    }
  }
  digitalWrite(MQTT_PIN, LOW);
  Serial.println();

  Serial.println("You're connected to the MQTT broker");
  Serial.println();
}

void gatherSensorDataAndPublish() {
  digitalWrite(RUNNING_PIN, HIGH);
  Serial.println("Publishing message");

  // Build JSON message to publish
  const size_t capacity = JSON_OBJECT_SIZE(10);
  DynamicJsonDocument doc(capacity);
  doc["timestamp"] = getTime();
  doc["water_softener_id"] = waterSoftenerId;
  for (int i = 0; i < SENSOR_COUNT; i += 1) {
    Serial.print("sensor--");
    Serial.println("sensor_" + String(i));
    doc["sensor_" + String(i)] = getSensorData(i);
  }
  
  mqttClient.beginMessage("sensor/salt_level");
  serializeJson(doc, mqttClient);
  mqttClient.print(millis());
  mqttClient.endMessage();
  digitalWrite(RUNNING_PIN, LOW);
}
