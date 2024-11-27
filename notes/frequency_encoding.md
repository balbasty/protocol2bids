# Distortion across the frequency-encoding direction

```
        ┊────[TotalReadoutTime]──→┊
ADC:    ▐██████████████████████████▌
        ┃ ┃ ┃ ┃      ...     ┃ ┃ ┃ ┃
       └────────────────────────────┘
MatrixFE * (1 + FreqOversampling) * PartialFourierFE
```

Usually, `FreqOversampling = 100%`.

`PixelBandwidth` (in `Hz/pixel`) is provided per _acquisition pixel_
(without considering oversampling). The `DwellTime` is the time between two
frequency-encoded points of the _real acqisition matrix_ (including
oversampling).

```
DwellTime = 1/BandwidthPerPixel
TotalReadoutTime = DwellTime * MatrixFE * (1 + FreqOversampling) * PartialFourierFE
```

What matters for distortion correction is the `EffectiveDwellTime`, i.e.,
the time between two _pixels_ in the _reconstructed_ image.

# Partial Fourier + Oversampling + Acceleration

**NOTE** that in practice there is _NEVER_ acceleration along the
readout direction

```
          │──────→│ DwellTime

 -8  -7  -6  -5  -4  -3  -2  -1   0  +1  +2  +3  +4  +5  +6  +7
                                  ↓
┌┈┈┈┬┈┈┈┬┈┈┈┬┈┈┈┬───┬───┬───┬───┬───┬───┬───┬───┬┈┈┈┬┈┈┈┬┈┈┈┬┈┈┈┐
│ ◇ │ ◇ │ ■ │ □ │ ■ │ □ │ ■ │ □ │ ■ │ □ │ ■ │ □ │ ■ │ □ │ ■ │ □ │
└┈┈┈┴┈┈┈┴┈┈┈┴┈┈┈┴───┴───┴───┴───┴───┴───┴───┴───┴┈┈┈┴┈┈┈┴┈┈┈┴┈┈┈┘
                        └────────────────┘
                           Calibration=4
                └───────────────────────────────┘
                        AcquisitionMatrix=8
└───────────────────────────────────────────────────────────────┘
              AcquisitionMatrix * (1 + Oversampling=2)
        └───────────────────────────────────────────────────────┘
                RealAcquisitionMatrix * PartialFourier=7/8

■ = Acquired
□ = Skipped for acceleration
◇ = Skipped for partial fourier
```
