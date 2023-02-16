---
title: A review of the Garmin Fenix 6(x)
date: 2023-02-15
categories: [review]
tags:
- review
- garmin
- fitness
- health
- gps
- smartwatch
---

I've been using a [Garmin Fenix 6x][] for a couple of weeks and thought it might be interesting to put together a short review.

[garmin fenix 6x]: https://www.garmin.com/en-US/p/641435

## Is it really a smartwatch?

I think it's a misnomer to call the Fenix a "smartwatch". I would call it a highly capable fitness tracker. That's not a knock on the product; I really like it so far, but pretty much everything it does is centered around either fitness tracking or navigation. If you browse around the ["Connect IQ" store][iqstore], mostly you'll find (a) watch faces, (b) fitness apps, and (c) navigation apps. It's not able to control your phone (for the most part; there are some apps available that offer remote camera control and some other limited features); you can't check your email on it, or send text messages, and you'll never find a watch version of any major smartphone app.

[iqstore]: https://apps.garmin.com/en-US/

So if you're looking for a smartwatch, maybe look elsewhere. But if you're looking for a great fitness tracker, this just might be your device.

## Things I will not talk about

I don't listen to music when I exercise. If I'm inside, I'm watching a video on a streaming service, and if I'm outside, I want to be able to hear my surroundings. So I won't be looking at any aspects of music support on the Fenix.

## All the data in one place

One of the things I really like about the Fenix is that I now have more of my activity and health data in one place.

As part of my exercise a use a [Schwinn IC4][] spin bike. Previously, I was using a [Fitbit Charge 5][], which works fine but meant exercise metrics ended up in multiple places: while I could collect heart rate with the Fitbit, to collect cycling data like cadence, power, etc, I needed to use another app on my phone (I used [Wahoo Fitness][]). Additionally, Fitbit doesn't support sharing data with Apple Health, so there wasn't a great way to see a unified view of things.

[schwinn ic4]: https://www.schwinnfitness.com/ic4/100873.html
[fitbit charge 5]: https://www.fitbit.com/global/us/products/trackers/charge5
[wahoo fitness]: https://apps.apple.com/us/app/wahoo-fitness-phone-powered-fitness/id391599899?ign-mpt=uo%3D8%26amp%3Buo%3D8

This has all changed with the Fenix:

- First and probably most importantly, the Fenix is able to utilize the sensor on the IC4 directly, so cadence/speed/distance data is collected in the same place as heart rate data.

- Through the magic of the [Gymnasticon][] project, the Fenix is also able to collect power data from the bike.

- The Fenix is also great at tracking my outside bike rides, and of course providing basic heart rate and time tracking of my strength and PT workouts.

All of this means that Garmin's tools (both their app and the [Garmin Connect][] website) provide a great unified view of my fitness activities.

[garmin connect]: https://connect.garmin.com/
[gymnasticon]: https://github.com/ptx2/gymnasticon

## Notifications

This is an area in which I think there is a lot of room for improvement.

Like any good connected watch, you can configure your Fenix to receive notifications from your phone. Unfortunately, this is an all-or-nothing configuration; there's no facility for blocking or selecting notifications from specific apps.

I usually have my phone in do-not-disturb mode, so notifications from Google or the New York Times app don't interrupt me, but they show up in the notification center when I check for anything interesting. With my Fenix connected, I get interrupted every time something happens.

Having the ability to filter *which* notifications get sent to the watch would be an incredibly helpful feature.

## Battery life

One of the reasons I have the 6x instead of the 6 is the increased battery size that comes along with the bigger watch. While the advertising touts a battery life of "up to 21 days with activity tracking and 24/7 wrist-based heart rate monitoring", I've been seeing battery life closer to 1 week under normal use (which includes probably 10-20 miles of GPS-tracked bike rides a week).

I've been using the pulse oximeter at night, but I understand that can have a substantial contribution to battery drain; I've disabled it for now and I'll update this post if it turns out that has a significant impact on battery life.

