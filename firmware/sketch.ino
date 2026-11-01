#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <ArduinoJson.h>
#include <esp_timer.h>
#include <time.h>

#if __has_include("coldchain_config.h")
#include "coldchain_config.h"
#else
#include "coldchain_config.example.h"
#endif

constexpr uint8_t SENSOR_PIN = 18, BUZZER_PIN = 19, LED_PIN = 23;
constexpr uint32_t SAMPLE_MS = 5000, ALERT_MS = 30000, MAX_GAP_MS = 10000;
constexpr float MIN_C = 2.0, MAX_C = 8.0;
constexpr size_t CAPACITY = 120;
OneWire oneWire(SENSOR_PIN);
DallasTemperature sensors(&oneWire);

struct Reading {
  uint32_t sequence;
  uint64_t uptime;
  time_t timestamp;
  float temperature, latitude, longitude;
  bool valid, alarm;
  uint32_t dropped;
};
Reading buffer[CAPACITY];
size_t queueHead = 0, queueCount = 0;
uint32_t lostCount = 0;
SemaphoreHandle_t queueMutex;
char bootId[25];
volatile bool networkPaused = false;
const float route[][2] = {
  {36.8065,10.1815},{36.8105,10.1865},{36.8145,10.1920},
  {36.8190,10.1990},{36.8235,10.2070},{36.8285,10.2160},
  {36.8340,10.2260},{36.8395,10.2370},{36.8460,10.2490},
  {36.8535,10.2620},{36.8620,10.2750},{36.8710,10.2890},
  {36.8780,10.3030},
};
constexpr size_t ROUTE_SIZE = sizeof(route) / sizeof(route[0]);

void enqueue(const Reading &value) {
  xSemaphoreTake(queueMutex, portMAX_DELAY);
  if (queueCount == CAPACITY) {
    queueHead = (queueHead + 1) % CAPACITY;
    queueCount--;
    lostCount++;
    Serial.printf("BUFFER_FULL lost=%lu\n", (unsigned long)lostCount);
  }
  buffer[(queueHead + queueCount) % CAPACITY] = value;
  buffer[(queueHead + queueCount) % CAPACITY].dropped = lostCount;
  queueCount++;
  xSemaphoreGive(queueMutex);
}

bool peekReading(Reading &value) {
  xSemaphoreTake(queueMutex, portMAX_DELAY);
  bool found = queueCount > 0;
  if (found) value = buffer[queueHead];
  xSemaphoreGive(queueMutex);
  return found;
}

void acknowledge(uint32_t sequence) {
  xSemaphoreTake(queueMutex, portMAX_DELAY);
  // An overflow may have displaced the item while an HTTP request was in flight.
  if (queueCount && buffer[queueHead].sequence == sequence) {
    queueHead = (queueHead + 1) % CAPACITY;
    queueCount--;
  }
  xSemaphoreGive(queueMutex);
}

