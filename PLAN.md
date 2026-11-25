# protocol2bids — action plan (parser overhaul)

> Living document. Agents working on this repo: read this first, pick an
> unchecked task from §9, and tick it (with a short note / commit hash)
> when done. Keep the plan in sync with reality.
>
> Working branch: `claude/refactor/robust-pdf-parser`

## 1. Goal

Parse PDF printouts of MRI protocols (mostly Siemens, also Philips and GE)
and produce the best possible guess of the corresponding BIDS sidecar
(+ DICOM-derived / dcm2niix-like keys), optionally refined by the NIfTI
header (shape + affine) of the corresponding image.

Two clearly separated problems:

1. **Extraction** — PDF → structured protocol tree
   (`protocol → card → [subcard] → [group] → key → value`).
   Purely about layout; must be robust to software versions, page breaks,
   two-column layouts, wrapped keys/values, re-typeset PDFs, font quirks.
2. **Interpretation** — protocol tree → BIDS sidecar.
   Pure physics/vendor knowledge (see `notes/`); must be explicit,
   testable and must never silently swallow programming errors.

## 2. Input corpus (245 PDFs in `examples/` and `datasets/`)

| Family | Count | Layout | Examples |
| --- | --- | --- | --- |
| Siemens `syngo MR B15/B17/B19` (VB) | ~97 | 2 columns, headers at col edge, keys indented, groups indented via **leading spaces inside spans**, values left-aligned at fixed x, `-----` sub-tab separators | `datasets/pdf/CoRR/BNU_1/rest.pdf` |
| Siemens `syngo MR 2002B/2004A/A30` (VA) | ~26 | as VB but units in brackets (`240 [mm]`), booleans as `0/1`, content emitted *before* headers in the PDF stream | `datasets/pdf/ABIDE1/NYU/rest.pdf` |
| Siemens `syngo MR D11/D13` (VD) | ~9 | 1 column, values **right-aligned**, "Page x of y" + date footer, TOC at end | `examples/pdf/siemens/Siemens_VD13_UKBB_*.pdf` |
| Siemens `syngo MR E11` (VE) | ~8 | 2 columns, bold 10pt card headers `Card - Subcard`, keys at same x as headers, groups have values (`Slice group 1`) and 4-space indented children, TOC at **start** | `examples/pdf/siemens/Siemens_VE11_*.pdf` |
| Siemens `Numaris/X VA20–VA31` (XA) | 4 | like VE but **Title Case** keys (`FoV Read`, `Distance Factor`, `Phase Encoding Dir.`), `Acc::` in title | `examples/pdf/siemens/Siemens_XA*` |
| Re-typeset Siemens (Word → PDF) | few | Times font, arbitrary x positions | `datasets/pdf/ABIDE2/ONRC_2/*.pdf` |
| Siemens with broken font encoding | 1 | glyphs need recoding (`utils/font_recoder.py`) | `examples/pdf/siemens_vb_hmri.pdf` |
| Image-only (scanned) | 3 | no text layer → OCR | `examples/unparsable/siemens/*` |
| Philips ExamCard (table) | ~10 | 3–4 columns `INFO PAGE / GEOMETRY / CONTRAST / ...`, indented sub-keys | `datasets/pdf/ABIDE1/KKI/rest.pdf`, `ABIDE1/SBL/*.pdf` |
| Philips ExamCard (txt dump) | ~6 | `Key = value;` lines, indented sub-keys | `datasets/pdf/ABIDE1/Leuven_*/*.pdf` |
| GE scan parameter sheet | ~12 | 2 columns of UPPERCASE sections | `datasets/pdf/ABIDE1/SDSU/*.pdf` |
| GE DICOM dump | 3 | `Name  gggg,eeee  value` | `examples/pdf/ge_dicom_fcon.pdf` |
| GE LX tcl (`set PROTNAME ...`) | 4 | tcl script | `datasets/pdf/CoRR/IACAS/*.pdf` |
| GE "Word" summaries | 2 | key: value with ligature garbage (`Pa3ent`) | `datasets/pdf/ABIDE1/UM_*/anat.pdf` |
| FCON/CoRR/ABIDE2 scan tables | ~50 | one column per scan | `examples/pdf/corr/*_scantable.pdf` |

