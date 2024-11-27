# TurboFLASH

A TurboFLASH is a FLASH with magnetisation preparation (inversion pulse),
and a sequence of (excited) phase-encode steps acquired after each inversion
pulse. In general, there is one inversion pulse per slice, but the
acquisition can also be segmented, in which case a subset oh phase-encode
steps are acquired after each inversion pulse.

* Siemens: `tfl`

## Sequence diagram

```
                        MatrixSE * OversamplingSE * PartialFourierSE
                 ┌───────────────────────────────────────────────────────┐
RF:  180           α            α            α            α            α                  180
      ┃     ...    ┃            ┃            ┃    ....    ┃            ┃               ... ┃
      ┊            ┊────[TR]───→┊────[TR]───→┊            ┊────[TR]───→┊                   ┊
      ┊────[TI]───→┊            ┊            ┊            ┊            ┊────────[TD]──────→┊
      ┊─────────────────────────────────────────[TRprep]──────────────────────────────────→┊
      ┊            ┊─[TE]─┒     ┊─[TE]─┒     ┊            ┊─[TE]─┒     ┊─[TE]─┒     ┊      ┊
ADC:  ┊            ┊    █████   ┊    █████   ┊    ....    ┊    █████   ┊    █████   ┊      ┊
FE:   ┊            ┊  --+++++   ┊  --+++++   ┊            ┊  --+++++   ┊  --+++++   ┊      ┊
PE:   ┊            ┊  +j     -j ┊  +j     -j ┊            ┊  +j     -j ┊  +j     -j ┊      ┊
SE:   + ?          +- +k     -k +- +k     -k +-           +- +k     -k +- +k     -k ┊      ┊
```

* Usually, `SliceOversampling = 100%`
* `j` denotes phase-encoding steps (inner loop)
* `k` denotes slice-encoding steps (outer loop).


## Timing

```
EchoTime = TE
InversionTime = TI
RepetitionTimeExcitation = TR
RepetitionTimePreparation = (MatrixSe * OversamplingSE * PartialFourierSE) * TR + TI + TD
ScanTime = (MatrixPE * OversamplingPE * PartialFourierPE) * RepetitionTimePreparation
```

## Distortion across readout

```
        ┊──[TotalReadoutTime*Ov]──→┊
ADC:    ▐██████████████████████████▌
        ┃ ┃ ┃ ┃      ...     ┃ ┃ ┃ ┃
       └────────────────────────────┘
        MatrixFE * FreqOversampling
```

Usually, `FreqOversampling = 200%`.

`PixelBandwidth` (in `Hz/pixel`) is provided per _acquisition pixel_
(without considering oversampling). The `DwellTime` is the time between two
frequency-encoded points of the _real acqisition matrix_ (including
oversampling).

```
DwellTime = 1/BandwidthPerPixel
TotalReadoutTime = DwellTime * MatrixFE
```
