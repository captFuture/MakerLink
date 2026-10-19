#pragma once
/**
 * pn532_uart.h  —  PN532 HSU (High Speed UART) über die ESPHome-uart-Komponente
 *
 * Port von pn532_hsu.h (gleiches Protokoll, gleiche Abläufe), aber ohne
 * Arduino-HardwareSerial: läuft mit ESP-IDF (nötig für Zigbee) und Arduino.
 *
 * Protokoll-Referenz: NXP PN532 User Manual (UM10232)
 * Frame-Format:  00 00 FF LEN LCS TFI(D4) CMD DATA... DCS 00
 * ACK-Frame:     00 00 FF 00 FF 00
 *
 * Verwendung im ESPHome interval-Lambda:
 *   uart:
 *     - id: pn532_uart
 *       tx_pin: ...
 *       rx_pin: ...
 *       baud_rate: 115200
 *
 *   static PN532_UART pn532(id(pn532_uart));
 *   if (!pn532.ready) pn532.begin();
 *   std::string uid = pn532.read_tag();          // "" wenn kein Tag
 */

#include <string>
#include "esphome/components/uart/uart.h"
#include "esphome/core/hal.h"
#include "esphome/core/log.h"

class PN532_UART {
public:
    bool ready = false;

    explicit PN532_UART(esphome::uart::UARTComponent *parent) : _uart(parent) {}

    void begin() {
        _flush();

        // Wakeup-Sequenz: 16x 0x55 + SAMConfig-Frame eingebettet
        const uint8_t wakeup[] = {
            0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55,
            0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55,
            0x00, 0x00, 0xFF, 0x03, 0xFD, 0xD4, 0x14, 0x01, 0x17, 0x00
        };
        _uart.write_array(wakeup, sizeof(wakeup));
        esphome::delay(100);
        _flush();

        // GetFirmwareVersion — prüft ob PN532 antwortet
        const uint8_t cmd_fw[] = {0x02};
        _send(cmd_fw, 1);
        uint8_t resp[32];
        uint8_t rlen = 0;
        if (!_recv(resp, rlen, 1000) || rlen < 5 || resp[1] != 0x03) {
            ESP_LOGE("pn532", "GetFirmwareVersion failed (no response)");
            return;
        }
        ESP_LOGI("pn532", "PN532 found: IC=PN5%02X FW=%d.%d", resp[2], resp[3], resp[4]);

        // SAMConfiguration: normal mode, no timeout, no IRQ
        const uint8_t cmd_sam[] = {0x14, 0x01, 0x00, 0x00};
        _send(cmd_sam, 4);
        if (!_recv(resp, rlen, 500)) {
            ESP_LOGE("pn532", "SAMConfig no response");
            return;
        }
        ESP_LOGI("pn532", "PN532 ready (SAMConfig OK)");
        ready = true;
    }

    // Liest einen passiven ISO14443A Tag (Mifare etc.)
    // Gibt UID als String "F4-96-D2-28" zurück, oder "" wenn kein Tag.
    std::string read_tag() {
        if (!ready) return "";

        // InListPassiveTarget: max 1 Tag, 106kbps ISO14443A
        const uint8_t cmd[] = {0x4A, 0x01, 0x00};
        _send(cmd, 3);

        uint8_t resp[32];
        uint8_t rlen = 0;
        if (!_recv(resp, rlen, 600)) return "";

        // resp: [D5][4B][NbTg][Tg][ATQA 2B][SAK][NFCIDLen][NFCID...]
        if (rlen < 9 || resp[1] != 0x4B || resp[2] == 0) return "";

        uint8_t uid_len = resp[7];
        if (uid_len == 0 || uid_len > 7 || (uint8_t)(8 + uid_len) > rlen)
            return "";

        char buf[6];
        std::string result = "";
        for (uint8_t i = 0; i < uid_len; i++) {
            if (i > 0) result += "-";
            snprintf(buf, sizeof(buf), "%02X", resp[8 + i]);
            result += buf;
        }
        return result;
    }

private:
    esphome::uart::UARTDevice _uart;

    // RX-Buffer leeren
    void _flush() {
        uint32_t t = esphome::millis();
        uint8_t b;
        while (esphome::millis() - t < 20) {
            while (_uart.available()) _uart.read_byte(&b);
        }
    }

    // Checksum: ~(sum) + 1, nimmt nur das untere Byte
    uint8_t _cs(const uint8_t *d, uint8_t n) {
        uint8_t s = 0;
        for (uint8_t i = 0; i < n; i++) s += d[i];
        return (uint8_t)(~s + 1);
    }

