# Reverse-engineering the Docan DR-WIFI-04-V2 battery Wi-Fi stick for ESPHome

**Status:** working prototype, documented 27 September 2026  
**Board tested:** `DR-WIFI-04-V2`, PCB date `2025-05-16`  
**Module:** Espressif ESP32-WROOM-32E  
**Battery tested:** Docan/DoCan ZZ 16-cell LiFePO4 packs (BMS firmware `STD05`, `LN10` and `ANZ09`) using the ASCII BMS protocol described below

## Home Assistant result

The decoded BMS data is published as native ESPHome entities. This dashboard combines four battery packs, each with its own stick running the same YAML, and shows stored energy, state of charge, individual cell voltages, cell delta, temperatures, capacity and state of health.

![Home Assistant overview showing stored energy and state of charge of four Docan battery packs](images/home-assistant-overview.png)

Each pack has its own cell and health cards. Packs 1 and 2 use the older BMS generation, packs 3 and 4 the newer `ANZ09` generation.

![Cell voltages and health of packs 1 and 2](images/home-assistant-packs-1-2.png)

![Cell voltages and health of packs 3 and 4](images/home-assistant-packs-3-4.png)

### Historical monitoring

Because the values are normal Home Assistant entities, they can be recorded and compared over time. This makes it possible to monitor pack synchronization, cell-voltage drift, temperature differences and balancing behaviour. The temperature graph shows the environment temperature of the `ANZ09` packs rising while their cell delta is high, which is described under [Environment temperature as a balancing indicator](#environment-temperature-as-a-balancing-indicator).

![Home Assistant history graphs for state of charge, temperatures, cell delta and cell voltages](images/home-assistant-history.png)

<details>
<summary>ESPHome and BMS diagnostics</summary>

The diagnostic entities expose BMS identity, valid-frame counters, raw status words and the automatically discovered BMS address and pack number. Serial numbers are redacted in this screenshot.

![Identity and BMS status of four packs, with serial numbers redacted](images/home-assistant-diagnostics.png)

</details>


## Summary

I replaced the original firmware on a Docan battery Wi-Fi stick with ESPHome. The stick now reads the BMS locally, publishes the values directly to Home Assistant, discovers the connected BMS address automatically, and uses its three onboard LEDs for useful local status.

The configuration currently provides:

- pack voltage, current, power, state of charge and state of health;
- remaining and full-charge capacity, cycle count and internal resistance;
- all 16 cell voltages plus minimum, maximum, average and delta;
- environment, pack, MOS and four cell temperatures;
- operating state: charging, discharging or idle;
- raw BMS alarm/status words for future decoding;
- design capacity and lifetime charge/discharge counters;
- BMS hardware, firmware and model, plus serial-number fields, production date and manufacturer code;
- valid/invalid frame counters and BMS communication state;
- automatic BMS-address discovery and recovery after a communication timeout;
- three automatic status LEDs.

The [generic ESPHome YAML](docan-wifi-stick-esphome.yaml) contains the complete implementation. It does not require a custom ESPHome component.

This is an independent reverse-engineering result, not official Docan documentation. Confirm the PCB revision and pinout before using it on another stick.

## Why this was needed

The stick already contains a capable ESP32, but its original application is cloud-oriented. The goal was to reuse the existing hardware for fully local monitoring in Home Assistant and to avoid adding a second microcontroller or an external UART adapter permanently.

The work had two parts:

1. determine the electrical connections of the ESP32, BMS UART, programming pads and LEDs;
2. capture and decode enough of the BMS protocol to build a robust ESPHome configuration.

## Board identification and orientation

The rear silkscreen identifies the tested board as:

- `DR-WIFI-04-V2`
- `2025-05-16`

For all LED descriptions below, the board is oriented with the **ESP32 module on the left** and the **USB-A plug on the right**. The LEDs then form a vertical row:

1. LED1 at the top;
2. LED2 in the middle;
3. LED3 at the bottom.

This ordering matches the PCB silkscreen.

### Board photographs

![Front of the opened stick, showing the ESP32 and test pads](images/IMG20260927185943.jpg)

*Front of the opened stick: ESP32-WROOM-32E and labelled test pads.*

![Another front overview of the opened stick](images/IMG20260927185934.jpg)

*Second front overview showing the component layout and USB-A plug.*

![Rear of the DR-WIFI-04-V2 board](images/IMG20260927221016.jpg)

*Rear of the PCB with the `DR-WIFI-04-V2` marking, board date and visible traces.*

![Temporary resistor and soldered test leads on the board](images/IMG20260926204648.jpg)

*Temporary bench setup with a soldered 10 kΩ resistor and test leads. I used 10 kΩ because I did not have the initially suggested 20 kΩ resistor; 10 kΩ worked for the test. After cleaning the pads, the stick worked again without the resistor. This is a troubleshooting photograph, not a required permanent modification.*

## Confirmed ESP32 connections

The most important result is that the programming UART and the BMS UART are separate.

| Function | ESP32 GPIO | Status |
|---|---:|---|
| BMS UART TX | GPIO4 | Confirmed and working |
| BMS UART RX | GPIO17 | Confirmed and working |
| Programming/debug UART TX (`U0TXD`) | GPIO1 | Confirmed at the board TX pad |
| Programming/debug UART RX (`U0RXD`) | GPIO3 | Confirmed at the board RX pad |
| LED1 cathode via R9 | GPIO25 | Confirmed and working |
| LED2 cathode via R10 | GPIO26 | Confirmed and working |
| LED3 cathode via R12 | GPIO27 | Confirmed and working |

The BMS connection works at **9600 baud, 8 data bits, no parity, 1 stop bit (8N1)**.

The ESP32-WROOM-32E datasheet maps module pins 10, 11 and 12 to GPIO25, GPIO26 and GPIO27 respectively. That was important because early measurements mixed up physical module pin numbers and GPIO numbers.

## Programming pads

The board exposes pads labelled approximately as follows:

- `GND`, `KEY`, `GND`, `BOOT`, `EN`, `RX`, `TX`, `3V3` on one side;
- `GND`, `TDO`, `TCK`, `TDI`, `TMS`, `3V3` and related test pads on the other side.

The conventional ESP32 serial-flashing connections are therefore available:

| USB-to-UART adapter | Stick |
|---|---|
| TX | RX / GPIO3 |
| RX | TX / GPIO1 |
| GND | GND |
| 3.3 V logic | 3V3 only if the board is not powered elsewhere |

Pull `BOOT` low while resetting with `EN` to enter the ROM download mode. Use a **3.3 V UART**, not 5 V logic. Do not connect two power sources to the board at the same time; if the stick is powered separately, connect only UART TX, RX and common ground.

The USB-A form factor should not by itself be treated as proof that every signal on the board is standard USB data. I only characterized the UART and power-related behavior needed for this project.

## How the LED pinout was found

The initial GPIO guesses did not control the LEDs. The successful process was:

1. With the stick powered, the USB-side terminal of all three LEDs measured 3.3 V.
2. Continuity testing showed that these three terminals share the board's 3.3 V rail.
3. In diode-test mode, placing the red probe on the USB side and the black probe on the other LED terminal illuminated each LED. The forward voltage was approximately 2.3–2.4 V.
4. The cathode traces were then followed through their series resistors to the ESP32 module pins.
5. Temporary ESPHome GPIO outputs confirmed the final mapping electrically and visually.

The final circuit is:

| LED | Series resistor | Resistor marking | ESP32 module pin | GPIO | Logic |
|---|---|---:|---:|---:|---|
| LED1, top | R9 | `472` (4.7 kΩ) | 10 | GPIO25 | Active-low |
| LED2, middle | R10 | `472` (4.7 kΩ) | 11 | GPIO26 | Active-low |
| LED3, bottom | R12 | `472` (4.7 kΩ) | 12 | GPIO27 | Active-low |

All three anodes are tied to 3.3 V. The ESP32 therefore sinks current: **GPIO low turns the LED on; GPIO high turns it off**. In ESPHome this is represented with `inverted: true`.

Earlier candidates such as GPIO32, GPIO33 and GPIO39 were ruled out. GPIO39 is input-only and cannot directly drive an LED. The apparent continuity readings that led to those candidates were high, rising resistance readings through other components rather than a direct copper connection.

## Final status-LED behavior

The test switches used during reverse engineering were removed from the final configuration. The LEDs are now internal outputs with automatic meanings:

| LED | Meaning | Behavior |
|---|---|---|
| LED1 / GPIO25 | ESPHome heartbeat | 120 ms flash every 2 seconds |
| LED2 / GPIO26 | Home Assistant connected | Solid while an API client subscribed to entity states is connected |
| LED3 / GPIO27 | Healthy BMS communication and activity | Solid while communication is healthy, with a 120 ms dark pulse for every valid BMS frame |

For LED2 the configuration uses ESPHome's `api.connected` condition with `state_subscription_only: true`. This deliberately ignores a logger-only client and makes the light a better approximation of an actual Home Assistant connection.

LED3 is switched off if no valid BMS frame has been received for more than 30 seconds. The timeout check runs every 10 seconds, so the visual change can occur up to almost 10 seconds after the 30-second threshold.

## GPIO1, GPIO3 and D1

GPIO1 and GPIO3 are not spare LED outputs. They are the ESP32's default UART0 pins:

- GPIO1 = `U0TXD` and is connected to the board's TX pad;
- GPIO3 = `U0RXD` and is connected to the board's RX pad.

UART0 is used by the ESP32 ROM for downloading firmware and by normal firmware for serial logging. The ESPHome configuration uses `logger: baud_rate: 0`, which disables runtime UART logging, but the pins should still be left alone because they remain important for flashing and may carry ROM boot messages during reset.

D1 is a three-terminal device connected to both GPIO1 and GPIO3. Diode-mode measurements with the red probe on its common terminal gave approximately 0.573 V and 0.700 V toward the two branches. Low-resistance checks associated those branches with GPIO1 and GPIO3.

What is **not yet proven** is where the common D1 terminal ultimately goes. Plausible roles include input protection/clamping or diode-OR activity coupling. It is not the primary LED1 driver: LED1 is conclusively controlled through R9 by GPIO25.

Two useful follow-up measurements would be:

- D1 common terminal to ground;
- D1 common terminal to the LED1 cathode.

## JTAG and other test pads

Two test-pad paths were followed physically:

| Test pad | Resistor | Confirmed GPIO |
|---|---|---:|
| TCK | R25, marked `1001` (1 kΩ) | GPIO13 |
| TDO | R26, marked `1001` (1 kΩ) | GPIO15 |

This matches the ESP32's default JTAG assignment:

| JTAG signal | Default ESP32 GPIO |
|---|---:|
| TDI / MTDI | GPIO12 |
| TCK / MTCK | GPIO13 |
| TMS / MTMS | GPIO14 |
| TDO / MTDO | GPIO15 |

Only the TCK and TDO resistor paths were explicitly continuity-confirmed on this board. TDI and TMS are consistent with the standard ESP32 mapping but still need direct board-level confirmation.

Measurements between the LED cathodes and these JTAG pads were in the megaohm range and rising. They are not the LED control paths.

## GPIO2, D4 and D38

D4 and D38 are nearby three-terminal parts. One shared terminal was found on the 3.3 V rail, and another node appears to be reached from GPIO2 through a resistor. However, measurements from LED2 and LED3 to these devices were in the megaohm range and rose while measuring. They are therefore not direct LED drivers.

Their exact purpose remains unresolved; they may be part of power, supervision or another support circuit. GPIO2 is also an ESP32 strapping pin, so the safe choice is to leave it unused until this circuit is understood.

## BMS serial protocol

The BMS uses printable ASCII hexadecimal frames. Every captured frame starts with `~` and ends with carriage return (`\r`). A frame can be described as:

| Full-frame character position | Size | Meaning |
|---:|---:|---|
| 0 | 1 | Start marker `~` |
| 1 | 2 | Protocol/version field, observed `22` |
| 3 | 2 | BMS address |
| 5 | 2 | Function family, observed `4A` |
| 7 | 2 | Command in requests or return code in responses |
| 9 | 4 | Length word |
| 13 | variable | Payload as ASCII hex |
| final 4 | 4 | ASCII checksum |

The lower 12 bits of the four-character length word are the **number of ASCII payload characters**, not the number of decoded bytes. The count must therefore be even.

Responses carry the return code (`RTN`, `00` for success) at positions 7–8 instead of the command (`CID2`). A response therefore does not say which request it answers. The ESPHome configuration sends one request at a time, remembers the pending `CID2` (and, for `B0`, the data group) and interprets the next valid response accordingly.

### BMS generations observed

Four DoCan ZZ 16 kWh packs were monitored in parallel: two older and two newer units. Service `51` (see below) reports two BMS generations:

| | Older packs | Newer packs |
|---|---|---|
| BMS model | `16S200JC26` | `16S200JC35` |
| BMS firmware | `STD05`, `LN10` | `ANZ09` |
| BMS hardware | `T1` | `T1` |
| Service `42` live layout | leading `00` byte, then SOC | starts directly with SOC |

Raw status words also differ per firmware. For example, during normal operation the FET status word was `0x1023` on the `STD05` and `ANZ09` packs and `0x23` on the `LN10` pack. Compare raw status words only between packs running the same BMS firmware.

### Checksum

The checksum is the 16-bit two's complement of the sum of every ASCII byte after `~`, up to but not including the checksum itself:

```text
sum = ASCII(frame[1 ... character_before_checksum])
checksum = (-sum) & 0xFFFF
```

The checksum is appended as four uppercase hexadecimal characters.

### Confirmed requests

| CID2 | Purpose | Request or addressed command tail | Schedule used |
|---|---|---|---:|
| `50` | Discover BMS address | `~22004A500000FDA2\r` (broadcast, address `00`) | Every 5 s until discovered |
| `42` | Live telemetry | `42E00200` | Every 10 s |
| `51` | BMS hardware, firmware and model | `510000` | Once after every discovery, retried every 30 s until parsed |
| `B0` | Data group 03: serial numbers, production date, manufacturer | `B0600A000103FF00` | Once after every discovery, retried every 30 s until parsed |
| `B0` | Data group 04: lifetime counters | `B0600A000104FF00` | Every 60 s |

Requests other than discovery are prefixed with `~22<address>4A` and followed by the checksum. The `B0` INFO field has this layout:

```text
00 | operation (01 = read) | data group | FF | 00
```

Only operation `01` (read) has been used. Data groups 03 and 04 are confirmed; other groups have not been read yet.

Addressed frames are built at runtime. For example, with address `01` the live request is:

```text
~22014A42E00200FD29\r
```

One observed lifetime request and response at address `00` were:

```text
TX: ~22004AB0600A000104FF00FB6D\r
RX: ~22004A00D030B0000104FF12445783C07AA8000005440000048D02D80266F38E\r
```

### Identity responses

The service `51` payload contains three NUL-padded ASCII fields followed by bytes that are not yet understood:

| Payload offset | Field |
|---:|---|
| 0–9 | BMS hardware, e.g. `T1` |
| 10–19 | BMS firmware, e.g. `ANZ09` |
| 20–29 | BMS model, e.g. `16S200JC35` |
| 30 onward | 7 unknown bytes, logged only |

The `B0` data group 03 response is recognized by `payload[0] = B0`, `payload[2] = 01`, `payload[3] = 03` and `payload[4] = FF`. It was confirmed on a DoCan ZZ 16S pack:

| Payload offset | Field |
|---:|---|
| 0 | `B0` |
| 1 | `03` |
| 2 | Operation, `01` |
| 3 | Data group, `03` |
| 4 | `FF` |
| 5 | Data length, observed `0x71` (113) |
| 6–35 | Serial-number field 1, ASCII, NUL padded |
| 36–65 | Serial-number field 2, ASCII, NUL padded |
| 66–95 | Serial-number field 3, ASCII, NUL padded |
| 96–98 | Production date as binary `YY MM DD`, e.g. `1A 06 1A` = 2026-06-26 |
| 99 onward | Manufacturer code, ASCII, NUL padded |

The meaning of the three separate serial-number fields has not been established. They are published as three diagnostic text entities.

On all four packs, the first serial-number field had the form `AAAYYMMDDNNNN`: a three-letter prefix, a six-digit date and a four-digit number. The production date in bytes 96–98 was consistently two to five days after the date in that serial number. A plausible interpretation is that the serial number carries the cell or module date and the production date marks final pack assembly, but this has not been confirmed.

## Automatic BMS-address discovery

Hard-coding the address worked during early tests but was not robust because different packs answered at addresses such as `00`, `01` and `02`.

The final logic does this:

1. initialize the address to `0xFF`, meaning unknown;
2. broadcast `~22004A500000FDA2\r` every 5 seconds;
3. accept a checksummed zero-length success response;
4. learn the address from characters 3–4 of that response;
5. show the corresponding pack number as address + 1;
6. send subsequent telemetry requests to the discovered address;
7. forget the address and restart discovery after a BMS timeout.

Address `0x00` is valid, which is why `0xFF` is used as the unknown sentinel.

Only the zero-length discovery response is used to learn the address. This prevents an ordinary response-header value from accidentally changing it.

## Decoded live telemetry payload

All multi-byte values below are big-endian. `be16(i)` means a 16-bit unsigned value starting at decoded payload byte `i`; signed temperature and current fields use a signed 16-bit interpretation.

### Fixed beginning

Two layouts have been observed. Older BMS firmware (`STD05`, `LN10`) starts the payload with an extra `00` byte; newer firmware (`ANZ09`) starts directly with the state of charge. Let `b` be the start offset: `b = 1` for the older layout and `b = 0` for the newer one.

| Payload offset | Field | Scale |
|---:|---|---:|
| `b + 0` | State of charge | `be16 / 100` % |
| `b + 2` | Pack voltage | `be16 / 100` V |
| `b + 4` | Cell count `N` | 1–16 |
| `b + 5` onward | `N` cell voltages | each `be16 / 1000` V |

Let `p = b + 5 + 2N`, immediately after the cell voltages:

| Relative offset | Field | Scale |
|---:|---|---:|
| `p + 0` | Environment temperature | signed `be16 / 10` °C |
| `p + 2` | Pack average temperature | signed `be16 / 10` °C |
| `p + 4` | MOS temperature | signed `be16 / 10` °C |
| `p + 6` | Temperature-sensor count `T` | byte |
| `p + 7` onward | `T` individual temperatures | each signed `be16 / 10` °C |

Let `q = p + 7 + 2T`, immediately after the individual temperatures:

| Relative offset | Field | Scale |
|---:|---|---:|
| `q + 0` | Pack current | signed `be16 / 100` A |
| `q + 2` | Pack internal resistance | `be16 / 10` mΩ |
| `q + 4` | State of health | `be16` % |
| `q + 6` | User-defined number | one byte, currently skipped |
| `q + 7` | Full-charge capacity | `be16 / 100` Ah |
| `q + 9` | Remaining capacity | `be16 / 100` Ah |
| `q + 11` | Cycle count | `be16` |

Power is calculated locally as voltage × current. The operating state is derived as:

- charging above +0.10 A;
- discharging below −0.10 A;
- idle between those thresholds.

### Selecting the layout

The configuration does not rely on the firmware version to pick `b`. It evaluates both candidates and accepts a candidate only if:

- state of charge, pack voltage and cell count are in plausible ranges;
- every cell voltage is between 2.000 and 4.000 V;
- the sum of the cell voltages matches the pack voltage within 0.5 V.

If both candidates fit, the one with the smallest deviation is used. If neither fits, the frame is counted as invalid.

An earlier version tried `b = 1` first and accepted it on range checks alone. On `ANZ09` packs a one-byte-shifted read can pass those checks when the low byte of the state of charge is small and the low byte of the voltage falls in a narrow range; the cell count is then read from the high byte of cell 1 (`0x0C` or `0x0D`). Such frames usually failed later at the temperature-count check, and rarely published wrong values. The symptom was about 0.6–0.7 % invalid frames (roughly 1 in 150) on `ANZ09` packs only, occurring in clusters because state of charge and voltage change slowly. A simulation over 20,000 random `ANZ09` frames reproduced 0.61 %. After switching to the cell-sum check, all four packs reported 0 invalid frames over more than 22,000 frames each.

### Status words

The final part of the live payload contains status fields. Voltage, current, temperature, alarm, FET, balance-low, balance-high, machine and I/O status are exposed as raw diagnostic entities. Their vendor-specific individual bits have not yet been confidently decoded.

Ten-second logs over one week show this behaviour of the voltage status word. These meanings are observations, not vendor-confirmed definitions:

| Bit | Set | Cleared | Likely meaning |
|---|---|---|---|
| `0x10` | Highest cell about 3.55–3.58 V (both generations) | Below about 3.45 V | Cell over-voltage warning |
| `0x01` | At the top of charge (seen on `ANZ09` only) | Below about 3.40 V | Charging blocked / pack full |

A value of `0x11` means both bits are set. While `0x01` is set, the pack reports exactly 0.00 A and neither charges nor discharges, even with a small load on the bus.

### Environment temperature as a balancing indicator

On `ANZ09` packs, the environment temperature rises from about 29 °C to 34–36 °C whenever the cell delta exceeds about 20–30 mV, and falls back when the delta is small again. The correlation with the cell delta was 0.71 and 0.77 on two packs. This happens both on the voltage plateau and at the top of charge, which suggests that the active balancer starts on cell delta regardless of cell voltage. Until the balance status words are decoded, this temperature is a useful indirect "balancer running" signal.

## Decoded lifetime-counter payload

The lifetime response is recognized by:

```text
payload[0] = B0
payload[2] = 01
payload[3] = 04
payload[4] = FF
```

The confirmed fields are:

| Payload offset | Field | Scale |
|---:|---|---:|
| 10–11 | Design capacity | `be16 / 100` Ah |
| 12–15 | Lifetime charged capacity | `be32 / 10` Ah |
| 16–19 | Lifetime discharged capacity | `be32 / 10` Ah |
| 20–21 | Lifetime charged energy | `be16 / 100` kWh |
| 22–23 | Lifetime discharged energy | `be16 / 100` kWh |

The 0.1 Ah scale of the 32-bit lifetime-capacity counters was checked against the corresponding energy counters and the values displayed by the system.

## Example validated values

The following values were decoded from real captured frames and were internally consistent:

| Measurement | Observed value |
|---|---:|
| Pack voltage | 52.64 V |
| Pack current | −0.70 to −0.82 A |
| Calculated power | −37 to −43 W |
| State of charge | about 51.87–51.89 % |
| State of health | 100 % |
| Remaining capacity | about 174.95–175.02 Ah |
| Full-charge capacity | 337.28 Ah |
| Cycle count | 4 |
| Cell count | 16 |
| Cell voltage range | 3.289–3.291 V |
| Cell delta | 1–2 mV |
| Environment temperature | 24.4 °C |
| Pack average temperature | 20.0 °C |
| MOS temperature | 21.8 °C |
| Four cell temperatures | 20.2, 20.4, 19.8, 19.7 °C |
| Design capacity | 314.00 Ah |
| Lifetime charged capacity | 134.80 Ah |
| Lifetime discharged capacity | 116.50 Ah |
| Lifetime charged energy | 7.28 kWh |
| Lifetime discharged energy | 6.14 kWh |

These values also provided useful checks for signed current, decimal scaling and dynamic payload offsets.

## ESPHome implementation details

The generic configuration uses ESP-IDF and declares an 8 MB flash size, matching the configuration tested on this hardware. Its main behaviors are:

- UART debug captures complete frames ending in carriage return;
- every response is checked for framing, hexadecimal validity, declared length and checksum before use;
- malformed frames increment an invalid-frame counter and are logged at WARN level with a reason (`header`, `checksum`, `length mismatch`, `temperature count`, `no consistent live layout`, ...) and the raw frame;
- valid frames increment a valid-frame counter and refresh BMS communication state;
- requests are queued and sent one at a time with a 700 ms gap, so every response can be matched to the pending request;
- live telemetry is requested every 10 seconds;
- lifetime counters are requested every 60 seconds;
- battery identity (services `51` and `B0` group 03) is read once after every discovery and retried every 30 seconds until both responses have been parsed, so a swapped pack is picked up again;
- unexpected valid responses are logged as raw hexadecimal for analysis instead of being decoded;
- diagnostic buttons refresh live telemetry, lifetime counters and battery info, restart discovery and reset the frame counters;
- BMS communication becomes false after more than 30 seconds without a valid frame;
- cell entities are throttled to 30 seconds to reduce Home Assistant recorder traffic;
- aggregate pack values update on each live response;
- API encryption, OTA, fallback AP and captive portal remain available.

The UART parser uses an inline ESPHome lambda. No cloud connection and no external custom component are required.

Copy the [generic ESPHome YAML](docan-wifi-stick-esphome.yaml) into your ESPHome configuration, set a unique `esphome.name` and `friendly_name`, and define these values in your local `secrets.yaml`:

```yaml
wifi_ssid: "your-ssid"
wifi_password: "your-wifi-password"
docan_api_encryption_key: "your-generated-api-key"
docan_ap_password: "your-fallback-ap-password"
```

Change `esphome.name` and `friendly_name` for each stick. Do not give two sticks the same ESPHome name.

### Running several packs

Four packs have been run with identical YAML on four sticks. Per pack, only `esphome.name`, `friendly_name`, `wifi.use_address` (when a fixed address is used), the fallback AP SSID and the two device-specific secrets differ.

- Do not connect the USB ports of several packs to one ESP32 without per-channel galvanic isolation. The USB ground is most likely the pack's B−, and a pack with an open MOSFET can sit at a different potential.
- The RS485 link between packs is a cleaner option for a single ESP32: a passive listener built with a 3.3 V auto-direction RS485 module whose TXD is tied high so that it never transmits. This has not been built yet.
- Home Assistant `button-card` templates written with YAML `>-` folding must not contain `//` comments inside the JavaScript. Folding joins the lines, so the comment swallows the statement that follows it.

## What is confirmed and what remains open

### Confirmed

- PCB identity and ESP32 module family;
- BMS UART on GPIO4/GPIO17 at 9600 8N1;
- serial programming UART on GPIO1/GPIO3;
- LED1/2/3 on GPIO25/GPIO26/GPIO27 through R9/R10/R12;
- common 3.3 V LED anodes and active-low drive;
- working checksum and length validation;
- BMS-address discovery;
- live telemetry and lifetime-counter decoding;
- both live-payload layouts (older `STD05`/`LN10` and newer `ANZ09` BMS firmware) and their automatic selection;
- BMS hardware, firmware and model (service `51`);
- serial-number fields, production date and manufacturer code (`B0` data group 03);
- the `B0` read request layout for data groups 03 and 04;
- automatic status-LED operation in ESPHome;
- TCK through R25 to GPIO13 and TDO through R26 to GPIO15.

### Still open

- exact purpose and common-node destination of D1;
- exact purpose of D4/D38 and the surrounding GPIO2 circuit;
- direct continuity confirmation of the TDI and TMS pads;
- meanings of the individual raw status bits; only voltage-status bits `0x10` and `0x01` have observed behaviour so far;
- the last 7 bytes of the service `51` response and the meaning of the three serial-number fields;
- other `B0` data groups (thresholds and balancer settings are probably there) and the `B0` write operation (probably `02`, untested);
- services such as `44`, `47` and `92` known from related protocols (untested);
- whether other Docan PCB revisions have the same pinout and protocol layout.

No BMS setting-changing or control commands were investigated. This work intentionally focuses on read-only monitoring.

## Safety and reproducibility notes

- Disconnect the stick from the battery/inverter while soldering or continuity-testing.
- Never use resistance or diode mode on a powered board.
- Use 3.3 V UART logic.
- Confirm ground and supply rails before connecting a flasher.
- Avoid driving ESP32 strapping pins such as GPIO2, GPIO12 and GPIO15 during boot.
- Preserve a copy of the original firmware if you have a reliable way to read it before erasing.
- Expect other PCB revisions to differ; verify traces instead of relying only on the board's physical resemblance.
- Test the configuration on the bench before depending on it for alarms or protection. The BMS itself, not ESPHome or Home Assistant, must remain responsible for battery protection.

## Useful follow-up work for the community

Contributions that would help complete this reverse engineering include:

- clear photographs of other board revisions;
- continuity measurements for D1, D4, D38, TDI and TMS;
- raw frames captured while specific alarms or balancing states are deliberately active;
- a read-only scan of `B0` data groups `00`–`0F` with the raw replies logged. Look for likely cell thresholds such as `0D48` (3400 mV), `0DDE` (3550 mV) and `0E42` (3650 mV). Do not try write operations;
- a passive RS485 listener that monitors several packs from one ESP32;
- manufacturer documentation for the DR-1363 data groups;
- confirmation of the YAML on Noon, YP, LN, Panda or other Docan pack families;
- a safe decoding table for the raw voltage/current/temperature/alarm/FET/I/O status bits.

Additional leads from an independent analysis of the original `wifi_32` firmware (not yet verified against captured responses from this pack):

- Check the high nibble of the four-character LENGTH word. It appears to be `(-sum of the three LENID nibbles) & 0x0F`. The current ESPHome parser checks the 12-bit payload length and frame checksum, but not this length checksum.
- Capture a response to read-only command `0x84` and compare it with the working `0x42` live-telemetry response and simultaneous app values. The original firmware reportedly polls `0x84`, with a different, apparently fixed response layout. Do not assume the two responses are interchangeable.
- The ESPHome parser now matches each response to the pending request and only decodes `0x42`, `0x51` and `B0` group 03/04 responses; anything else is logged as raw hex. When adding another command, give it its own branch in the parser rather than relying on the live-telemetry decoder.
- Investigate read-only commands `0x80`, `0x83` and `0x4D` separately, and compare their responses with the still-unknown status fields and BMS clock. Treat firmware-derived field names and scales as hypotheses until checked against captured frames.
- Compare the original firmware's reported `0x50`, `0x51`, `0xA0`, `0xB0` and `0xB1` poll cycle with actual UART captures; record BMS model, firmware version and address for each capture.
- Map the original firmware's two update paths without running an update. The active image contains distinct `BMS_OTA` and `sys_OTA` code and a shared-looking `download_upgrade_file`/`/drgk/web/binFile/` path. The BMS path includes `bms_bin_V%d.%d.%d.bin`, update-state persistence, and log messages `send reset cmd`, `send file info` (file size and packet count), and `send data %d`, plus timeout/read/write error handling. The stick path uses ESP-IDF's `esp_ota_write`, selects the next boot partition and restarts. Determine from disassembly or a passive capture how the update type selects a file and destination, whether the versioned BMS filename is remote or only local, and the exact BMS UART packet format, acknowledgements, integrity checks and recovery behavior. These strings establish the broad workflow, not a verified update procedure.
- Investigate the factory-looking Wi-Fi configuration found in one original firmware dump's NVS partition (SSID `DR_New_Energy`, with a preconfigured password). Determine whether the stick joins that network as a client or creates its own access point, and whether the entry is only a leftover production/test setting. This single dump does not prove every unit ships with the same credentials, establish the Wi-Fi mode, or show that a user's network was never configured. If a working credential is shared across production devices, the manufacturer should address it.

The original firmware also appears to support remote settings and BMS firmware updates. Those write paths are outside the scope of this read-only project. Do not publish a raw flash dump: its NVS partition may contain Wi-Fi credentials or other device-specific data.

When sharing captures, remove Wi-Fi credentials, API keys, MAC addresses and any serial numbers you consider private.

## References

- [Espressif ESP32-WROOM-32E / ESP32-WROOM-32UE datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-wroom-32e_esp32-wroom-32ue_datasheet_en.pdf)
- [Espressif ESP32 schematic checklist: UART0 download and logging pins](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32/schematic-checklist.html)
- [Espressif: configuring other JTAG pins](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-guides/jtag-debugging/configure-other-jtag.html)
- [ESPHome logger component](https://esphome.io/components/logger/)
- [ESPHome native API component](https://esphome.io/components/api/)