Reference outputs available for validation:
* `datasets/json/ABIDE2/**` — sidecars distributed with ABIDE2
  (hand-curated, sometimes wrong/inconsistent, but good for sanity checks).
* `datasets/nii/**` — header-only NIfTI files matching the PDFs.
* `datasets/p2b/**`, `examples/json/**` — previous outputs of this tool
  (regression baseline only, known to contain bugs).

## 3. Diagnosis of the current implementation

Extraction (`vendors/siemens/{va,vb,vd,ve}.py`):
* Four near-duplicate parsers, each relying on the *order* of text
  objects in the PDF stream and on hard-coded trace offsets
  (`traces[1:]`, `traces[6:]`, `traces[:-2]`) → breaks on any variation.
* Indentation inferred from span x0, but VA/VB encode group indentation
  with leading spaces inside spans → partially handled with `startswith(' ')`.
* Column alignment estimated from the first page only.
* Users need `--skip-pages` to isolate one protocol out of a multi-protocol
  PDF (see `datasets/convert_*.sh`); TOC handling is ad hoc.
* Very slow (`page.get_textbox(bbox)` per trace).
* VE parser hard-codes `SoftwareVersions = 'syngo MR E11'`.

Interpretation (`vendors/siemens/common.py`):
* The keymap DSL wraps every formula in `try/except Exception: continue`,
  so typos and bugs are silent. Confirmed bugs:
  * `AcqusitionMatrix{FE,PE,SE}` typo → `ReconMatrix*` fallback never set.
  * `ParallelReductionFactorOurOfPlane` typo.
  * `raise exceptions` raises a list; kwargs loop uses the wrong variable.
  * `PercentPhaseFOV` reads `Routine//FoV Phase` (wrong case) → never set.
  * `MultiPlanarExcitation` compares a string to an int and its fallback
    lambda has the wrong arity → never set.
  * `"System - Miscellaneous/Coil Combine Mode"` uses `/` instead of `//`.
  * TSE `EchoTrainLength` mapper has no `formula` → never set.
  * `ScanningSequence` / `SequenceVariant` / `ScanOptions` (iadd mappers)
    abort on the first missing key and are mostly absent from outputs.
  * `RepetitionTime` is never written (only `VendorReportedRepetitionTime`).
  * `FrequencyEncodingSteps` uses PE inputs.
  * `MagneticFieldStrength` lookup fails for many models (`Allegra`,
    `Verio`, `Trio`, `Prisma_fit` variants, `Vida-XT-128`, ...).
* Key variants (`Resolution//X`, `Resolution - Common//X`,
  `Resolution - iPAT//X`, Title Case in XA...) are enumerated by hand for
  each field.

## 4. Target architecture

```
protocol2bids/
  pdf/
    words.py        # backend: PDF → Word(text, bbox, font, size, bold, page)
                    #   (pymupdf by default; pdfplumber backend possible;
                    #    OCR fallback; font recoding)
    layout.py       # vendor-agnostic: words → lines → columns → rows
                    #   Row(page, col, y, indent, key, value, font info)
  model.py          # Protocol / Entry data model + flexible lookup
  values.py         # value parsing: numbers, units, On/Off, fractions,
                    #   "A >> P", "R6.9 A4.6 H6.9 mm", "3.1×3.1×3.5 mm"
  vendors/
    siemens/
      printout.py   # ONE parser for VA/VB/VD/VE/XA: rows → [Protocol]
      synonyms.py   # key/card normalisation (XA Title Case, renamed keys)
      bids.py       # Protocol → BIDS (explicit functions, see §7)
    philips/        # ExamCard (table + txt dump)
    ge/             # scan sheet, DICOM dump, LX tcl
    tables.py       # fcon/CoRR/ABIDE scan tables
  detect.py         # vendor/format sniffing on extracted text
  cli.py            # list / select / convert
tests/
  test_layout.py, test_siemens_printout.py, test_values.py,
  test_siemens_bids.py, test_corpus.py (+ snapshots/)
```

### 4.1 Data model

