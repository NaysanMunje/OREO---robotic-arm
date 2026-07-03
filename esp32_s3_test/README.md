# ESP32-S3 smoke test

Minimal bring-up sketch for the DevKit board (serial, WiFi, or GPIO sanity checks).

```powershell
pio run -t upload
pio device monitor
```

Use before wiring motors. Production firmware: [../esp32_dm542_stepper_test/](../esp32_dm542_stepper_test/).
