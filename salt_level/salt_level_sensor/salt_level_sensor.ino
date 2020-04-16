#include <ArduinoBearSSL.h>
#include <ArduinoECCX08.h>
#include <ArduinoMqttClient.h>
#include <ArduinoJson.h>
#include <WiFiNINA.h>

#include "arduino_secrets.h"

const char ssid[]        = SECRET_SSID;
const char pass[]        = SECRET_PASS;
const char broker[]      = SECRET_BROKER;
const char* certificate  = SECRET_CERTIFICATE;

WiFiClient    wifiClient;            // Used for the TCP socket connection
BearSSLClient sslClient(wifiClient); // Used for SSL/TLS connection, integrates with ECC508
MqttClient    mqttClient(sslClient);

unsigned long lastMillis = 0;
const char waterSoftenerId[] = "softener_one";

void setup() {
  Serial.begin(115200);
  while (!Serial);

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
}

void loop() {
  if (millis() - lastMillis > 5000) {
    lastMillis = millis();
    
    if (WiFi.status() != WL_CONNECTED) {
      connectWiFi();
    }
  
    if (!mqttClient.connected()) {
      connectMQTT();
    }

    gatherSensorDataAndPublish();
  }
}

unsigned long getTime() {
  // get the current time from the WiFi module  
  return WiFi.getTime();
}

int getSensorData(int sensorId) {
  // get the current sensor value
  return sensorId;
}

void connectWiFi() {
  Serial.print("Attempting to connect to SSID: ");
  Serial.print(ssid);
  Serial.print(" ");

  while (WiFi.begin(ssid, pass) != WL_CONNECTED) {
    Serial.print(".");
    delay(5000);
  }
  Serial.println();

  Serial.println("You're connected to the network");
  Serial.println();
}

void connectMQTT() {
  Serial.print("Attempting to MQTT broker: ");
  Serial.print(broker);
  Serial.println(" ");

  while (!mqttClient.connect(broker, 8883)) {
    // failed, retry
    Serial.print(".");
    delay(5000);
  }
  Serial.println();

  Serial.println("You're connected to the MQTT broker");
  Serial.println();
}

void gatherSensorDataAndPublish() {
  Serial.println("Publishing message");

  // Build JSON message to publish
  const size_t capacity = JSON_OBJECT_SIZE(5);
  DynamicJsonDocument doc(capacity);
  doc["timestamp"] = getTime();
  doc["water_softener_id"] = waterSoftenerId;
  doc["sensor_1"] = getSensorData(1);
  doc["sensor_2"] = getSensorData(2);
  doc["sensor_3"] = getSensorData(3);
  
  mqttClient.beginMessage("sensor/salt_level");
  serializeJson(doc, mqttClient);
  mqttClient.print(millis());
  mqttClient.endMessage();
}