```python
@dataclass
class Entry:
    card: str            # "Routine", "Contrast", ... (normalised)
    subcard: str | None  # "Common", "iPAT", "Dynamic" (VE/XA) or tab index (VB '-----')
    path: tuple[str,...] # group path, e.g. ("Slice group 1",)
    key: str             # raw key as printed
    value: str | None    # raw value as printed (joined if wrapped)
    page: int; bbox: tuple  # provenance (debugging / tests)

@dataclass
class Protocol:
    path: str            # "\\USER\...\name"
    header: dict         # TA, PAT, voxel size, rel SNR, sequence folder/name
    scanner: dict        # model, software version, field strength
    entries: list[Entry]
    def get(self, key, card=None, group=None, default=...) -> str
    def tree(self) -> dict   # nested dict for JSON dumps / snapshots
```

`get()` matches on a **normalised key** (casefold, collapse spaces,
synonyms table: `dist. factor ≡ distance factor`,
`phase enc. dir. ≡ phase encoding dir.`, `accel. factor pe ≡ acceleration
factor pe`, `pat mode ≡ acceleration mode`, ...), and on card *prefix*
(`card="Resolution"` matches `Resolution`, `Resolution - Common`,
`Resolution - iPAT`...). Group defaults to "first group" (slice group 1).
This replaces all hand-written `VARIANTS`.

## 5. Layout engine (vendor-agnostic)

1. **Words**: `page.get_text("words")`-like extraction (word bboxes exclude
   whitespace ⇒ leading-space indentation in VA/VB is handled for free),
   plus span font/size/bold via `get_text("dict")`. Apply font recoding
   when the text is garbled (no ASCII keywords but recoded text has them).
   If a page has no text: optional OCR (`page.get_textpage_ocr`, needs
   tesseract; skip with a clear warning when unavailable).
2. **Lines**: cluster words by baseline (tolerance ~ 0.3 × font size).
3. **Segments**: inside a line, split words where the horizontal gap is
   > ~1.5 × font size (separates key / value even when they share a span,
   and separates the two page columns).
4. **Columns**: estimate column boundaries per *document* (not per page)
   from the x-histogram of segment starts / whitespace gutters; page width
   / 2 is only a fallback. Full-width items (title, scanner banner,
   separators) are tagged and excluded.
5. **Rows**: each segment is assigned to a column; within a column, a row
   = (indent, key text, value text). Per column (document-wide), estimate:
   * indent levels by clustering key x0 (1-D k-means / gap clustering);
   * value zone: left edge of value segments (left-aligned layouts) or
     right edge (right-aligned VD layouts).
6. **Reading order**: page by page, column by column, top to bottom.
   State (current card/group) carries across columns and pages (VB right
   column often continues the last card of the left column).
7. **Noise**: drop page banners (`SIEMENS MAGNETOM ...` repeated),
   page numbers (`1/-`, `-2-`, `Page 1 of 5`), dates, TOC pages, `-----`
   separators (but record them as sub-tab boundaries).

## 6. Siemens printout parser (single implementation)

* **Protocol start**: line starting with `\\` (path, possibly wrapped over
  2 lines) followed by the title line matching
  `TA:|Scan Time:` … `Voxel size:` … `Rel. SNR:` … `SIEMENS|USER|: <seq>`.
  Parse title with tolerant regex (PAT / PM / Acc:: optional; `mm` glued
  to next token in VE; `[mm]` in VA).
* **Scanner banner**: `SIEMENS MAGNETOM <model...> (syngo MR <ver>|Numaris/X <ver>)`;
  model may contain spaces/dashes (`Prisma_fit`, `Vida-XT-128`,
  `Cima X`). VE banners lack the version → infer `syngo MR E11` only when
  the content is VE-like, and say so in a provenance field.
* **TOC**: skip pages titled `Table of contents` (beginning or end).
* **Row classification** (per row, using document-level statistics):
  * *card header*: no value AND (bold/larger font OR minimal indent level
    OR name matches known card regex
    `^(Properties|Routine|Contrast|Resolution|Geometry|System|Physio|Diff|BOLD|Angio|Inline|Sequence|Perfusion|ASL|Spectro|Dixon|Cardiac|Water|Fat|...)( - .+)?$`)
  * *group header*: next row is more indented (VB `Slice group 1`,
    VE `Slice group | 1` → group name `Slice group 1`).
  * *key continuation*: key-only row, same indent, no value, starts with
    lowercase or the previous key's value line has no own key (e.g.
    `Start measurement without` / `further preparation`).
  * *value continuation*: value-only row → append to previous value
    (`Prescan Normalize,` / `Elliptical filter`).
  * *empty key*: key without value (`Before measurement`) → `None`.
