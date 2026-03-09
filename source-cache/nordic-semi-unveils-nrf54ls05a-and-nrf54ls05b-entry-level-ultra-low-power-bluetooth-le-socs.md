# Nordic Semi unveils nRF54LS05A and nRF54LS05B entry-level, ultra-low-power Bluetooth LE SoCs

Nordic Semiconductor introduced the nRF54LS05A and nRF54LS05B as entry-level, ultra-low-power Bluetooth Low Energy Arm Cortex-M33 microcontrollers. They are designed either to act as the main wireless SoC in simple products such as sensors, tags, beacons, remotes, and PC peripherals, or to serve as a Bluetooth LE companion device in more advanced systems.

Both chips run at 128 MHz and use Nordic’s fourth-generation Bluetooth LE radio. They also include analog and digital interfaces, advanced security features, and 0.5 MB of non-volatile memory. The main difference between the two parts is memory capacity: the nRF54LS05A has 64 KB of RAM, while the nRF54LS05B has 96 KB.

![Nordic nRF54LS05A and nRF54LS05B](https://www.cnx-software.com/wp-content/uploads/2026/03/Nordic-nRF54LS05A-nRF54LS05B.jpg "nRF54LS05A / nRF54LS05B product image")

## Main specifications

- CPU: Arm Cortex-M33 at 128 MHz, rated at 250 CoreMark/mA at 3V and 500 CoreMark total.
- Memory and storage: 64 KB RAM on the nRF54LS05A, 96 KB RAM on the nRF54LS05B, and 508 KB of NVM.
- Wireless: Bluetooth LE at 1 Mbps and 2 Mbps, plus a 2.4 GHz proprietary mode with GFSK at 1 Mbps, 2 Mbps, and 4 Mbps.
- Radio details: single-ended antenna output with on-chip balun, 128-bit AES/ECB/CCM/AAR coprocessor, transmit power from -10 dBm to +4 dBm, and -96 dBm receive sensitivity for 1 Mbps Bluetooth LE.
- I/O and peripherals: up to 37 GPIOs, three serial interfaces with EasyDMA for I2C, SPI, and UART, a 4-channel SAADC, global RTC, PWM, QDEC, watchdog, 32-bit timers, and a temperature sensor.
- Clocking and power: single 32 MHz crystal operation, optional 32.768 kHz crystal, supply voltage from 1.7 V to 3.6 V, radio current of 3.4 mA for Rx and 4.8 mA for Tx at 0 dBm, and sleep modes from 0.6 μA to 1.2 μA.
- Packaging: 6 x 6 mm QFN48 package with 0.4 mm pitch.

![Simplified block diagram of the nRF54LS05 family](https://www.cnx-software.com/wp-content/uploads/2026/03/nRF54LS05A-nRF54LS05B-block-diagram.webp "Simplified block diagram")

The new SoCs are supported by the nRF Connect SDK, including a bare-metal option. Nordic says they provide a smooth migration path from the nRF52 series to speed development.

The article notes a few limitations as well. The new chips do not support Bluetooth Channel Sounding and they do not support Bluetooth Mesh.

Nordic also emphasizes reduced design complexity, smaller size, lower cost, mature Bluetooth LE radio and stack support, extended battery life, and pin-to-pin compatibility inside the wider nRF54 family.

At the time of the article, documentation was already online, but most of it was still general family-level material rather than highly detailed documentation for the two exact chips.

![nRF54LS05-DK development kit](https://www.cnx-software.com/wp-content/uploads/2026/03/nRF54LS05-DK.webp "nRF54LS05-DK development kit")

Developers will be able to evaluate the parts using the nRF54LS05-DK, a development board based on the nRF54LS05B while also emulating the lower-memory nRF54LS05A. The board includes an nRF5340 debugger chip, a PMIC, headers for all I/O, four user buttons, and four LEDs.

Nordic says the two SoCs and the development kit are available through an early access program now, with production planned for the third quarter of 2026.
