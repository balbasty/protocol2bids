# RF spoiling increment

From Yarnykh (2007):

* __GE__ (default): 115.4°
* __Philips__ (default): 150°

In Lin & Song (2009), a Siemens FLASH sequence is modified to introduce
random phase increments. They compare against a fixed increment of __117°__,
which we can maybe assume is Siemens' default?

__117°__ was also proposed in Zur, Wood & Neuringer (1991).

In Scheffler (1999), it is said that __50°__ and __117°__ are common
vendors defaults.

__84°__ was proposed in Epstein, Nugler & Brookeman (1996).
But it is unclear if this value is used by anyone.

__50°__ was proposed in Preibisch & Deichmann (2009).

In Teixeira & al. (2019) it is said that the vendor's defaults are:

* __Philips__: 150°
* __Siemens__: 50°
* __GE__: 115°

Note that these are consistent (for GE and Philips) with the values
reported by Yarnykh (2007).

The default values __Siemens=50°__ and __Philips=150°__ are also reported in
Leutritz & al. (2020).

## References

* Zur, Wood & Neuringer,
  _"Spoiling of Transverse Magnetization in Steady-State Sequences."_
  MRM (1991)
* Epstein, Nugler & Brookeman,
  _"Spoiling of Transverse Magnetization in Gradient-Echo (GRE) Imaging
  during the Approach to Steady State."_
  MRM (1996)
* Scheffler,
  _"A Pictorial Description of Steady-States in Rapid Magnetic Resonance Imaging."_
  CMR (1999)
* Yarnykh,
  _"Effect of the phase increment on the accuracy of T1 measurements by the
  variable flip angle method using a fast RF spoiled gradient echo sequence."_
  ISMRM (2007)
* Lin & Song,
  _"Improved signal spoiling in fast radial gradient-echo imaging:
  Applied to accurate T1 mapping and flip angle correction."_
  MRM (2009)
* Preibisch & Deichmann,
  _"Influence of RF Spoiling on the Stability and Accuracy of T1 Mapping
  Based on Spoiled FLASH With Varying Flip Angles."_
  MRM (2009)
* Teixeira & al.,
  _"Controlled saturation magnetization transfer for reproducible multivendor
  variable flip angle T1 and T2 mapping."_
  MRM (2019)
* Leutritz & al.,
  _"Multiparameter mapping of relaxation (R1, R2*), proton density and
  magnetization transfer saturation at 3 T: A multicenterdual-vendor
  reproducibility and repeatability study."_
  MRM (2020)
