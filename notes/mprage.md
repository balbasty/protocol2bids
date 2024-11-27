# MPRAGE

An MPRAGE is really just like a TurboFLASH, except that the inner
loop is slice-encoding, and the outer loop is phase-encoding.

## Sequence diagram

```
                        MatrixSE * (1 + OversamplingSE) * PartialFourierSE
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

* Usually, `SliceOversampling = 0%`
* `j` denotes phase-encoding steps (outer loop)
* `k` denotes slice-encoding steps (inner loop).


## Timing

```
EchoTime = TE
InversionTime = TI
RepetitionTimeExcitation = TR
RepetitionTimePreparation = (MatrixSe * OversamplingSE * PartialFourierSE) * TR + TI + TD
ScanTime = (MatrixPE * OversamplingPE * PartialFourierPE) * RepetitionTimePreparation
```
