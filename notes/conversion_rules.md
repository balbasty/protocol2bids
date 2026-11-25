# Conversion rules: review and sources

Target: the sidecar that **dcm2niix** would have written from the DICOMs
(BIDS keys + dcm2niix keys), guessed from the printout.

Status: ✅ confirmed by sources, 🔧 corrected after review, ⚠️ uncertain
(implemented as best guess or deliberately not written).

Main sources:
- dcm2niix source: `console/nii_dicom_batch.cpp` (NDB), `console/nii_dicom.cpp`
  (ND), and the vendor READMEs (`Siemens/`, `Philips/`, `GE/`).
- dcm2niix validation data (`neurolabusc/dcm_qa*`), in particular M. Harms'
  spreadsheet `dcm_qa/In/TotalReadoutTime/PF_PAT_POS_PFOV_PEres_INTERP_test2_2017.09.22.xlsx`.
- BIDS specification (`src/schema/objects/metadata.yaml`).
- CMRR multiband slice-order note (`CMRR_MB_Slice_Order.pdf`, rev 1.1).
- Philips slice-order script by G. Gilbert (Philips), "validated for R5.3.1":
  `irenevav/UBC_MRI_Centre_AnalysisHub/fMRISliceOrder_R531_Elition_WIP_FSL.m`.
- Real sidecars from OpenNeuro mirrors (e.g. ds003540, ds004078, ds005479).

## Siemens