* Duplicate keys inside the same card (e.g. VB `Table position H` and
  `Table position 0 mm`) are kept as separate entries (list semantics).
* Output: `list[Protocol]`; selection by index or by name glob.

## 7. BIDS interpretation (Siemens)

Rewrite `common.py` as explicit, small functions grouped by topic
(hardware, sequence, geometry, k-space, timing, EPI), each:
* takes a `Protocol` (+ already computed BIDS keys + optional NIfTI info),
* returns values or raises `Missing` (a dedicated exception) when an input
  is absent — **only** `Missing` is caught by the driver; any other
  exception is a bug and surfaces in tests (optionally logged-and-skipped
  in CLI `--lenient` mode).
* records provenance (`which protocol keys were used`) for `--explain`.

Formulas follow `notes/siemens_dicom.md`, `notes/mprage.md`,
`notes/turboflash.md`, `notes/phase_encoding.md`,
`notes/frequency_encoding.md`:

* Matrices: `AcquisitionMatrixFE = Base resolution`;
  `AcquisitionMatrixPE = round(Base × PhaseRes × FoVphase)`;
  SE = slices (2D) or slabs × slices-per-slab (3D);
  oversampled variants with phase/slice oversampling; FE oversampling ×2.
* Recon matrix: from NIfTI when available (via direction mapping),
  otherwise acquisition matrix (×2 if `Interpolation On`).
* Directions: `DirectionPE/FE/SE` in anatomical codes, then BIDS
  `PhaseEncodingDirection` etc. from the NIfTI affine (existing
  `nii2axes`). Handle oblique strings (`T > C-23.0`, `Sag > Cor 10.2`) by
  taking the main orientation; handle `Rotation` (90° swaps PE/FE in-plane).
* Timing: `RepetitionTime` (normal sequences), `RepetitionTimeExcitation`
  / `RepetitionTimePreparation` / `InversionTime` for MPRAGE-like
  (`tfl*`), `EchoTime` (multi-echo: `TE 1..n` → list), `FlipAngle`.
* EPI: `EffectiveEchoSpacing`, `TotalReadoutTime`,
  `BandwidthPerPixelPhaseEncode`, `EchoTrainLength`, `NumberShots`,
  `MultibandAccelerationFactor`, `SliceTiming` (from TR, #slices,
  multi-slice mode / series order (`Interleaved`, `Ascending`,
  `Descending`), MB factor, concatenations) — Siemens interleaved rule:
  odd counts start at 0, even counts start at 1.
* Sequence classification table (`ScanningSequence`, `SequenceVariant`,
  `ScanOptions`, `PulseSequenceType`, `MRAcquisitionType`) driven by a
  single declarative table keyed on sequence name pattern
  (from `notes/vendor_sequences.md`) + modifiers (TI ⇒ IR/MP, RF spoiling
  ⇒ SP, fat sat ⇒ FS, asymmetric echo ⇒ PFF, phase PF ⇒ PFP, flow comp ⇒ FC,
  phase oversampling ⇒ OSP).
* Diffusion: b-values / directions / diffusion mode when present.
* `MagneticFieldStrength`: model table incl. `Allegra`, `Trio`, `Verio`,
  `Prisma_fit`, `Vida-XT*`, `Skyra_fit`..., matched by normalised prefix.
* Fix every bug listed in §3.

Output key policy (to confirm with maintainer, see §10): BIDS keys first,
then dcm2niix-style keys, then protocol2bids-specific keys
(`DirectionPE`, `OversampledAcquisitionMatrix*`, ...), optionally under
a namespace or dropped with `--strict-bids`.

## 8. Testing strategy

* `tests/test_values.py`: unit tests for value parsing.
* `tests/test_layout.py`: synthetic PDFs generated with pymupdf
  (`page.insert_text`) covering: 2 columns, wrapped keys/values,
  leading-space indentation, right-aligned values, page breaks.
