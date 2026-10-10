# gd77-mods

🌐 **[Project site](https://gd77-mods.chicagooffline.com/)**

OpenGD77 display mods — patches that keep a capable DMR handheld readable for
someone who is new to radio, instead of burying the channel name under a row of
status flags.

Every mod is a setting you can switch off. Write-ups live on the project site.

## Patches and builds

Each mod is published as a plain unified diff against the OpenGD77 release
source, under `site/patches/`. Apply it to your own checkout and build it.

Prebuilt firmware lives in `site/firmware/` for anyone who doesn't want a
toolchain. These images carry no AMBE vocoder — the OpenGD77 sources don't
contain one, so the build leaves that region of flash as `0xFF` and your
flashing tool merges the vocoder in from its own donor image at write time.

OpenGD77 is BSD-3-Clause plus a non-commercial clause, which permits
redistributing binaries provided the licence accompanies them; it ships as
`site/firmware/LICENSE-OpenGD77.txt`. This site is non-commercial. The OpenGD77
developers wrote the firmware and have not endorsed these builds.

---

Eric Muehlstein — KC9MHE (amateur), WRXC682 (GMRS).
Written with AI assistance; the radios, the testing and any mistakes are mine.
