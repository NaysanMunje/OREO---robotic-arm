# Limit switch bench test

Minimal firmware to verify limit switch wiring before running the full arm stack.

## Use

```powershell
pio run -t upload
pio device monitor
```

Press each limit — serial output should show the corresponding GPIO going **LOW** (active).

## GPIO (this sketch)

Check `src/main.cpp` for the exact pins configured in this test project. Compare with [../WIRING.md](../WIRING.md) and [../esp32_dm542_stepper_test/README.md](../esp32_dm542_stepper_test/README.md) for production firmware pins.

## Next step

Flash [../esp32_dm542_stepper_test/](../esp32_dm542_stepper_test/) when all limits read correctly.