* `tests/test_siemens_printout.py`: for each Siemens example PDF, assert
  number of protocols, protocol names, presence of key fields
  (`Routine/TR`, `Routine/TE`, `Resolution/Base resolution`,
  `Sequence/Bandwidth`, sequence name) and a few exact values checked by
  hand against the PDF.
* `tests/snapshots/`: JSON dump of `Protocol.tree()` per PDF; a test
  compares and `pytest --snapshot-update` regenerates (review diffs!).
* `tests/test_siemens_bids.py`: formula tests with hand-computed
  expectations (EPI echo spacing/TRT, MPRAGE timing, slice timing),
  plus comparison against `datasets/json/ABIDE2` for overlapping keys
  (tolerant; known-wrong reference values listed explicitly).
* `tests/test_corpus.py`: every PDF in the corpus parses without
  exception (OCR/unsupported families xfail with reason).
* CI: GitHub Actions running pytest on 3.10–3.13.

## 9. Work breakdown

Legend: `[ ]` todo, `[~]` in progress, `[x]` done.

### Phase 0 — infrastructure
- [x] 0.1 `pyproject.toml` (build-system only; metadata stays in
      `setup.cfg`), `[test]` extra, nibabel/numpy added to deps; editable
      install works.
- [x] 0.2 `tests/` + `pytest.ini` + `.github/workflows/tests.yml`
      (installs tesseract for OCR tests).
- [~] 0.3 Corpus index: Siemens part lives in `tests/test_corpus.py`;
      other families to add with phase 4.

### Phase 1 — extraction (Siemens first)
- [x] 1.1 `pdf/words.py` word extraction (+ font info, recoding hook).
- [x] 1.2 `pdf/layout.py` lines → segments → columns → rows.
- [x] 1.3 `model.py` Entry/Protocol + normalised lookup + synonyms.
- [x] 1.4 `values.py` value parsing.
- [x] 1.5 `vendors/siemens/printout.py` single parser (banner, title,
      TOC, cards, groups, continuations).
- [~] 1.6 Tests on all Siemens PDFs (smoke test on every file + hand-
      checked values per version). JSON snapshots still to do.
- [x] 1.7 Font-recoded PDF (`siemens_vb_hmri.pdf`): handled by OCR
      fallback when the text layer looks garbled (`font_recoder.py` is
      now unused).
- [x] 1.8 OCR fallback for `examples/unparsable/*` (full-page OCR for
      pages without text, line-level OCR for garbled lines, e.g. XA titles).

### Phase 2 — Siemens → BIDS
- [x] 2.1 New `vendors/siemens/bids.py` driver (`Missing` exception,
      provenance via `--explain`), existing keys ported.
- [x] 2.2 Fix bugs listed in §3; add `RepetitionTime`, `SliceTiming`,
      `PercentPhaseFOV`, sequence classification table.
- [~] 2.3 Direction handling: main orientation of oblique slices used;
      NIfTI-based recon matrices. **Fixed polarity bug in
      `utils/nii2axes.py`** (positive axes were reversed). TODO: verify
      FE polarity / sagittal slice polarity against real DICOMs.
- [~] 2.4 Multi-echo (`EchoTime` list, `EchoTime1/2`), MB slice timing,
      diffusion summary keys done. TODO: CMRR/HCP specific cards,
      concatenations in slice timing.
- [~] 2.5 Validation against `datasets/json/ABIDE2`: done by hand (see
      §11); to be turned into a test with an allow-list of known
      reference errors.

### Phase 3 — CLI
- [x] 3.1 `p2b list file.pdf` (protocol index, names, sequence).
- [x] 3.2 `p2b file.pdf out.json --select 2|"*rest*" --nii ...`
      (`--skip-pages` kept for backward compatibility).
- [x] 3.3 `p2b dump file.pdf` (raw protocol tree as JSON) and
      `--explain` provenance.
- [x] 3.4 Regenerate `examples/json`, `datasets/p2b` with the new code
      and update `convert*.sh` (protocols selected by index, not pages).

### Phase 4 — other vendors / formats (reuse layout engine)
- [x] 4.1 Philips ExamCard table layout (`ABIDE1/KKI`, `SBL`): reader done
      (`pdf/kvtable.py` + `vendors/philips/examcard.py`), BIDS mapping todo.
- [x] 4.2 Philips ExamCard txt dump (`Leuven_*`, `Trinity`): same reader;
      BIDS mapping todo.