void networkTask(void *) {
  Serial.printf("NETWORK_TASK priority=%u core=%d\n",
                (unsigned int)uxTaskPriorityGet(nullptr), xPortGetCoreID());
  WiFi.mode(WIFI_STA);
  WiFi.begin("Wokwi-GUEST", "", 6);
  configTime(0, 0, "pool.ntp.org", "time.google.com");
  uint32_t lastReconnect = millis();
  uint32_t retryMs = 1000;
  for (;;) {
    if (networkPaused || strlen(API_BASE_URL) == 0) {
      vTaskDelay(pdMS_TO_TICKS(250));
      continue;
    }
    if (WiFi.status() != WL_CONNECTED) {
      if ((uint32_t)(millis() - lastReconnect) >= 10000) {
        WiFi.reconnect();
        lastReconnect = millis();
      }
      vTaskDelay(pdMS_TO_TICKS(250));
      continue;
    }
    Reading reading;
    if (!peekReading(reading)) {
      vTaskDelay(pdMS_TO_TICKS(100));
      continue;
    }
    StaticJsonDocument<1024> doc;
    doc["schema_version"] = 1;
    doc["config_version"] = 1;
    doc["vehicle_id"] = "VEH-001";
    doc["transport_id"] = TRANSPORT_ID;
    doc["boot_id"] = bootId;
    doc["sequence"] = reading.sequence;
    doc["uptime_ms"] = reading.uptime;
    if (reading.timestamp > 1700000000) {
      char stamp[25];
      struct tm utc;
      gmtime_r(&reading.timestamp, &utc);
      strftime(stamp, sizeof(stamp), "%Y-%m-%dT%H:%M:%SZ", &utc);
      doc["measured_at"] = stamp;
    } else doc["measured_at"] = nullptr;
    if (reading.valid) doc["temperature_c"] = reading.temperature;
    else doc["temperature_c"] = nullptr;
    doc["latitude"] = reading.latitude;
    doc["longitude"] = reading.longitude;
    doc["sensor_status"] = reading.valid ? "ok" : "error";
    doc["local_alarm"] = reading.alarm;
    doc["source"] = "wokwi";
    doc["dropped_count"] = reading.dropped;
    String payload;
    serializeJson(doc, payload);
    WiFiClientSecure tls;
    WiFiClient plain;
    HTTPClient http;
    String url = String(API_BASE_URL) + "/api/v1/telemetry";
    bool secure = url.startsWith("https://");
    if (secure && (strlen(ROOT_CA) == 0 || time(nullptr) < 1700000000)) {
      Serial.println("TLS_WAIT: certificate and synchronized UTC clock required");
      vTaskDelay(pdMS_TO_TICKS(2000));
      continue;
    }
    bool started;
    if (secure) {
      tls.setCACert(ROOT_CA);
      tls.setHandshakeTimeout(30);
      started = http.begin(tls, url);
    } else {
      started = http.begin(plain, url); // Local/private gateway only.
    }
    if (!started) {
      vTaskDelay(pdMS_TO_TICKS(2000));
      continue;
    }
    http.setConnectTimeout(3000);
    http.setTimeout(3000);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-Device-Key", DEVICE_API_KEY);
    Serial.printf("HTTP_START seq=%lu mode=%s\n",
                  (unsigned long)reading.sequence, secure ? "HTTPS" : "HTTP");
    int code = http.POST(payload);
    if (secure && code < 0) {
      char detail[160] = {};
      int tlsCode = tls.lastError(detail, sizeof(detail));
      Serial.printf("TLS_ERROR code=%d detail=%s\n", tlsCode, detail);
    }
    http.end();
    Serial.printf("HTTP seq=%lu status=%d\n", (unsigned long)reading.sequence, code);
    if (code == 200 || code == 201) {
      acknowledge(reading.sequence);
      retryMs = 1000;
      vTaskDelay(pdMS_TO_TICKS(80));
    } else if (code == 422 || code == 409) {
      Serial.println("MEASUREMENT_REJECTED: check serial log and API contract");
      acknowledge(reading.sequence);
      vTaskDelay(pdMS_TO_TICKS(500));
    } else {
      vTaskDelay(pdMS_TO_TICKS(retryMs));
      retryMs = min((uint32_t)10000, retryMs * 2);
    }
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  sensors.begin();
  sensors.setResolution(12);
  queueMutex = xSemaphoreCreateMutex();
  snprintf(bootId, sizeof(bootId), "%08lx%08lx", (unsigned long)esp_random(), (unsigned long)esp_random());
  Serial.println("FROID CONNECT | 2..8 C | delay=30s | sample=5s | firmware=netfix-2");
  Serial.println("Serial command 'n': pause/resume outgoing HTTP (local alarm stays active)");
  // TLS certificate verification can consume several seconds of CPU in Wokwi.
  // Share priority 0 with IDLE0 so tick time-slicing keeps the task watchdog
  // serviced during crypto work. Acquisition/alarm stay on the other core.
  // Keep certificate verification and both watchdogs enabled.
  BaseType_t created = xTaskCreatePinnedToCore(
      networkTask, "network", 16384, nullptr, tskIDLE_PRIORITY, nullptr, 0);
  if (created != pdPASS) Serial.println("NETWORK_TASK_FAILED: insufficient task resources");
}

void loop() {
  static uint64_t nextSample = 0, excursionStart = 0, previousSample = 0;
  static uint32_t sequence = 0;
  static bool pending = false, alarm = false, buzzerActive = false;
  if (Serial.available() && Serial.read() == 'n') {
    networkPaused = !networkPaused;
    Serial.println(networkPaused ? "NETWORK_PAUSED" : "NETWORK_RESUMED");
  }
  uint64_t now = esp_timer_get_time() / 1000;
  if (now < nextSample) { delay(10); return; }
  sensors.requestTemperatures();
  float temperature = sensors.getTempCByIndex(0);
  now = esp_timer_get_time() / 1000;
  // Schedule from the acquisition instant, independently of network requests.
  nextSample = now + SAMPLE_MS - 750; // 12-bit conversion takes approximately 750 ms.
  // Ordered bounds also reject NaN and infinities, without the Xtensa ULT.S
  // instruction emitted by isfinite(), which Wokwi does not implement.
  bool valid = temperature >= -55 && temperature <= 125
               && temperature != DEVICE_DISCONNECTED_C;
  if (previousSample && now - previousSample > MAX_GAP_MS) pending = false;
  bool outside = valid && (temperature < MIN_C || temperature > MAX_C);
  if (outside) {
    if (!pending) { excursionStart = now; pending = true; }
    alarm = now - excursionStart >= ALERT_MS;
  } else { pending = false; alarm = false; }
  digitalWrite(LED_PIN, alarm ? HIGH : LOW);
  if (alarm && !buzzerActive) tone(BUZZER_PIN, 1400);
  if (!alarm && buzzerActive) noTone(BUZZER_PIN);
  buzzerActive = alarm;
  size_t point = min((size_t)(sequence / 6), ROUTE_SIZE - 1);
  Reading reading{sequence, now, time(nullptr), temperature,
                  route[point][0], route[point][1], valid, alarm, 0};
  enqueue(reading);
  Serial.printf("MEASURE seq=%lu temp=%.2f state=%s elapsed=%lus net=%s wifi=%s clock=%s\n",
                (unsigned long)sequence, temperature,
                !valid ? "SENSOR_ERROR" : alarm ? "ALARM" : pending ? "PENDING" : "NORMAL",
                (unsigned long)(pending ? (now - excursionStart) / 1000 : 0),
                networkPaused ? "paused" : "active",
                WiFi.status() == WL_CONNECTED ? "connected" : "waiting",
                time(nullptr) > 1700000000 ? "ready" : "waiting");
  previousSample = now;
  sequence++;
}
