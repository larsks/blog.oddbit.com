---
categories: [tech]
title: "A DIY CPAP Battery Box"
date: "2019-05-14"
tags:
- diy
- medical
- cpap
- battery
---

A year or so ago I was diagnosed with [sleep apnea][], and since them I've been sleeping with a [CPAP][]. This past weekend, I joined my daughter on a [scout][] camping trip to a [campground][] without readily accessible electricity. This would be the first time I found myself in this situation, and as the date approached, I realized I was going to have to build or buy some sort of battery solution for my CPAP. I opted for the "build" option because it seemed like a fun project.

[sleep apnea]: https://en.wikipedia.org/wiki/Sleep_apnea
[cpap]: https://en.wikipedia.org/wiki/Continuous_positive_airway_pressure
[scout]: https://www.scouting.org/scoutsbsa/
[campground]: https://www.mass.gov/locations/harold-parker-state-forest

This is what I ended up with:

{{< figure
src="batterybox-003.jpg"
link="batterybox-003.jpg"
width="400"
>}}

{{< figure
src="batterybox-005.jpg"
link="batterybox-005.jpg"
width="400"
>}}


{{< figure
src="batterybox-001.jpg"
link="batterybox-001.jpg"
width="400"
>}}

It has a pair of 10Ah SLA batteries, two 12V ports, two USB charging ports, and an integrated 4A charger (just plug in an extension cord and it's all set). There are fuses on all of the output ports.

## Batteries

{{< figure
src="12v-10ah-batteries.jpg"
link="https://www.amazon.com/gp/product/B079LYZX9K"
width="200"
class="floatright"
>}}

I spent some time looking at battery options.  I wanted something that would easily last a couple of nights.  According to the [documentation from ResMed][resmed], my AirSense CPAP draws around 1A when the heat and humidity are disabled. That means for two nights, with the heat and humidity off, I'll need at least 16Ah.

[resmed]: https://www.resmed.com/us/dam/documents/articles/198103_battery-guide_glo_eng.pdf

I looked at some [LiFePO4][] batteries, but they were typically two- to three- times the cost of an equivalent [SLA][] battery.  I ended up purchasing a pair of 10Ah SLA batteries. Testing confirms that it does last for two nights. With the integrated 4A charger, they charge up relatively quickly as well (for a single night of use, it took around an hour for a full charge).

[lifepo4]: https://en.wikipedia.org/wiki/Lithium_iron_phosphate_battery
[sla]: https://en.wikipedia.org/wiki/Sealed_lead-acid_battery

The batteries are held in place by a roughly U-shaped piece of wood on the bottom of the case. The charger and the foam bad hold the batteries in when the top is closed.

{{< figure
src="resmed-battery-excerpt.png"
link="resmed-battery-excerpt.png"
width="200"
caption="ResMed battery data"
class="floatright"
>}}

## Parts list

- [Pelican 1300 case](https://www.amazon.com/gp/product/B00009XVKW)
- [Motopower MP00207 4A Charger](https://www.amazon.com/dp/B01FG7NW60)
- [NOCO 13A 125V port plug with extension cord](https://www.amazon.com/gp/product/B009ANV81S)
- [YonHan 4.8A Dual USB charger](https://www.amazon.com/gp/product/B07KSGMC39)
- [AutoEC 30A 12V switches](https://www.amazon.com/gp/product/B012IE1EKA)
- [12V Sockets](https://www.amazon.com/gp/product/B07QN2ML4X)

## Panel design

I used [qcad][] to design the panel layout. The cross-hairs are for identifying the center point:

{{< figure
src="panel-layout.png"
link="panel-layout.pdf"
width="400"
>}}

[qcad]: https://www.qcad.org/

I used a 1 1/8" hole saw to make the holes for the 12V and USB ports and a 2" hole saw for the through-plug on the back. I used a [step bit](https://www.amazon.com/gp/product/B001OEPYWK) to drill the smaller holes for the switches.

## A few extra pictures

{{< figure
src="batterybox-002.jpg"
link="batterybox-002.jpg"
width="400"
>}}

{{< figure
src="batterybox-004.jpg"
link="batterybox-004.jpg"
width="400"
>}}