- [x] 4.3 GE scan sheet (`SDSU`, `Stanford`, `MIA_1`, `SU_2`, `UM_*`):
      reader done (`vendors/ge/readers.py`), BIDS mapping todo.
- [x] 4.4 GE DICOM dump (`ge_dicom_fcon.pdf`, `EMC_1`): reader done; BIDS
      mapping todo (port `ge/dicom_printout.py`).
- [x] 4.5 GE LX tcl (`IACAS`): reader done; BIDS mapping todo.
- [x] 4.6 Scan tables (`*_scantable.pdf`): `vendors/tables.py` (all but
      `Gong_scantable.pdf`, which has another layout).
- [x] 4.7 BIDS mappings for Philips / GE (`vendors/{philips,ge}/bids.py`).

### Phase 5 — docs
- [~] 5.1 README: new CLI and supported formats matrix done; key table
      still describes the old implementation.
- [ ] 5.2 Move formulas from code comments to `notes/` where missing.

## 10. Open questions for the maintainer

1. Keep non-BIDS helper keys (`DirectionPE`, `OversampledAcquisitionMatrix*`,
   `HasPartialFourier*`, ...) in the output sidecars, or only behind a flag?
2. ~~`pymupdf` is AGPL while this package is MIT.~~ Decision: keep
   PyMuPDF; the README warns about its license for people who bundle
   protocol2bids.
3. Is OCR (tesseract) an acceptable optional dependency?
4. Should multi-protocol PDFs produce one sidecar per protocol by default
   (named after the protocol), rather than `out1.json`, `out2.json`?

## 11. Findings / status log

* **2026-11-25** — Phase 1 + most of phase 2/3 implemented on
  `claude/refactor/robust-pdf-parser`.
  * Every Siemens PDF of the corpus parses (`tests/test_corpus.py`),
    including re-printed PDFs with annotations, scanned PDFs (OCR) and
    PDFs with broken fonts (OCR).
  * pymupdf's default `TEXT_MEDIABOX_CLIP` drops glyphs that poppler
    renders (e.g. `datasets/pdf/CoRR/Utah_1/fieldmap.pdf`); disabled.
  * Old per-version parsers (`siemens/{va,vb,vd,ve,common,utils}.py`) and
    `register.py` were removed; `philips/`, `ge/`, `fcon.py` are untouched
    and still unregistered (phase 4).
  * ABIDE2 reference sidecars vs ours: TE/TR/FA/PE direction agree;
    differences come from the references: dist. factor applied to 3D
    slab partitions (`SpacingBetweenSlices` 1.5× too large),
    `AcquisitionMatrixPE` = base resolution (ignores FoV phase / phase
    resolution), NYU_1/NYU_2 bold values swapped, `TriTim` typo.
  * Known limitations: `Siemens_VB19+XA20+2002B_*.pdf` is a compilation
    of partial printouts with annotations (parses, but many protocols are
    incomplete); OCR output is noisy (some keys/cards misread);
    `examples/json` and `datasets/p2b` have **not** been regenerated yet
    (task 3.4).

* **2026-11-25 (2)** — Maintainer answers: keep helper keys; OCR is an
  acceptable optional dependency; name multi-protocol outputs after the
  protocol (done). Outputs regenerated. Readers for Philips and GE
  written; BIDS converters for them, vendor dispatch in `api.py`, scan
  tables and tests still to do. A review of the conversion rules against
  dcm2niix/literature is in progress.

* **2026-11-25 (3)** — Rules reviewed against dcm2niix source/validation
  data and literature: see `notes/conversion_rules.md` (Siemens DwellTime
  ×2, CMRR multiband order, SequenceVariant per sequence, no
  SpacingBetweenSlices / PE polarity for 3D; Philips/GE conventions).
  Philips, GE and scan-table converters + format detection done; outputs
  regenerated (new Philips/GE sites enabled in `datasets/convert_*.sh`).
  Old draft modules (`philips/txt.py`, `ge/dicom_printout.py`,
  `fcon.py`, `utils/font_recoder.py`) removed.
  Remaining: snapshots, HyperBand / product-SMS slice timing,
  `Gong_scantable.pdf`, optional MIT PDF backend.