| Rule | Status | Notes |
| --- | --- | --- |
| `PhaseEncodingDirection`: A>>P → `j-`, P>>A → `j`, R>>L → `i`, L>>R → `i-` (dcm2niix LAS-like output) | ✅ | Requires the `nii2axes` fix (positive axes were reversed). Mapping goes through the NIfTI affine, so it holds for any orientation of the file. |
| 3D (non-EPI) scans: no `PhaseEncodingDirection` | 🔧 | dcm2niix ≥ 2024 (issue #849) stops reporting the polarity for 3D sequences; we write `PhaseEncodingAxis` instead. |
| `EffectiveEchoSpacing = EchoSpacing × (1 + PhaseOversampling) / R` | ✅ | Partial Fourier, phase resolution, phase FOV and interpolation do not change it (Harms). Off by up to ~0.7 % when the PE line count is rounded. |
| `TotalReadoutTime = EES × (ReconMatrixPE − 1)` | ✅ | Interpolation doubles `ReconMatrixPE`, so it doubles TRT. |
| `BandwidthPerPixelPhaseEncode = 1 / (EES × ReconMatrixPE)` | ✅ | |
| `DwellTime = 1 / (PixelBandwidth × BaseResolution × 2)` | 🔧 | Includes the 2× readout oversampling (CSA RealDwellTime). Was missing the ×2. |
| `AcquisitionMatrixPE = round(Base × PhaseRes × PhaseFOV)` | ✅ | Excludes oversampling, PF, PAT. E.g. 256 × 93.75 % → 240. |
| `PhaseEncodingSteps = AcqPE × (1 + PO) × PF` | ✅ | |
| `EchoTrainLength` (EPI) `= PhaseEncodingSteps / R` | ✅ | Not the console "EPI factor". Old VB `ep2d_bold` writes 1 in DICOM (dcm2niix omits it); we still write the physical value. |
| `SpacingBetweenSlices` (2D) `= thickness × (1 + dist. factor)` | ✅ | |
| `SpacingBetweenSlices` (3D) | 🔧 | Not written. "Dist. factor" is the gap between *slabs*; dcm2niix writes nothing for single-slab 3D. (The ABIDE2 reference sidecars apply the factor to partitions, which is wrong.) |
| Interleaved order: odd N → 1,3,5,…,2,4,…; even N → 2,4,…,1,3,… (1-based) | ✅ | `SliceTiming = rank × (TR − DelayInTR) / N`. Real data are quantized (~2.5 ms). |
| CMRR multiband interleaved | 🔧 | Always starts at slice 0; nshots ≤ 4: every other slice; nshots = 6: 0,2,4,1,5,3; even nshots > 6: step `n/2 − 1` (minus 1 if even), modulo nshots (matches the 36-slice MB2 dcm_qa data). ⚠️ The CMRR PDF's 10-shot example does not follow the modulo rule. |
| Siemens product SMS slice timing | ✅ (empirical) | No documentation found; rule inferred from the scanner-reported times of real dcm2niix sidecars (OpenNeuro, dcm_qa_*) and checked on **374/374** product-SMS sidecars (VE11 to XA61; CMRR sidecars: 1108/1108 with the CMRR rule). Slices k and k + nexc share their time (nexc = N/MB). Ascending/descending: 1..nexc / nexc..1. Interleaved, **even nexc**: even groups first then odd groups, with group nexc moved to position floor(nexc/4) of the even half and group 1 to the same position of the odd half (nexc=8 → 2,4,8,6,3,5,1,7), so that the adjacent groups nexc and 1 are half a TR apart. Interleaved, **odd nexc**: single-band parity rule applied to the total N on VB/VD/VE/XA10–XA20, to nexc on XA30+ (version boundary between XA11 and XA30 not pinned down; when the version is unknown and MB is even, no `SliceTiming` is written). Interleaved-descending: no sample. Timing: rank × (TR − delay) / nexc (scanner times are slightly shorter and quantized to 2.5 ms). |
| Concatenations > 1, sequential multi-slice | ⚠️ | `SliceTiming` not written. |
| `SpoilingRFPhaseIncrement = 50°` for product FLASH-based sequences | ✅ (medium) | Pulseq maintainers, Preibisch & Deichmann 2009, PLOS One 2025. No Siemens document found. Only written for `SIEMENS:` sequences with RF spoiling. |
| `ScanningSequence` / `SequenceVariant` / `ScanOptions` | 🔧 | Aligned on real dcm2niix sidecars: `ep2d_bold` EP / SK / FS; CMRR bold adds SS; `ep2d_diff` EP / SK\SP; `tfl` GR\IR / SK\SP\MP / IR; `gre_field_mapping` GR / SP; `tse` SE / SK\SP; SPACE-FLAIR SE\IR / SK\SP\MP; TrueFISP GR / SK\SS. OSP when phase oversampling > 0. Options vary with protocol details, so treat these as approximate. |
| `MagneticFieldStrength` from model name, else Larmor frequency | ✅ | |

## Philips

| Rule | Status | Notes |
| --- | --- | --- |
| "fold-over direction" = phase-encoding axis | 🔧 | The old draft parser treated it as the readout axis. |
| Polarity of phase encoding | ⚠️ | Not stored by Philips. Only `PhaseEncodingAxis` is written (like dcm2niix). |
| Readout timing from water-fat shift | ⚠️ | Formulas disagree across tools. We follow dcm2niix (issue #377): `ES = WFS / (f0 × 3.4 ppm × (EPI factor + 1))`, `EstimatedTotalReadoutTime = ES × EPI factor`, `EstimatedEffectiveEchoSpacing = TRT / (ReconMatrixPE − 1)`, and **never** write `EffectiveEchoSpacing`/`TotalReadoutTime`. EPI factor already includes SENSE. Known gaps: interpolation, halfscan. sdcflows uses another formula (≈ R× larger with SENSE). |
| `MagneticFieldStrength` from `WFS × BW` when no title | ✅ | WFS (pix) × BW (Hz/pix) = water-fat difference (≈ 434 Hz at 3 T). |
| Slice order (single package) | 🔧 | "default" = odd first (1,3,5,…,2,4,…) **for any N**; "interleaved" = step `round(sqrt(N))`; ascend/descend; "rev. central". The sqrt step is often wrongly attributed to "default". |
| `SliceTiming` | ⚠️ | dcm2niix writes none for Philips. We write it only for 1 package, no multiband and "Temporal slice spacing = equidistant"; otherwise omitted. |
| TFE inversion time | ⚠️ | We write the prepulse delay as printed ("To Exc"); with a linear profile order the effective TI is longer. |
| Scan-table "Bandwidth" of Philips EPI | 🔧 | Usually the PE bandwidth from the WFS: stored as `PhilipsReportedBandwidth`, not `PixelBandwidth`. |

## GE

| Rule | Status | Notes |
| --- | --- | --- |
| Sheet "Bandwidth" is ±kHz: `PixelBandwidth = 2 × BW × 1000 / Freq` | ✅ (medium-high) | Matches GE sidecars (±250 kHz / 64 → 7812.5). |
| EPI timing from DICOM (0043,102C) | ✅ | dcm2niix: `R = 1/(0043,1083)[0]`, `RF = 4 if PFF else 2`, `lines = ceil(AcqPE/R/RF)·RF`, `EES = (lines−1)·ESP/(AcqPE−1)`, `TRT = EES·(ReconPE−1)`. Only available from DICOM dumps. Cannot be derived from scan sheets (ramp sampling). |
| Interleaved order: odd first for any N | ✅ | |
| HyperBand slice timing | ✅ (= dcm2niix model) | dcm2niix *computes* GE SliceTiming itself (`sliceTimingGE`/`sliceTimeGE`): nexc = ceil(N/MB); even nexc: before 27.0 R03 one dummy slot is added (slices then mapped modulo nexc+1), from 27.0 R03 (or ≥ 27.1) on the last two excitations are swapped; HyperBand before 26.0: not supported. Our port matches all dcm_qa_ge references and 45/45 HyperBand sidecars computed by recent dcm2niix (remaining mismatches: old dcm2niix builds that did not record the MB factor, hand-made sidecars). Needs the software version (not on scan sheets). |
| GE slice timing: sequence types | ✅ (= dcm2niix) | Only for epiRT (IOPT contains FMRI: times spread over TR − group delay `DELACQNOAV`), multi-phase EPI (spread over TR; `DELACQ` = Minimum → no delay; variable delays `MPhVar` unsupported) and diffusion (non-cycling systems: pre-R03 behaviour; Premier/UHP/7.0T use gradient cycling whose mode is not printed → no timing). Not for 3D, localizers or other sequences. LX `SLICEORDER`: 0 = sequential, otherwise interleaved. Slice times are given in acquisition-index order; dcm2niix additionally reverses them when the DICOM slices are spatially flipped, which a printout cannot tell. |
| Phase-encoding polarity | ⚠️ | Not on scan sheets → `PhaseEncodingAxis` only. |
| `PercentPhaseFOV = Phase FOV × 100` | ✅ | |
| `AcquisitionMatrixPE` = printed "Phase" | ⚠️ | Relation with Phase FOV not established. |
| Fractional NEX = partial Fourier | ✅ (medium) | Only `PartialFourierEnabled` is set. |

## Scan tables (FCON1000)

Values are hand-typed by sites: only direct mappings are made.
`PhaseEncodingDirection` uses the Siemens convention and is written only
for Siemens tables with a NIfTI file. The old mapping used the readout
bandwidth as `BandwidthPerPixelPhaseEncode`, which was wrong (removed).