One of the reasons that the Fenix is able to get substantially better battery life than the Apple Watch is that the screen is far, far dimmer. By default, the screen brightness is set to 20%; you can increase that, but you'll consume substantially more power by doing so. In well lit areas -- outdoors, or under office lighting -- the display is generally very easy to read even with the backlight low.

## Ease of use

It's a mixed bag.

The basic watch and fitness tracking functionality is easy to use, and I like the fact that it uses physical buttons rather than a touch screen (I've spent too much time struggling with touch screens in winter). The phone app itself is relatively easy to use, although the "Activities & Apps" screen has the bad habit of refreshing while you're trying to use it.

I have found Garmin's documentation to be very good, and highly search optimized. In most cases, when I've wanted to know how to do something on my watch I've been able to search for it on Google, and:

- Garmin's manual is usually the first result
- The instructions are on point and clearly written

For example, I wanted to know how to remove an activity from the list of favorite activities, so I searched for `garmin remove activity from favorites`, which led me directly to [this documentation](https://www8.garmin.com/manuals/webhelp/fenix6-6ssport/EN-US/GUID-B1501DD1-3616-4171-8814-07340761F494.html).

This was exactly the information I needed. I've had similar success with just about everything I've searched for.

The Garmin Connect app and website are both generally easy to use and well organized. There is an emphasis on "social networking" aspects (share your activities! Join a group! Earn badges!) in which I have zero interest, and I wish there was a checkbox to simply disable those parts of the UI.

The place where things really fall over is the "[IQ Connect][iqstore]" app store. There are many apps and watch faces there that require some sort of payment, but there's no centralized payment processing facility so you end up getting sent to random payment processors all over the place depending on what the software author selected...and price information simply isn't displayed in the app store **at all** unless an author happens to include it in the product description.

The UI for configuring custom watch faces is awful; it's a small step up from someone just throwing a text editor at you and telling you to edit a file. For this reason I've mostly stuck with Garmin-produced watch faces (the built-in ones and a few from the app store), which tend to have high visual quality but aren't very configurable.

## Some random technical details

While Garmin doesn't provide any Linux support at all, you can plug the watch into your Linux system and access the watch filesystem using any MTP client, including Gnome's [GVFS][]. While this isn't going to replace your phone app, it does give you reasonably convenient access to activity tracking data (as `.fit` files).

[gvfs]: https://wiki.gnome.org/Projects/gvfs

The Fenix ships with reasonably complete US maps. I haven't had the chance to assess their coverage of local hiking trails. You can load maps from the [OpenStreetMap][] project, although the process for doing so is annoyingly baroque.

[openstreetmap]: https://www.openstreetmap.org

It is easy to load GPX tracks from your favorite hiking website onto the watch using the Garmin Connect website or phone app.

## Wrapping up

I'm happy with the watch. It is a substantial upgrade from my Charge 5 in terms of fitness tracking, and aesthetically I like it as much as the Seiko [SNJ025][] I was previously wearing. It's not a great smartwatch, but that's not what I was looking for, and the battery life is much better than actual smart watches from Apple and Samsung.

[snj025]: https://seikousa.com/products/snj025

---

## A digression, in which I yell at All Trails

This isn't a Garmin or Fenix issue, but I'd like to specially recognize All Trails for making the process of exporting a GPX file to Garmin Connect as painful as possible. You can't do it at all from the phone app, so the process is something like:

1. Use the All Trails app to find a hike you like
2. Decide you want to send it to your watch
3. Open a browser on your phone, go to https://alltrails.com, and log in (again, even though you were already logged in on the app)
4. Find the hike again
5. Download the GPX
6. Open the downloads folder
7. Open the GPX file
8. Click the "share" button
9. Find the Garmin Connect app

That is...completely ridiculous. The "Share" button in the All Trails app should provide an option to share the GPX version of the route so the above process could be collapsed into a single step. All Trails, why do you hate your users so much?