    // Frame senden: 00 00 FF LEN LCS D4 CMD DATA... DCS 00
    void _send(const uint8_t *data, uint8_t len) {
        uint8_t frame_len = len + 1;  // TFI(D4) + data
        uint8_t lcs = _cs(&frame_len, 1);

        uint8_t dcs_buf[32];
        dcs_buf[0] = 0xD4;
        for (uint8_t i = 0; i < len && i < 31; i++) dcs_buf[i + 1] = data[i];
        uint8_t dcs = _cs(dcs_buf, len + 1);

        uint8_t frame[40];
        uint8_t pos = 0;
        frame[pos++] = 0x00;        // Preamble
        frame[pos++] = 0x00;        // Start1
        frame[pos++] = 0xFF;        // Start2
        frame[pos++] = frame_len;
        frame[pos++] = lcs;
        frame[pos++] = 0xD4;        // TFI host→PN532
        for (uint8_t i = 0; i < len; i++) frame[pos++] = data[i];
        frame[pos++] = dcs;
        frame[pos++] = 0x00;        // Postamble

        _flush();
        _uart.write_array(frame, pos);
    }

    // Auf Byte warten mit Timeout
    int16_t _read_byte(uint32_t timeout_ms) {
        uint32_t t = esphome::millis();
        uint8_t b;
        while (esphome::millis() - t < timeout_ms) {
            if (_uart.available() && _uart.read_byte(&b)) return b;
            esphome::yield();
        }
        return -1;
    }

    // ACK + Response lesen
    // buf bekommt TFI(D5) + CMD_RESPONSE + DATA, len = Anzahl dieser Bytes
    bool _recv(uint8_t *buf, uint8_t &len, uint32_t timeout_ms) {
        len = 0;

        // --- ACK warten: 00 00 FF 00 FF 00 ---
        const uint8_t ACK[] = {0x00, 0x00, 0xFF, 0x00, 0xFF, 0x00};
        uint8_t ack_pos = 0;
        uint32_t t = esphome::millis();
        while (esphome::millis() - t < timeout_ms) {
            int16_t b = _read_byte(10);
            if (b < 0) continue;
            if ((uint8_t)b == ACK[ack_pos]) {
                if (++ack_pos == 6) break;
            } else {
                ack_pos = ((uint8_t)b == 0x00) ? 1 : 0;
            }
        }
        if (ack_pos < 6) {
            ESP_LOGV("pn532", "ACK timeout");
            return false;
        }

        // --- Response Frame Header: [00] [00] [FF] [LEN] [LCS] ---
        uint32_t t2 = esphome::millis();
        uint8_t hdr[5];
        uint8_t h = 0;
        while (esphome::millis() - t2 < timeout_ms && h < 5) {
            int16_t b = _read_byte(10);
            if (b < 0) continue;
            if (h == 0 && (uint8_t)b == 0x00) { hdr[h++] = b; continue; }
            if (h == 1 && (uint8_t)b == 0x00) { hdr[h++] = b; continue; }
            if (h == 2 && (uint8_t)b == 0xFF) { hdr[h++] = b; continue; }
            if (h >= 3) { hdr[h++] = b; }
        }
        if (h < 5) {
            ESP_LOGV("pn532", "Response header timeout (got %d/5 bytes)", h);
            return false;
        }

        uint8_t data_len = hdr[3];
        if ((uint8_t)(data_len + hdr[4]) != 0x00) {
            ESP_LOGW("pn532", "LCS error: LEN=0x%02X LCS=0x%02X", hdr[3], hdr[4]);
            return false;
        }
        if (data_len == 0 || data_len > 30) {
            ESP_LOGV("pn532", "Unexpected data_len=%d", data_len);
            return false;
        }

        // --- Daten + DCS + Postamble lesen ---
        uint8_t to_read = data_len + 2;
        uint32_t t3 = esphome::millis();
        uint8_t pos = 0;
        while (pos < to_read && esphome::millis() - t3 < timeout_ms) {
            int16_t b = _read_byte(10);
            if (b >= 0) buf[pos++] = (uint8_t)b;
        }
        if (pos < to_read) {
            ESP_LOGV("pn532", "Data timeout: got %d/%d", pos, to_read);
            return false;
        }

        len = data_len;  // buf[0]=TFI(D5), buf[1]=CMD+1, buf[2..]=data
        return true;
    }
};
