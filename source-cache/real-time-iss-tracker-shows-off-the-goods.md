# Real-Time ISS Tracker Shows Off The Goods

![Orbigator 实物图](https://hackaday.com/wp-content/uploads/2026/03/orbigator_detail.jpg)

What hardware hacker doesn’t have a soft spot for transparent cases? While they may have fallen out of mainstream favor, they have an undeniable appeal to anyone with an interest in electronic or mechanical devices. Which is why the [Orbigator built by wyojustin](https://wyolum.com/orbigator-real-time-satellite-tracker-with-overhead-alert-radar/) stands out among similar desktop orbital trackers we’ve seen.

Conceptually, it’s very similar to the [International Space Station tracking lamp that Will Dana built in 2025](https://hackaday.com/2025/07/08/touch-lamp-tracks-iss-with-style/). In fact, wyojustin cites it specifically as one of the inspirations for this project. But unlike that build, which saw a small model of the ISS moving across the surface of the globe, a transparent globe is rotated around the internal mechanism. This not only looks gorgeous, but solves a key problem in Will’s design — that is, there’s no trailing servo wiring that needs to be kept track of.

For anyone who wants an Orbigator of their own, wyojustin has done a fantastic job of documenting the hardware and software aspects of the build, and all the relevant files are available in the [project’s GitHub repository](https://github.com/wyolum/orbigator).

The 3D printable components have been created with OpenSCAD, the firmware responsible for calculating the current position of the ISS on the Raspberry Pi Pico 2 is written in MicroPython, and the PCB was designed in KiCad. Incidentally, we noticed that Hackaday alum [Anool Mahidharia](https://hackaday.com/author/anool/) appears to have been lending a hand with the board design.

As much as we love these polished orbital trackers, [we’ve seen far more approachable builds](https://hackaday.com/2025/04/07/tracking-the-iss-made-easy/) if you don’t need something so elaborate. If you’re more interested in keeping an eye out for planes and can get your hands on a pan-and-tilt security camera, [it’s even easier](https://hackaday.com/2025/05/27/look-to-the-sky-with-this-simple-plane-tracker/).
